import os
import sys
import ctypes
import logging
from event_translator import EventTranslator
from IPython.core.debugger import Tracer
import pdb
import psana

class LCLSTranslator(object):    
    def __init__(self, state):
        if('LCLS/DataSource' not in state):
            raise ValueError("You need to set the 'LCLS/DataSource'"
                             " in the configuration")
        else:
            self.ds = psana.DataSource(state['LCLS/DataSource'])

        # Define how to translate between LCLS keys and Hummingbird ones
        self._n2c = {}
        self._n2c[psana.Bld.BldDataFEEGasDetEnergy] = 'pulseEnergy'
        self._n2c[psana.Bld.BldDataEBeamV5] = 'photonEnergy'
        self._n2c[psana.CsPad.DataV2] = 'photonPixelDetector'
        self._n2c[psana.CsPad2x2.ElementV1] = 'photonPixelDetector'
        self._n2c[psana.Acqiris.DataDescV1] = 'ionTOF'

        # Calculate the inverse mapping
        self._c2n = {}
        for k, v in self._n2c.iteritems():
            self._c2n[v] = self._c2n.get(v, [])
            self._c2n[v].append(k)

    def nextEvent(self):
        evt = self.ds.events().next()
        return EventTranslator(evt,self)
        
    def eventKeys(self, evt):
        native_keys = evt.keys()
        common_keys = set()
        for k in native_keys:
            for c in self.nativeToCommon(k):
                common_keys.add(c)
        return list(common_keys)

    def nativeToCommon(self,key):
        if(key.type() in self._n2c):
            return [self._n2c[key.type()]]
        else:
            return []
        
    def eventNativeKeys(self, evt):
        return evt.keys()
        
    def translate(self, evt, key):
        native_keys = self._c2n[key]
        event_keys = evt.keys()
        values = {}
        for k in event_keys:
            if(k.type() in native_keys):
                obj = evt.get(k.type(), k.src())
                if(type(obj) is psana.Bld.BldDataFEEGasDetEnergy):
                    self.trBldDataFEEGasDetEnergy(values, obj)
                elif(type(obj) is psana.Bld.BldDataEBeamV5):
                    self.trBldDataEBeam(values, obj)
                else:
                    raise RuntimeError('%s not yet supported' % (type(obj)))
        return values

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

        values['photon energy in J'] = photonEnergyeV/6.242e+18
                    
    def trBldDataFEEGasDetEnergy(self, values, obj):
        # convert from mJ to J
        values['f_11_ENRC'] = obj.f_11_ENRC()/1000.0
        values['f_12_ENRC'] = obj.f_12_ENRC()/1000.0
        values['f_21_ENRC'] = obj.f_21_ENRC()/1000.0
        values['f_22_ENRC'] = obj.f_22_ENRC()/1000.0        
