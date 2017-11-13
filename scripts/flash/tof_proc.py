#!/usr/bin/env python

import numpy as np
import h5py as h
import matplotlib
import matplotlib.pyplot as plt
import sys, os, re, shutil, subprocess, time
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-f", "--file", action="store", type="string", dest="inputFile", help="Input H5 file with TOF data", metavar="FILENAME", default="")
parser.add_option("-m", "--motor", action="store", type="string", dest="motorName", help="Motorname to plot TOF data against (default: injectory)", metavar="NAME", default="injectory")
parser.add_option("-r", "--run", action="store", type="int", dest="runNumber", help="Run number with TOF data", metavar="NUMBER", default=0)
parser.add_option("-l", "--level", action="store", type="int", dest="outputLevel", help="Output level in input H5 file (default: 3)", metavar="NUMBER", default=3)

(options, args) = parser.parse_args()

########################################################
original_dir = os.getcwd() + '/'
work_dir = "/asap3/flash/gpfs/bl1/2017/data/11001733/processed/hummingbird_tof/"

if options.inputFile != '' or options.runNumber != 0:
        # open input cxidb file
        if options.inputFile != '':
                print "Reading TOF data from %s%s ..." % (work_dir, options.inputFile)
                f = h.File(work_dir + options.inputFile, "r")
        else:
                fname = "r%04d_ol%d.h5" % (options.runNumber, options.outputLevel)
                print "Reading TOF data from %s%s ..." % (work_dir, fname)
                f = h.File(work_dir + fname, "r")
        gmdPath = "/entry_1/FEL/gmd" 
        tdPath = "/entry_1/detector_2/data"
        injectorPath = "/entry_1/motors/%s" % options.motorName
        
        # sanity check
        for p in [gmdPath, tdPath, injectorPath]:
                if (not f.get(p)):
                        print "\t'%s' does not exist, aborting..." % (p)
                        sys.exit(1)
        td = f[tdPath][:]
        print "\tfound %d time traces with %d bins" % (td.shape[0], td.shape[1])
        gmd = f[gmdPath][:]
        gmd_is_nan = np.isnan(gmd)
        gmd_is_not_nan = np.abs(gmd_is_nan.astype(np.int) - 1).astype(np.bool)
        gmd_without_nan = gmd[gmd_is_not_nan]
        print "\tfound %d gmd values (including %d NaNs) between %.2f and %.2f (%.2f +/- %.2f)" % (gmd.shape[0], gmd_is_nan.sum(), np.nanmin(gmd), np.nanmax(gmd), np.nanmean(gmd), np.nanstd(gmd))
        injector = f[injectorPath][:]
        injector_unique = np.sort(list(set(injector)))
        print "\tfound %d injector (%d unique) values between %.2f and %.2f (%.2f +/- %.2f)" % (injector.shape[0], injector_unique.shape[0], injector.min(), injector.max(), injector.mean(), injector.std())
        #print injector_unique
        
        # histogram gmd energies
        gmd_bins = np.arange(np.floor(gmd_without_nan.min()) - 1., np.ceil(gmd_without_nan.max()) + 3., 1.) - 0.5
        gmd_hist, gmd_bins = np.histogram(gmd_without_nan, bins=gmd_bins)
        gmd_bins_center = np.array([(gmd_bins[i] + gmd_bins[i + 1])/2 for i in range(len(gmd_bins) - 1)])

        # histogram injector values
        injector_delta = 0.05
        injector_bins = np.arange(injector.min() - injector_delta, injector.max() + 3*injector_delta, injector_delta) - injector_delta/2.
        injector_hist, injector_bins = np.histogram(injector, bins=injector_bins)
        injector_bins_center = np.array([(injector_bins[i] + injector_bins[i + 1])/2 for i in range(len(injector_bins) - 1)])

        # plot histogram
        fig = plt.figure(num=1, figsize=(11.5, 5.0), dpi=100, facecolor='w', edgecolor='k')
        fig.suptitle("Histograms")
        ax1 = fig.add_subplot(121)
        ax1.set_title("GMD energies (uJ)")
        ax1.set_xlabel("GMD (uJ)")
        ax1.set_ylabel("number of hits")
        ax1.plot(gmd_bins_center, gmd_hist)

        ax2 = fig.add_subplot(122)
        ax2.set_title("%s positions (mm)" % options.motorName)
        ax2.set_xlabel("%s (mm)" % options.motorName)
        ax2.set_ylabel("number of hits")
        ax2.plot(injector_bins_center, injector_hist)
        plt.show(block=False)

        while True:
                try:
                        gmd_low = np.float(input("Enter lower limit for GMD energies (uJ): "))
                        ax1.axvline(x=gmd_low, color='k', linestyle='--')
                        plt.draw()
                        gmd_high = np.float(input("Enter upper limit for GMD energies (uJ): "))
                        ax1.axvline(x=gmd_high, color='k', linestyle='--')
                        plt.draw()
                        break
                except ValueError as err:
                        print err
        
        gmd[gmd_is_nan] = -1
        data_to_use = gmd_is_not_nan & (gmd >= gmd_low) & (gmd <= gmd_high)
        print "\taveraging %d / %d traces (%.1f%%)" % (data_to_use.sum(), len(data_to_use), data_to_use.sum()*100./len(data_to_use))
        td_avg = np.zeros((injector_unique.shape[0], td.shape[1]))
        n = 0
        for p in injector_unique:
                td_avg[n] = np.mean(td[data_to_use & (injector == p)], axis=0)
                n += 1
        
        # plot TOF data
        fig = plt.figure(num=2, figsize=(11.5, 5.0), dpi=100, facecolor='w', edgecolor='k')
        fig.suptitle("TOF")
        ax1 = fig.add_subplot(121)
        ax1.set_title("TOF traces")
        ax1.set_xlabel("flight time (arb. u.)")
        ax1.set_ylabel("ion trace (mV)")
        ax1.plot(np.mean(td[data_to_use], axis=0), 'k', label="selected")
        ax1.plot(np.mean(td, axis=0), 'k--', label="all")
        cmap = plt.get_cmap('plasma')
        colors = [cmap(n) for n in np.linspace(0, 1, len(injector_unique))]
        n = 0
        for p in injector_unique:
                ax1.plot(td_avg[n] - (n + 1)*100, color=colors[n], label="%.2f mm" % p)
                n += 1
        #plt.legend(loc='best')
        #plt.legend(bbox_to_anchor=(1.05, 1), loc=2, borderaxespad=0.)
        plt.legend(loc=4)

        ax2 = fig.add_subplot(122)
        ax2.set_title("TOF trace vs %s" % options.motorName)
        #ax2.imshow(td_avg, interpolation='nearest', origin='lower', extent=[0, td_avg.shape[1], injector_unique[0], injector_unique[-1]], aspect="auto")
        im = ax2.imshow(td_avg, interpolation='nearest', origin='lower', extent=[0, td_avg.shape[1], injector_bins[1], injector_bins[-3]], aspect="auto", cmap=plt.get_cmap("viridis"))
        plt.colorbar(im, pad=0.01)
        plt.show()
else:
        print "No input file or run specified, aborting..."
        sys.exit(1)
