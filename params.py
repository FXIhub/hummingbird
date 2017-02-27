import csv
import numpy as np
import h5py

def read_params(filename, run_nr):
    params = {}
    with open(filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        params = {}
        for row in reader:
            if np.int16(row["RunNr"]) == run_nr:
                params['RunType'] = str(row["RunType"])
                params['hitscoreThreshold'] = np.int(row["HitscoreThreshold"])
                params['darkNr'] = np.int(row["DarkNr"])
    return params

def run_numbers(filename, runtype):
    run_numbers = []
    with open(filename) as f:
        reader = csv.DictReader(f, delimiter=';')
        for row in reader:
            if str(row["RunType"]) == runtype:
                run_numbers.append(np.int(row["RunNr"]))
    return run_numbers

            
            
