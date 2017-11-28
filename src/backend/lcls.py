# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
"""Translates between LCLS events and Hummingbird ones"""
from __future__ import print_function # Compatibility with python 2 and 3
import os
import logging
from backend.event_translator import EventTranslator
from backend.record import Record, add_record
import psana
import numpy
import datetime
from pytz import timezone
from . import ureg
from backend import Worker
import ipc
from hummingbird import parse_cmdline_args

_argparser = None
def add_cmdline_args():
    global _argparser
    from utils.cmdline_args import argparser
    _argparser = argparser
    group = _argparser.add_argument_group('LCLS', 'Options for the LCLS event translator')
    group.add_argument('--lcls-run-number', metavar='lcls_run_number', nargs='?',
                        help="run number",
                        type=int)
    group.add_argument('--lcls-number-of-frames', metavar='lcls_number_of_frames', nargs='?',
                        help="number of frames to be processed",
                        type=int)
    
    # ADUthreshold for offline analysis
    #group.add_argument('--ADUthreshold', metavar='ADUthreshold', nargs='?',
    #                    help="ADU threshold",
    #                    type=int)
    # Hitscore threshold for offline analysis
    #group.add_argument('--hitscore-thr', metavar='hitscore_thr', nargs='?',
    #                    help="Hitscore threshold",
    #                    type=int)
    # Output directory for offline analysis
    #group.add_argument('--out-dir', metavar='out_dir', nargs='?',
    #                    help="Output directory",
    #                    type=str)
    # Reduce output from offline analysis
    #group.add_argument('--reduced-output',
    #                    help="Write only very few data to output file",
    #                    action='store_true')
    
    
PNCCD_IDS = ['pnccdFront', 'pnccdBack']
ACQ_IDS = [('ACQ%i' % i) for i in range(1,4+1)]

