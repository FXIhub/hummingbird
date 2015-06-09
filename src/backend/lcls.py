"""Translates between LCLS events and Hummingbird ones"""
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

class LCLSTranslator(object):
    """Translate between LCLS events and Hummingbird ones"""
    def __init__(self, state):
        config_file = None
        if('LCLS/PsanaConf' in state):
            config_file = "%s/%s" % (Worker.state['_config_dir'],
                                     state['LCLS/PsanaConf'])
        elif('LCLS' in state and 'PsanaConf' in state['LCLS']):
            config_file = "%s/%s" % (Worker.state['_config_dir'],
                                     state['LCLS']['PsanaConf'])
        if(config_file is not None):
            if(not os.path.isfile(config_file)):
                raise RuntimeError("Could not find [LCLS][PsanaConf]: %s" %
                                   (config_file))
            logging.info("Info: Found configuration file %s.", config_file)
            psana.setConfigFile(config_file)

        if('LCLS/DataSource' in state):
            self.data_source = psana.DataSource(state['LCLS/DataSource'])
        elif('LCLS' in state and 'DataSource' in state['LCLS']):
            self.data_source = psana.DataSource(state['LCLS']['DataSource'])
        else:
            raise ValueError("You need to set the '[LCLS][DataSource]'"
                             " in the configuration")

        # Define how to translate between LCLS types and Hummingbird ones
        self._n2c = {}
        self._n2c[psana.Bld.BldDataFEEGasDetEnergy] = 'pulseEnergies'
        self._n2c[psana.Bld.BldDataFEEGasDetEnergyV1] = 'pulseEnergies'
        self._n2c[psana.Lusi.IpmFexV1] = 'pulseEnergies'
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
        self._n2c[psana.CsPad.DataV2] = 'photonPixelDetectors'
        self._n2c[psana.CsPad2x2.ElementV1] = 'photonPixelDetectors'
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
        self._s2c['DetInfo(CxiDs1.0:Cspad.0)'] = 'CsPad Ds1'
        self._s2c['DetInfo(CxiDsd.0:Cspad.0)'] = 'CsPad Dsd'
        self._s2c['DetInfo(CxiDs2.0:Cspad.0)'] = 'CsPad Ds2'
        self._s2c['DetInfo(CxiDg3.0:Cspad2x2.0)'] = 'CsPad Dg3'
        self._s2c['DetInfo(CxiDg2.0:Cspad2x2.0)'] = 'CsPad Dg2'
        self._s2c['DetInfo(CxiEndstation.0:Acqiris.0)'] = 'Acqiris 0'
        self._s2c['DetInfo(CxiEndstation.0:Acqiris.1)'] = 'Acqiris 1'

    def next_event(self):
        """Grabs the next event and returns the translated version"""
        evt = self.data_source.events().next()
        return EventTranslator(evt, self)

    def event_keys(self, evt):
        """Returns the translated keys available"""
        native_keys = evt.keys()
        common_keys = set()
        for k in native_keys:
            for c in self._native_to_common(k):
                common_keys.add(c)
        # parameters corresponds to the EPICS values, analysis is for values added lateron
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
        if(key in self._c2n):
            return self.translate_core(evt, key)
        elif(key == 'parameters'):
            return self._tr_epics()
        elif(key == 'analysis'):
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
                print '%s not found in event' % (key)

    def translate_core(self, evt, key):
        """Returns a dict of Records that matchs a core humminbird key.

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
                elif(isinstance(obj, psana.Acqiris.DataDescV1)):
                    self._tr_acqiris(values, obj, k)
                elif(isinstance(obj, psana.EventId)):
                    self._tr_event_id(values, obj)
                elif(isinstance(obj, psana.EvrData.DataV3) or
                     isinstance(obj, psana.EvrData.DataV4)):
                    self._tr_event_codes(values, obj)
                else:
                    print type(obj)
                    print k
                    raise RuntimeError('%s not yet supported' % (type(obj)))
        return values

    def event_id(self, evt):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return float(self.translate(evt, 'eventID')['Timestamp'].timestamp)

    def _tr_bld_data_ebeam(self, values, obj):
        """Translates BldDataEBeam to hummingbird photon energy"""
        photon_energy_ev = -1
        if(isinstance(obj, psana.Bld.BldDataEBeamV6)):
            photon_energy_ev = obj.ebeamPhotonEnergy()
        else:
            peak_current = obj.ebeamPkCurrBC2()
            dl2_energy_gev = 0.001*obj.ebeamL3Energy()

        # If we don't have direct access to photonEnergy
        # we need to calculate it
        if(photon_energy_ev == -1):
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
        add_record(values, 'photonPixelDetectors', 'CsPad2x2', obj.data(), ureg.ADU)

    def _tr_cspad(self, values, obj, evt_key):
        """Translates CsPad to hummingbird numpy array, quad by quad"""
        n_quads = obj.quads_shape()[0]
        for i in range(0, n_quads):
            add_record(values, 'photonPixelDetectors', '%sQuad%d' % (self._s2c[str(evt_key.src())], i),
                       obj.quads(i).data(), ureg.ADU)

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
