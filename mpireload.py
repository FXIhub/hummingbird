#!/usr/bin/env python
"""A script to relaod hummingbird when running in mpi mode"""
import os, signal

with open('.pid', 'r') as file:
     pid = int(file.read())
os.kill(pid, signal.SIGUSR1)