class LCLSTranslator(object):
    """Translate between LCLS events and Hummingbird ones"""
    def __init__(self, state):
        self.timestamps = None
        self.library = 'psana'
        config_file = None
        if('LCLS/PsanaConf' in state):
            config_file = os.path.abspath(state['LCLS/PsanaConf'])
        elif('LCLS' in state and 'PsanaConf' in state['LCLS']):
            config_file = os.path.abspath(state['LCLS']['PsanaConf'])
        if(config_file is not None):
            if(not os.path.isfile(config_file)):
                raise RuntimeError("Could not find [LCLS][PsanaConf]: %s" %
                                   (config_file))
            logging.info("Info: Found configuration file %s.", config_file)
            psana.setConfigFile(config_file)

        if 'LCLS/CalibDir' in state:
            calibdir = state['LCLS/CalibDir']
            logging.info("Setting calib-dir to %s" % calibdir)
            psana.setOption('psana.calib-dir', calibdir)
        elif('LCLS' in state and 'CalibDir' in state['LCLS']):
            calibdir = state['LCLS']['CalibDir']
            logging.info("Setting calib-dir to %s" % calibdir)
            psana.setOption('psana.calib-dir', calibdir)

        if('LCLS/DataSource' in state):
            dsrc = state['LCLS/DataSource']
        elif('LCLS' in state and 'DataSource' in state['LCLS']):
            dsrc = state['LCLS']['DataSource']
        else:
            raise ValueError("You need to set the '[LCLS][DataSource]'"
                             " in the configuration")
        
        cmdline_args = _argparser.parse_args()
        self.N = cmdline_args.lcls_number_of_frames          
        if cmdline_args.lcls_run_number is not None:
            dsrc += ":run=%i" % cmdline_args.lcls_run_number

        # Cache times of events that shall be extracted from XTC (does not work for stream)
        self.event_slice = slice(0,None,1)
        if 'times' in state or 'fiducials' in state:
            if not ('times' in state and 'fiducials' in state):
                raise ValueError("Times or fiducials missing in state."
                                 " Extraction of selected events expects both event identifiers")                
            if dsrc[:len('exp=')] != 'exp=':
                raise ValueError("Extraction of events with given times and fiducials"
                                 " only works when reading from XTC with index files")
            if dsrc[-len(':idx'):] != ':idx':
                dsrc += ':idx'
            self.times = state['times']
            self.fiducials = state['fiducials']
            self.i = 0
            self.data_source = psana.DataSource(dsrc)
            self.run = self.data_source.runs().next()                        
        elif 'indexing' in state:
            if dsrc[-len(':idx'):] != ':idx':
                dsrc += ':idx'
            if 'index_offset' in state:
                self.i = state['index_offset'] / ipc.mpi.nr_event_readers()
            else:
                self.i = 0
            self.data_source = psana.DataSource(dsrc)
            self.run = self.data_source.runs().next()
            self.timestamps = self.run.times()
            if self.N is not None:
                self.timestamps = self.timestamps[:self.N]
            self.timestamps = self.timestamps[ipc.mpi.event_reader_rank()::ipc.mpi.nr_event_readers()]
        else:
            self.times = None
            self.fiducials = None
            self.i = 0
            if not dsrc.startswith('shmem='):
                self.event_slice = slice(ipc.mpi.event_reader_rank(), None, ipc.mpi.nr_event_readers())
            self.data_source = psana.DataSource(dsrc)
            self.run = None
            
        # Define how to translate between LCLS types and Hummingbird ones
        self._n2c = {}
        self._n2c[psana.Bld.BldDataFEEGasDetEnergy] = 'pulseEnergies'
        self._n2c[psana.Bld.BldDataFEEGasDetEnergyV1] = 'pulseEnergies'
        self._n2c[psana.Lusi.IpmFexV1] = 'pulseEnergies'
        self._n2c[psana.Camera.FrameV1] = 'camera'
        # Guard against old(er) psana versions
        try:
            self._n2c[psana.Bld.BldDataEBeamV1] = 'photonEnergies'
            self._n2c[psana.Bld.BldDataEBeamV2] = 'photonEnergies'
            self._n2c[psana.Bld.BldDataEBeamV3] = 'photonEnergies'
            self._n2c[psana.Bld.BldDataEBeamV4] = 'photonEnergies'
            self._n2c[psana.Bld.BldDataEBeamV5] = 'photonEnergies'
            self._n2c[psana.Bld.BldDataEBeamV6] = 'photonEnergies'
            self._n2c[psana.Bld.BldDataEBeamV7] = 'photonEnergies'
        except AttributeError:
            pass
        # CXI (CsPad)
        self._n2c[psana.CsPad.DataV2] = 'photonPixelDetectors'
        self._n2c[psana.CsPad2x2.ElementV1] = 'photonPixelDetectors'
        # CXI (OffAxis Cam)
        #self._n2c[psana.Camera.FrameV1] = 'photonPixelDetectors'
        # AMO (pnCCD)
        self._n2c[psana.PNCCD.FullFrameV1] = 'photonPixelDetectors'
        self._n2c[psana.PNCCD.FramesV1] = 'photonPixelDetectors'
        # --
        self._n2c[psana.Acqiris.DataDescV1] = 'ionTOFs'
        self._n2c[psana.EventId] = 'eventID'
        # Guard against old(er) psana versions
        try:
            self._n2c[psana.EvrData.DataV3] = 'eventCodes'
            self._n2c[psana.EvrData.DataV4] = 'eventCodes'
        except AttributeError:
            pass

        # Calculate the inverse mapping
        self._c2n = {}
        for k, v in self._n2c.iteritems():
            self._c2n[v] = self._c2n.get(v, [])
            self._c2n[v].append(k)

        # Define how to translate between LCLS sources and Hummingbird ones
        self._s2c = {}
        # CXI (OnAxis Cam)
        self._s2c['DetInfo(CxiEndstation.0:Opal4000.1)'] = 'Sc2Questar'
        # CXI (OffAxis Cam)
        self._s2c['DetInfo(CxiEndstation.0.Opal11000.0)'] = 'Sc2Offaxis'
        # CXI (CsPad)
        self._s2c['DetInfo(CxiDs1.0:Cspad.0)'] = 'CsPad Ds1'
        self._s2c['DetInfo(CxiDsd.0:Cspad.0)'] = 'CsPad Dsd'
        self._s2c['DetInfo(CxiDs2.0:Cspad.0)'] = 'CsPad Ds2'
        self._s2c['DetInfo(CxiDg3.0:Cspad2x2.0)'] = 'CsPad Dg3'
        self._s2c['DetInfo(CxiDg2.0:Cspad2x2.0)'] = 'CsPad Dg2'
        # AMO (pnCCD)
        self._s2c['DetInfo(Camp.0:pnCCD.1)'] = 'pnccdBack'
        self._s2c['DetInfo(Camp.0:pnCCD.0)'] = 'pnccdFront'
        # ToF detector
        self._s2c['DetInfo(AmoEndstation.0:Acqiris.0)'] = 'Acqiris 0'
        self._s2c['DetInfo(AmoEndstation.0:Acqiris.1)'] = 'Acqiris 1'
        self._s2c['DetInfo(AmoEndstation.0:Acqiris.2)'] = 'Acqiris 2'
        # AMO (Acqiris)
        self._s2c['DetInfo(AmoETOF.0:Acqiris.0)'] = 'Acqiris 0'
        self._s2c['DetInfo(AmoETOF.0:Acqiris.1)'] = 'Acqiris 1'
        self._s2c['DetInfo(AmoITOF.0:Acqiris.0)'] = 'Acqiris 2'
        self._s2c['DetInfo(AmoITOF.0:Acqiris.1)'] = 'Acqiris 3'

        # MCP Camera
        self._s2c['DetInfo(AmoEndstation.0:Opal1000.1)'] = 'OPAL1'
        # CXI (Acqiris)
        self._s2c['DetInfo(CxiEndstation.0:Acqiris.0)'] = 'Acqiris 0'
        self._s2c['DetInfo(CxiEndstation.0:Acqiris.1)'] = 'Acqiris 1'

        self.init_detectors(state)
        
        #print("Detectors:" , psana.DetNames())

    def init_detectors(self, state):
        # New psana call pattern
        self._detectors = {}
        self._c2id_detectors = {}
        if 'detectors' in state:
            for detid, det_dict in state['detectors'].items():
                if detid in PNCCD_IDS:
                    self._detectors[detid] = {}
                    self._detectors[detid]['id']  = det_dict['id']
                    self._detectors[detid]['type']  = det_dict['type']
                    self._detectors[detid]['key']  = det_dict['key']
                    obj =  psana.Detector(det_dict['id'])
                    self._detectors[detid]['obj']  = obj
                    meth = det_dict['data_method']
                    if meth == "image":
                        f = lambda obj, evt: obj.image(evt)
                    elif meth == "calib":
                        f = lambda obj, evt: obj.calib(evt)
                    elif meth == "raw":
                        def f(obj, evt):
                            #obj = self._detectors[detid]['obj']
                            raw = numpy.array(obj.raw(evt), dtype=numpy.float32, copy=True)
                            return raw
                    elif meth == "calib_pc":
                        def f(obj, evt):
                            cdata = numpy.array(obj.raw(evt), dtype=numpy.float32, copy=True) - obj.pedestals(evt)
                            return cdata
                    elif meth == "calib_cmc":
                        def f(obj, evt):
                            #obj = self._detectors[detid]['obj']
                            rnum = obj.runnum(evt)
                            cdata = numpy.array(obj.raw(evt), dtype=numpy.float32, copy=True) - obj.pedestals(evt)
                            obj.common_mode_apply(rnum, cdata, cmpars=None)
                            return cdata
                    elif meth == "calib_gc":
                        def f(obj, evt):
                            #obj = self._detectors[detid]['obj']
                            rnum = obj.runnum(evt)
                            cdata = numpy.array(obj.raw(evt), dtype=numpy.float32, copy=True) - obj.pedestals(evt)
                            obj.common_mode_apply(rnum, cdata, cmpars=None)
                            gain = obj.gain(evt)
                            cdata *= gain
                            return cdata
                    else:
                        raise RuntimeError('data_method = %s not supported' % meth)
                    self._detectors[detid]['data_method'] = f
                    self._c2id_detectors[det_dict['type']] = detid
                    print("Set data method for detector id %s to %s." % (det_dict['id'], meth))
                elif detid in ACQ_IDS:
                    self._detectors[detid] = {}
                    self._detectors[detid]['id']  = det_dict['id']
                    self._detectors[detid]['type']  = det_dict['type']
                    self._detectors[detid]['keys']  = det_dict['keys']
                    obj =  psana.Detector(det_dict['id'])
                    self._detectors[detid]['obj']  = obj
                    self._c2id_detectors[det_dict['type']] = detid
                else:
                    raise RuntimeError('Detector type = %s not implememented for ID %s' %  (det_dict['type'], detid))

    def next_event(self):
        """Grabs the next event and returns the translated version"""           
        if self.timestamps:            
            try:
                evt = self.run.event(self.timestamps[self.i])
            except (IndexError, StopIteration) as e:
                #if 'end_of_run' in dir(Worker.conf):
                #    Worker.conf.end_of_run()
                #ipc.mpi.slave_done()
                return None
            self.i += 1
        elif self.times is not None:
            evt = None
            while self.i < len(self.times) and evt is None:
                time = psana.EventTime(int(self.times[self.i]), self.fiducials[self.i])
                self.i += 1
                evt = self.run.event(time)
                if evt is None:
                    print("Unable to find event listed in index file")
            # We got to the end without a valid event, time to call it a day
            if evt is None:
                #if 'end_of_run' in dir(Worker.conf):
                #    Worker.conf.end_of_run()
                #ipc.mpi.slave_done()
                return None
        else:
            try:
                while (self.i % self.event_slice.step) != self.event_slice.start:
                    evt = self.data_source.events().next()
                    self.i += 1
                if self.N is not None and self.i >= self.N:
                    raise StopIteration
                evt = self.data_source.events().next()
                self.i += 1
            except StopIteration:
                #if 'end_of_run' in dir(Worker.conf):
                #    Worker.conf.end_of_run()
                #ipc.mpi.slave_done()
                return None
        return EventTranslator(evt, self)

    def event_keys(self, evt):
        """Returns the translated keys available"""
        native_keys = evt.keys()
        common_keys = set()
        for k in native_keys:
            for c in self._native_to_common(k):
                common_keys.add(c)
        # parameters corresponds to the EPICS values, analysis is for values added later on
        return list(common_keys)+['parameters']+['analysis']

    def _native_to_common(self, key):
        """Translates a native key to a hummingbird one"""
        if(key.type() in self._n2c):
            return [self._n2c[key.type()]]
        else:
            return []

    def event_native_keys(self, evt):
        """Returns the native keys available"""
        return evt.keys()

    def translate(self, evt, key):
        """Returns a dict of Records that match a given humminbird key"""
        values = {}
        if(key in self._c2id_detectors):
            return self.translate_object(evt, key)
        elif(key in self._c2n):
            return self.translate_core(evt, key)
        elif(key == 'parameters'):
            return self._tr_epics()
        elif(key == 'analysis'):
            return {}
        elif(key == 'stream'):
            return {}
        else:
            # check if the key matches any of the existing keys in the event
            event_keys = evt.keys()
            values = {}
            found = False
            for event_key in event_keys:
                if(event_key.key() == key):
                    obj = evt.get(event_key.type(), event_key.src(), event_key.key())
                    found = True
                    add_record(values, 'native', '%s[%s]' % (self._s2c[str(event_key.src())], key),
                               obj, ureg.ADU)
            if(found):
                return values
            else:
                print('%s not found in event' % (key))

    def translate_object(self, evt, key):
        values = {}
        detid = self._c2id_detectors[key]
        if detid in PNCCD_IDS:
            det = self._detectors[detid]
            obj = self._detectors[detid]['obj']
            data_nda = det['data_method'](obj, evt)
            if data_nda is None:
                image = None
            elif len(data_nda.shape) <= 2:
                image = data_nda
            elif len(data_nda.shape) == 3:
                image = numpy.hstack([numpy.vstack([data_nda[0],data_nda[1][::-1,::-1]]),
                                      numpy.vstack([data_nda[3],data_nda[2][::-1,::-1]])])
            add_record(values, det['type'], det['key'], image, ureg.ADU)
        elif detid in ACQ_IDS:
            det = self._detectors[detid]
            # waveforms are in Volts, times are in Seconds
            obj = det['obj']
            waveforms = obj.waveform(evt)
            #print("waveforms", waveforms)
            #times = obj.wftime(evt)
            for i, wf in enumerate(waveforms):
                add_record(values, det['type'], det['keys'][i], wf, ureg.V)
        else:
            raise RuntimeError('%s not yet supported' % key)
        return values

    def translate_core(self, evt, key):
        """Returns a dict of Records that matchs a core Hummingbird key.

        Core keys include  all except: parameters, any psana create key,
        any native key."""
        values = {}
        native_keys = self._c2n[key]
        event_keys = evt.keys()
        for k in event_keys:
            if(k.type() in native_keys):
                obj = evt.get(k.type(), k.src(), k.key())
                if(isinstance(obj, psana.Bld.BldDataFEEGasDetEnergy) or
                   isinstance(obj, psana.Bld.BldDataFEEGasDetEnergyV1)):
                    self._tr_bld_data_fee_gas_det_energy(values, obj)
                elif(isinstance(obj, psana.Lusi.IpmFexV1)):
                    self._tr_lusi_ipm_fex(values, obj, k)
                elif(key == 'photonEnergies'):
                    self._tr_bld_data_ebeam(values, obj)
                elif(isinstance(obj, psana.CsPad2x2.ElementV1)):
                    self._tr_cspad2x2(values, obj)
                elif(isinstance(obj, psana.CsPad.DataV2)):
                    self._tr_cspad(values, obj, k)
                # AMO
                elif(isinstance(obj, psana.PNCCD.FullFrameV1)):
                    self._tr_pnccdFullFrame(values, obj, k)
                elif(isinstance(obj, psana.PNCCD.FramesV1)):
                    self._tr_pnccdFrames(values, obj, k)
                # --
                elif(isinstance(obj, psana.Acqiris.DataDescV1)):
                    self._tr_acqiris(values, obj, k)
                elif(isinstance(obj, psana.Camera.FrameV1)):
                    self._tr_camera(values, obj)
                elif(isinstance(obj, psana.EventId)):
                    self._tr_event_id(values, obj)
                elif(isinstance(obj, psana.EvrData.DataV3) or
                     isinstance(obj, psana.EvrData.DataV4)):
                    self._tr_event_codes(values, obj)
                else:
                    print(type(obj))
                    print(k)
                    raise RuntimeError('%s not yet supported' % (type(obj)))
                
        return values

    def event_id(self, evt):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp

    def event_id2(self, evt):
        """Returns the LCLS time, a 64-bit integer as an alterative ID"""
        return self.translate(evt, 'eventID')['Timestamp'].timestamp2

    def _tr_bld_data_ebeam(self, values, obj):
        """Translates BldDataEBeam to hummingbird photon energy and other beam properties"""
        try:
            photon_energy_ev = obj.ebeamPhotonEnergy()
        except AttributeError:
            peak_current = obj.ebeamPkCurrBC2()
            dl2_energy_gev = 0.001*obj.ebeamL3Energy()
    
            ltu_wake_loss = 0.0016293*peak_current
            # Spontaneous radiation loss per segment
            sr_loss_per_segment = 0.63*dl2_energy_gev
            # wakeloss in an undulator segment
            wake_loss_per_segment = 0.0003*peak_current
            # energy loss per segment
            energy_loss_per_segment = (sr_loss_per_segment +
                                       wake_loss_per_segment)
            # energy in first active undulator segment [GeV]
            energy_profile = (dl2_energy_gev - 0.001*ltu_wake_loss -
                              0.0005*energy_loss_per_segment)
            # Calculate the resonant photon energy of the first active segment
            photon_energy_ev = 44.42*energy_profile*energy_profile
        add_record(values, 'photonEnergies', 'photonEnergy', photon_energy_ev, ureg.eV)

        try:
            ebeam_ang_x  = obj.ebeamLTUAngX()
            ebeam_ang_y  = obj.ebeamLTUAngY()
            ebeam_pos_x  = obj.ebeamLTUPosX()
            ebeam_pos_y  = obj.ebeamLTUPosY()
            ebeam_charge = obj.ebeamCharge()
            add_record(values, 'photonEnergies', 'angX', ebeam_ang_x)
            add_record(values, 'photonEnergies', 'angY', ebeam_ang_y)
            add_record(values, 'photonEnergies', 'posX', ebeam_pos_x)
            add_record(values, 'photonEnergies', 'posY', ebeam_pos_y)
            add_record(values, 'photonEnergies', 'charge', ebeam_charge)
        except AttributeError:
            print("Couldn't translate electron beam properties from BldDataEBeam")

    def _tr_bld_data_fee_gas_det_energy(self, values, obj):
        """Translates gas monitor detector to hummingbird pulse energy"""
        # convert from mJ to J
        add_record(values, 'pulseEnergies', 'f_11_ENRC', obj.f_11_ENRC(), ureg.mJ)
        add_record(values, 'pulseEnergies', 'f_12_ENRC', obj.f_12_ENRC(), ureg.mJ)
        add_record(values, 'pulseEnergies', 'f_21_ENRC', obj.f_21_ENRC(), ureg.mJ)
        add_record(values, 'pulseEnergies', 'f_22_ENRC', obj.f_22_ENRC(), ureg.mJ)

    def _tr_lusi_ipm_fex(self, values, obj, evt_key):
        """Translates Ipm relative pulse energy monitor
        to hummingbird pulse energy"""
        add_record(values, 'pulseEnergies', 'IpmFex - '+str(evt_key.src()), obj.sum(), ureg.ADU)

    def _tr_cspad2x2(self, values, obj):
        """Translates CsPad2x2 to hummingbird numpy array"""
        try:
            add_record(values, 'photonPixelDetectors', 'CsPad2x2S', obj.data(), ureg.ADU)
        except AttributeError:
            add_record(values, 'photonPixelDetectors', 'CsPad2x2', obj.data16(), ureg.ADU)

    def _tr_camera(self, values, obj):
        """Translates Camera frame to hummingbird numpy array"""
        #if obj.depth == 16 or obj.depth() == 12:
        #    data = obj.data16()
        #    print(data.shape)
        #else:
        #    data = obj.data8()
        #    print(data.shape)
        data = obj.data16()

        # off Axis cam at CXI
        #if data.shape == (1024,1024):
        #    add_record(values, 'camera', 'offAxis', data, ureg.ADU)
  
        # MCP (PNCCD replacement) at AMO (June 2016)
        if data.shape == (1024,1024):
            add_record(values, 'camera', 'mcp', data, ureg.ADU)

        if data.shape == (1752,2336):
            add_record(values, 'camera', 'onAxis', data, ureg.ADU)

    def _tr_cspad(self, values, obj, evt_key):
        """Translates CsPad to hummingbird numpy array, quad by quad"""
        n_quads = obj.quads_shape()[0]
        for i in range(0, n_quads):
            add_record(values, 'photonPixelDetectors', '%sQuad%d' % (self._s2c[str(evt_key.src())], i),
                       obj.quads(i).data(), ureg.ADU)
    def _tr_pnccdFullFrame(self, values, obj, evt_key):
        """Translates full pnCCD frame to hummingbird numpy array"""
        add_record(values, 'photonPixelDetectors', '%sfullFrame' % self._s2c[str(evt_key.src())], obj.data(), ureg.ADU)
    def _tr_pnccdFrames(self, values, obj, evt_key):
        """Translates pnCCD frames to hummingbird numpy array, frame by frame"""
        n_frames = obj.frame_shape()[0]
        for i in range(0, n_frames):
            add_record(values, 'photonPixelDetectors', '%sFrame%d' % (self._s2c[str(evt_key.src())], i),
                       obj.frame(i).data(), ureg.ADU)
    def _tr_acqiris(self, values, obj, evt_key):
        """Translates Acqiris TOF data to hummingbird numpy array"""
        config_store = self.data_source.env().configStore()
        acq_config = config_store.get(psana.Acqiris.ConfigV1, evt_key.src())
        samp_interval = acq_config.horiz().sampInterval()
        n_channels = obj.data_shape()[0]
        for i in range(0, n_channels):
            vert = acq_config.vert()[i]
            elem = obj.data(i)
            timestamp = elem.timestamp()[0].value()
            raw = elem.waveforms()[0]
            if(elem.nbrSamplesInSeg() == 0):
                logging.warning("Warning: TOF data for "
                                "detector %s is missing.", evt_key)
            data = raw*vert.slope() - vert.offset()
            rec = Record('%s Channel %d' %(self._s2c[str(evt_key.src())], i),
                         data, ureg.V)
            rec.time = (timestamp +
                        samp_interval * numpy.arange(0, elem.nbrSamplesInSeg()))
            values[rec.name] = rec

    def _tr_event_id(self, values, obj):
        """Translates LCLS eventID into a hummingbird one"""
        timestamp = obj.time()[0]+obj.time()[1]*1e-9
        time = datetime.datetime.fromtimestamp(timestamp, tz=timezone('utc'))
        time = time.astimezone(tz=timezone('US/Pacific'))
        rec = Record('Timestamp', time, ureg.s)
        time = datetime.datetime.fromtimestamp(obj.time()[0])
        rec.datetime64 = numpy.datetime64(time, 'ns')+obj.time()[1]
        rec.fiducials = obj.fiducials()
        rec.run = obj.run()
        rec.ticks = obj.ticks()
        rec.vector = obj.vector()
        rec.timestamp = timestamp
        rec.timestamp2 = obj.time()[0] << 32 | obj.time()[1]
        values[rec.name] = rec

    def _tr_event_codes(self, values, obj):
        """Translates LCLS event codes into a hummingbird ones"""
        codes = []
        for fifo_event in obj.fifoEvents():
            codes.append(fifo_event.eventCode())
        add_record(values, 'eventCodes', 'EvrEventCodes', codes)

    def _tr_epics(self):
        """Returns an EPICSdict that provides access to EPICS parameters.

        Check the EPICSdict class for more details.
        """
        return EPICSdict(self.data_source.env().epicsStore())

class EPICSdict(object):
    """Provides a dict-like interface to EPICS parameters.

    Translated  all the parameters is too slow too slow.
    Instead parameters are only translated as they are needed,
    when they are accessed, using this class.
    """
    def __init__(self, epics):
        self.epics = epics
        self._cache = {}
        self._keys = None

    def keys(self):
        """Returns available EPICS names"""
        if self._keys is None:
            self._keys = self.epics.pvNames() + self.epics.aliases()
        return self._keys

    def len(self):
        """Returns the length of the dictionary"""
        return len(self.keys())

    def __getitem__(self, key):
        """Calls psana to retrieve and translate the EPICS item"""
        if(key not in self._cache):
            pv = self.epics.getPV(key)
            if(pv is None):
                raise KeyError('%s is not a valid EPICS key' %(key))
            rec = Record(key, pv.value(0))
            rec.pv = pv
            self._cache[key] = rec
        return self._cache[key]
