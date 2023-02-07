# --------------------------------------------------------------------------------------
# Copyright 2016, Benedikt J. Daurer, Filipe R.N.C. Maia, Max F. Hantke, Carl Nettelblad
# Hummingbird is distributed under the terms of the Simplified BSD License.
# -------------------------------------------------------------------------
import os

import numpy as np

# Loading a test object (binary hummingbird logo)
test_object = np.load(os.path.dirname(os.path.realpath(__file__)) + '/test_object.npy')*1e-2
test_diffraction = np.abs(np.fft.fftshift(np.fft.fft2(test_object)))**2

class Simulation:
    """
    Base class for simulation of typical single particle imaging data. 

    Kwargs:
        hitrate (float): Ratio of hits to be simulated, default is 0.1
        sigma     (int): Sigma used for simulation of detector noise (normal distribution), default is 1
    """
    def __init__(self, hitrate=0.1, sigma=1):
        self.hitrate = hitrate
        self.sigma   = sigma
        self.shape   = (256,256)
        self._is_hit = None

    def next_event(self):
        """Based on a given hitrate, the event is defined to be either a hit or a miss."""
        if np.random.rand() < self.hitrate:
            self._is_hit = True
        else:
            self._is_hit = False

    def get_pattern(self):
        """Returns a diffraction pattern (hit or miss)"""
        noise = np.random.normal(0, self.sigma, self.shape)
        if self._is_hit:
            return test_diffraction + noise
        else:
            return noise

    def get_pulse_energy(self):
        """Returns a randomized pulse energy [J]"""
        return np.random.random()*1e-3

    def get_injector_x(self):
        """Returns a randomized injector position in x [m]"""
        return np.random.random()*1e-6

    def get_injector_y(self):
        """Returns a randomized injector position in y [m]"""
        return np.random.random()*1e-6

    def get_injector_z(self):
        """Returns a randomized injector position in z [m]"""
        return np.random.random()*1e-6
