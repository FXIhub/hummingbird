"""Translates between LCLS events and Hummingbird ones"""
import os
import logging
import sys
if 'sphinx' in sys.modules:
    print sys.path
from backend.event_translator import EventTranslator
from backend.record import addRecord, Record
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
        self._s2c['DetInfo(CxiEndstation.0:Acqiris.0)'] = 'Acqiris 0'
        self._s2c['DetInfo(CxiEndstation.0:Acqiris.1)'] = 'Acqiris 1'

    def nextEvent(self):
        """Grabs the next event and returns the translated version"""
        evt = self.data_source.events().next()
        return EventTranslator(evt, self)

    def eventKeys(self, evt):
        """Returns the translated keys available"""
        native_keys = evt.keys()
        common_keys = set()
        for k in native_keys:
            for c in self.nativeToCommon(k):
                common_keys.add(c)
        # parameters corresponds to the EPICS values
        return list(common_keys)+['parameters']

    def nativeToCommon(self, key):
        """Translates a native key to a hummingbird one"""
        if(key.type() in self._n2c):
            return [self._n2c[key.type()]]
        else:
            return []

    def eventNativeKeys(self, evt):
        """Returns the native keys available"""
        return evt.keys()

    def translate(self, evt, key):
        """Returns a dict of Records that match a given humminbird key"""
        if(key in self._c2n):
            return self.translate_core(evt, key)
        elif(key == 'parameters'):
            return self.trEPICS()
        else:
            # check if the key matches any of the existing keys in the event
            event_keys = evt.keys()
            values = {}
            found = False
            for k in event_keys:
                if(k.key() == key):
                    obj = evt.get(k.type(), k.src(), k.key())
                    found = True
                    addRecord(values, self._s2c[str(k.src())] + ' ['+key+']',
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
                    self.trBldDataFEEGasDetEnergy(values, obj)
                elif(isinstance(obj, psana.Lusi.IpmFexV1)):
                    self.trLusiIpmFex(values, obj, k)
                elif(key == 'photonEnergies'):
                    self.trBldDataEBeam(values, obj)
                elif(isinstance(obj, psana.CsPad2x2.ElementV1)):
                    self.trCsPad2x2(values, obj)
                elif(isinstance(obj, psana.CsPad.DataV2)):
                    self.trCsPad(values, obj, k)
                elif(isinstance(obj, psana.Acqiris.DataDescV1)):
                    self.trAcqiris(values, obj, k)
                elif(isinstance(obj, psana.EventId)):
                    self.trEventID(values, obj)
                elif(isinstance(obj, psana.EvrData.DataV3) or
                     isinstance(obj, psana.EvrData.DataV4)):
                    self.trEventCodes(values, obj)
                else:
                    print type(obj)
                    print k
                    raise RuntimeError('%s not yet supported' % (type(obj)))
        return values

    def event_id(self, evt):
        """Returns an id which should be unique for each
        shot and increase monotonically"""
        return float(self.translate(evt, 'eventID')['Timestamp'].timestamp)

    def trBldDataEBeam(self, values, obj):
        """Translates BldDataEBeam to hummingbird photon energy"""
        photonEnergyeV = -1
        if(isinstance(obj, psana.Bld.BldDataEBeamV6)):
            photonEnergyeV = obj.ebeamPhotonEnergy()
        else:
            peakCurrent = obj.ebeamPkCurrBC2()
            dl2_energy_gev = 0.001*obj.ebeamL3Energy()

        # If we don't have direct access to photonEnergy
        # we need to calculate it
        if(photonEnergyeV == -1):
            ltu_wake_loss = 0.0016293*peakCurrent
            # Spontaneous radiation loss per segment
            sr_loss_per_segment = 0.63*dl2_energy_gev
            # wakeloss in an undulator segment
            wake_loss_per_segment = 0.0003*peakCurrent
            # energy loss per segment
            energy_loss_per_segment = (sr_loss_per_segment +
                                       wake_loss_per_segment)
            # energy in first active undulator segment [GeV]
            energyProfile = (dl2_energy_gev - 0.001*ltu_wake_loss -
                             0.0005*energy_loss_per_segment)
            # Calculate the resonant photon energy of the first active segment
            photonEnergyeV = 44.42*energyProfile*energyProfile

        addRecord(values, 'photon energy', photonEnergyeV, ureg.eV)

    def trBldDataFEEGasDetEnergy(self, values, obj):
        """Translates gas monitor detector to hummingbird pulse energy"""
        # convert from mJ to J
        addRecord(values, 'f_11_ENRC', obj.f_11_ENRC(), ureg.mJ)
        addRecord(values, 'f_12_ENRC', obj.f_12_ENRC(), ureg.mJ)
        addRecord(values, 'f_21_ENRC', obj.f_21_ENRC(), ureg.mJ)
        addRecord(values, 'f_22_ENRC', obj.f_22_ENRC(), ureg.mJ)

    def trLusiIpmFex(self, values, obj, evt_key):
        """Translates Ipm relative pulse energy monitor
        to hummingbird pulse energy"""
        addRecord(values, 'IpmFex '+str(evt_key.src()), obj.sum(), ureg.ADU)

    def trCsPad2x2(self, values, obj):
        """Translates CsPad2x2 to hummingbird numpy array"""
        addRecord(values, 'CsPad2x2', obj.data(), ureg.ADU)

    def trCsPad(self, values, obj, evt_key):
        """Translates CsPad to hummingbird numpy array, quad by quad"""
        nQuads = obj.quads_shape()[0]
        for i in range(0, nQuads):
            addRecord(values, '%s Quad %d' % (self._s2c[str(evt_key.src())], i),
                      obj.quads(i).data(), ureg.ADU)

    def trAcqiris(self, values, obj, evt_key):
        """Translates Acqiris TOF data to hummingbird numpy array"""
        config_store = self.data_source.env().configStore()
        acqConfig = config_store.get(psana.Acqiris.ConfigV1, evt_key.src())
        sampInterval = acqConfig.horiz().sampInterval()
        nChannels = obj.data_shape()[0]
        for i in range(0, nChannels):
            vert = acqConfig.vert()[i]
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
                        sampInterval * numpy.arange(0, elem.nbrSamplesInSeg()))
            values[rec.name] = rec

    def trEventID(self, values, obj):
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

    def trEventCodes(self, values, obj):
        """Translates LCLS event codes into a hummingbird ones"""
        codes = []
        for fifoEvent in obj.fifoEvents():
            codes.append(fifoEvent.eventCode())
        addRecord(values, 'EvrEventCodes', codes)

    def trEPICS(self):
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
            rec.PV = pv
            self._cache[key] = rec
        return self._cache[key]
