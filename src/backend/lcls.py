import os
import sys
import ctypes
import logging
from event_translator import EventTranslator
from record import addRecord, Record
import pdb
import psana
import numpy
import datetime
from pytz import timezone
from . import ureg
from backend import Backend

class LCLSTranslator(object):    
    def __init__(self, state):
        if('LCLS/PsanaConf' in state):
            config_file = Backend.state['_config_dir'] +'/'+ state['LCLS/PsanaConf']
            if(not os.path.isfile(config_file)):
                raise RuntimeError("Could not find LCLS/PsanaConf: %s" %(config_file))
            print config_file
            psana.setConfigFile(config_file)

        if('LCLS/DataSource' not in state):
            raise ValueError("You need to set the 'LCLS/DataSource'"
                             " in the configuration")
        else:
            self.ds = psana.DataSource(state['LCLS/DataSource'])
        

        # Define how to translate between LCLS types and Hummingbird ones
        self._n2c = {}
        self._n2c[psana.Bld.BldDataFEEGasDetEnergy] = 'pulseEnergies'
        self._n2c[psana.Bld.BldDataEBeamV1] = 'photonEnergies'
        self._n2c[psana.Bld.BldDataEBeamV2] = 'photonEnergies'
        self._n2c[psana.Bld.BldDataEBeamV3] = 'photonEnergies'
        self._n2c[psana.Bld.BldDataEBeamV4] = 'photonEnergies'
        self._n2c[psana.Bld.BldDataEBeamV5] = 'photonEnergies'
        self._n2c[psana.Bld.BldDataEBeamV6] = 'photonEnergies'
        self._n2c[psana.CsPad.DataV2] = 'photonPixelDetectors'
        self._n2c[psana.ndarray_int16_2] = 'photonPixelDetectors'
        self._n2c[psana.CsPad2x2.ElementV1] = 'photonPixelDetectors'
        self._n2c[psana.Acqiris.DataDescV1] = 'ionTOFs'
        self._n2c[psana.EventId] = 'eventID'
        self._n2c[psana.EvrData.DataV3] = 'eventCodes'

        # Calculate the inverse mapping
        self._c2n = {}
        for k, v in self._n2c.iteritems():
            self._c2n[v] = self._c2n.get(v, [])
            self._c2n[v].append(k)

        # Define how to translate between LCLS sources and Hummingbird ones
        self._s2c = {}
        self._s2c['DetInfo(CxiDs1.0:Cspad.0)'] = 'Front CsPad'
        self._s2c['DetInfo(CxiDsd.0:Cspad.0)'] = 'Back CsPad'
        self._s2c['DetInfo(CxiEndstation.0:Acqiris.0)'] = 'Acqiris 0'
        self._s2c['DetInfo(CxiEndstation.0:Acqiris.1)'] = 'Acqiris 1'

    def nextEvent(self):
        evt = self.ds.events().next()
        return EventTranslator(evt,self)
        
    def eventKeys(self, evt):
        native_keys = evt.keys()
        common_keys = set()
        for k in native_keys:
            for c in self.nativeToCommon(k):
                common_keys.add(c)
        # parameters corresponds to the EPICS values
        return list(common_keys)+['parameters']

    def nativeToCommon(self,key):
        if(key.type() in self._n2c):
            return [self._n2c[key.type()]]
        else:
            return []
        
    def eventNativeKeys(self, evt):
        return evt.keys()
        
    def translate(self, evt, key):
        if(key in self._c2n):
            values = {}        
            native_keys = self._c2n[key]
            event_keys = evt.keys()
            for k in event_keys:
                if(k.type() in native_keys):
                    obj = evt.get(k.type(), k.src(), k.key())
                    if(type(obj) is psana.Bld.BldDataFEEGasDetEnergy):
                        self.trBldDataFEEGasDetEnergy(values, obj)
                    elif(key == 'photonEnergies'):
                        self.trBldDataEBeam(values, obj)
                    elif(type(obj) is psana.CsPad2x2.ElementV1):
                        self.trCsPad2x2(values, obj)
                    elif(type(obj) is psana.CsPad.DataV2):
                        self.trCsPad(values, obj, k)
                    elif(type(obj) is psana.Acqiris.DataDescV1):
                        self.trAcqiris(values, obj, k)
                    elif(type(obj) is psana.EventId):
                        self.trEventID(values, obj)
                    elif(type(obj) is psana.EvrData.DataV3):
                        self.trEventCodes(values, obj)
                    elif(type(obj) is numpy.ndarray):
                        self.trNdArray(values, obj, k)
                    else:
                        print type(obj)
                        print k
                        raise RuntimeError('%s not yet supported' % (type(obj)))
            return values        
        elif(key == 'parameters'):
            return self.trEPICS()
        else:
            raise RuntimeError('%s not found in event' % (key))

    def id(self, evt):
        return float(self.translate(evt,'eventID')['Timestamp'].timestamp)

    def trBldDataEBeam(self, values, obj):
        photonEnergyeV = -1
        if(type(obj) is psana.Bld.BldDataEBeamV6):
            photonEnergyeV = obj.ebeamPhotonEnergy()
        else:
            peakCurrent = obj.ebeamPkCurrBC2()
            DL2energyGeV = 0.001*obj.ebeamL3Energy();
            
        # If we don't have direct access to photonEnergy
        # we need to calculate it
        if(photonEnergyeV == -1):
            LTUwakeLoss = 0.0016293*peakCurrent;
            # Spontaneous radiation loss per segment
            SRlossPerSegment = 0.63*DL2energyGeV;
            # wakeloss in an undulator segment
            wakeLossPerSegment = 0.0003*peakCurrent;
            # energy loss per segment
            energyLossPerSegment = SRlossPerSegment + wakeLossPerSegment;
            # energy in first active undulator segment [GeV]
            energyProfile = DL2energyGeV - 0.001*LTUwakeLoss - 0.0005*energyLossPerSegment;
            # Calculate the resonant photon energy of the first active segment
            photonEnergyeV = 44.42*energyProfile*energyProfile;

        addRecord(values, 'photon energy', photonEnergyeV, ureg.eV)
                    
    def trBldDataFEEGasDetEnergy(self, values, obj):
        # convert from mJ to J
        addRecord(values, 'f_11_ENRC', obj.f_11_ENRC(), ureg.mJ)
        addRecord(values, 'f_12_ENRC', obj.f_12_ENRC(), ureg.mJ)
        addRecord(values, 'f_21_ENRC', obj.f_21_ENRC(), ureg.mJ)
        addRecord(values, 'f_22_ENRC', obj.f_22_ENRC(), ureg.mJ)

    def trCsPad2x2(self, values, obj):
        addRecord(values, 'CsPad2x2', obj.data(), ureg.ADU)

    def trCsPad(self, values, obj, evt_key):
        nQuads = obj.quads_shape()[0]
        for i in range(0, nQuads):
            addRecord(values, '%s Quad %d' % (self._s2c[str(evt_key.src())], i),
                      obj.quads(i).data(), ureg.ADU)

    def trAcqiris(self, values, obj, evt_key):
        acqConfig = self.ds.env().configStore().get(psana.Acqiris.ConfigV1, evt_key.src())
        horiz = acqConfig.horiz();
        sampInterval = horiz.sampInterval();
        
        nChannels = obj.data_shape()[0]
        print obj.data_shape()
        for i in range(0, nChannels):
            vert = acqConfig.vert()[i]
            slope = vert.slope()
            offset = vert.offset()

            seg = 0
            elem = obj.data(i)
            timestamps = elem.timestamp();
            timestamp = timestamps[seg].value();
            trigTime = timestamps[seg].pos();
            nbrSamplesInSeg = elem.nbrSamplesInSeg();
            waveforms = elem.waveforms();
            raw = waveforms[seg]
            if(nbrSamplesInSeg == 0):
                logging.warning("Warning: TOF data for detector %s is missing.\n" % evt_key);
            data = raw*slope - offset
            time = timestamp + sampInterval * numpy.arange(0,nbrSamplesInSeg)

            rec = Record('%s Channel %d' %(self._s2c[str(evt_key.src())],i),
                         data, ureg.V)
            rec.time = time
            values[rec.name] = rec

    def trEventID(self, values, obj):
        timestamp = obj.time()[0]+obj.time()[1]*1e-9
        time = datetime.datetime.fromtimestamp(timestamp,tz=timezone('utc'))
        time = time.astimezone(tz=timezone('US/Pacific'))
        rec = Record('Timestamp', time, ureg.s)
        time = datetime.datetime.fromtimestamp(obj.time()[0])
        rec.datetime64 = numpy.datetime64(time,'ns')+obj.time()[1]        
        rec.fiducials = obj.fiducials()
        rec.run = obj.run()
        rec.ticks = obj.ticks()
        rec.vector = obj.vector()
        rec.timestamp = timestamp
        values[rec.name] = rec

    def trEventCodes(self, values, obj):        
        codes = []
        for i,fifoEvent in enumerate(obj.fifoEvents()):
            codes.append(fifoEvent.eventCode())

        addRecord(values, 'EvrEventCodes', codes)

    def trNdArray(self, values, obj, evtKey):
        addRecord(values, str(evtKey.src()) + evtKey.key(), obj, ureg.ADU)

    def trEPICS(self):
        return EPICSdict(self.ds.env().epicsStore())

class EPICSdict(object):
    def __init__(self, epics):
        self.epics = epics        
        self._cache = {}

    def keys(self):
        return self.epics.pvNames() + self.epics.aliases()

    def __getitem__(self, key):
        if(key not in self._cache):
            pv = self.epics.getPV(key)
            if(pv is None):
                raise KeyError('%s is not a valid EPICS key' %(key))
            rec = Record(key, pv.value(0))
            rec.PV = pv
            self._cache[key] = rec
        return self._cache[key]
