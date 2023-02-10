# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
from __future__ import (absolute_import,  # Compatibility with python 2 and 3
                        print_function)

import numpy as np

from hummingbird import ipc
from hummingbird.backend import add_record, ureg


def averagePulseEnergy(evt, records, outkey="averagePulseEnergy"):
    """Averages across given pulse energies and adds it to evt["analysis"][outkey].

    Args:
        :evt:      The event variable
        :records:  A dictionary of pulse energy :func:`~Record` objects

    Kwargs:
        :outkey(str):  Data key of resulting :func:`~backend.Record`, default is 'averagePulseEnergy'

    :Authors:
        Filipe Maia,
        Benedikt J. Daurer
    """
    pulseEnergy = []
    for pE in records.values():
        if (pE.unit == ureg.mJ):
            pulseEnergy.append(pE.data)
    if pulseEnergy:
        add_record(evt["analysis"], "analysis", outkey, np.mean(pulseEnergy), ureg.mJ)

def averagePhotonEnergy(evt, records, outkey="averagePhotonEnergy"):
    """Averages across given photon energies and adds it to evt["analysis"][outkey].

    Args:
        :evt:      The event variable
        :records:  A dictionary of photon energy :func:`~backend.Record` objects

    Kwargs:
        :outkey(str):  Data key of resulting :func:`~backend.Record`, default is 'averagePhotonEnergy'

    :Authors:
        Benedikt J. Daurer
    """
    photonEnergy = []
    for pE in records.values():
        if (pE.unit == ureg.eV):
            photonEnergy.append(pE.data)
    if photonEnergy:
        add_record(evt["analysis"], "analysis", outkey, np.mean(photonEnergy), ureg.eV)
        
def printPulseEnergy(pulseEnergies):
    """Expects a dictionary of pulse energy :func:`~backend.Record` objects and prints pulse energies to screen."""
    for k,v in pulseEnergies.items():
        print("%s = %s" % (k, (v.data*v.unit)))

def printPhotonEnergy(photonEnergies):
    """Expects a dictionary of photon energy :func:`~backend.Record` objects and prints photon energies to screen."""
    for k,v in photonEnergies.items():
        print("%s = %s" % (k, v.data*v.unit))
