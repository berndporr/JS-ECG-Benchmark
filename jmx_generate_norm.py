#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
This code will run all subjects, all experiments, all leads recordings through
all detectors or a single detector as required.
For each recording (for which there are annotations) passed through a detector
the detection locations will be saved, and then these passed for interval
analysis, where jitter, missed beats and extra/spurious detections are
identified. Jitter is taken as the difference (in samples) between the
annotated interval and the detected interval, and is not truly HRV as it is
calculated not just at rest.
For each recording (as above) passed through a detector, the jitter, missed
beat sample locations and extra/spurious detection locations are all saved as
seperate csv files. This means that all 'raw' interval analysis data is
available for subsequent benchmarking, plotting or analysis by lead type,
experiment, etc as desired and has not been combined in a way which results in
loss of information.
"""

import sys
import os
import numpy as np
import json
from ecg_gudb_database import GUDb
from ecgdetectors import Detectors
import pathlib # For local file use
from multiprocessing import Process

# The JMX analysis for a detector
import jmx_analysis

# directory where the results are stored
resultsdir = "results"

try:
    os.mkdir(resultsdir)
except OSError as error:
    pass

fs = 250 #sampling rate

detectors = Detectors(fs) # Initialise detectors for 250Hz sample rate (GUDB)

current_dir = pathlib.Path(__file__).resolve()

recording_leads = "einthoven_ii"
experiment = "sitting"

jmx_acc = np.empty((0,4))
jmx_norm = np.empty((0,4))

f = open("norm_calc.tsv","w")

for detector in detectors.detector_list:

    detectorname = detector[1].__name__
    detectorfunc = detector[1]
    
    print("Processing:",detector[0])

    for subject_number in range(0, 25): # loop for all subjects

        print("Analysing subject {}, {}, {}, {}".format(subject_number, experiment, recording_leads, detector[0]))

        # creating class which loads the experiment

        # For online GUDB access
        ecg_class = GUDb(subject_number, experiment) 

        # getting the raw ECG data numpy arrays from class
        chest_strap_V2_V1 = ecg_class.cs_V2_V1
        einthoven_i = ecg_class.einthoven_I
        einthoven_ii = ecg_class.einthoven_II
        einthoven_iii = ecg_class.einthoven_III

        # getting filtered ECG data numpy arrays from class
        ecg_class.filter_data()
        chest_strap_V2_V1_filt = ecg_class.cs_V2_V1_filt
        einthoven_i_filt = ecg_class.einthoven_I_filt
        einthoven_ii_filt = ecg_class.einthoven_II_filt
        einthoven_iii_filt = ecg_class.einthoven_III_filt

        data = einthoven_ii

        if ecg_class.anno_cables_exists:
            data_anno = ecg_class.anno_cables
            exist=True

        #%% Detection

        ### Applying detector to each subject ECG data set then correct for mean detector
        # delay as referenced to annotated R peak position
        # Note: the correction factor for each detector doesn't need to be exact,
        # but centres the detection point for finding the nearest annotated match
        # It may/will be different for different subjects and experiments

        if exist==True: # only proceed if an annotation exists
            detected_peaks = detectorfunc(data) # call detector class for current detector
            interval_results = jmx_analysis.evaluate(detected_peaks, data_anno, fs) # perform interval based analysis
            avgjit = np.average(interval_results[jmx_analysis.key_jitter])
            jmx = np.array([avgjit,
                            interval_results[jmx_analysis.key_missed],
                            interval_results[jmx_analysis.key_extra],
                            interval_results[jmx_analysis.key_sensitivity],
                            
            ])
            jmx_acc = np.vstack( (jmx_acc,jmx) )
            jmx_norm = np.average(jmx_acc,axis=0)
            print("J = {} sec, M = {} beats, X = {} beats, S = {}".format(jmx_norm[0],jmx_norm[1],jmx_norm[2],jmx_norm[3]))
            f.write("{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n".format(jmx[0],jmx[1],jmx[2],jmx[3],
                                                      jmx_norm[0],jmx_norm[1],jmx_norm[2],jmx_norm[3]))
            f.flush()
print("FINAL: J = {} sec, M = {} beats, X = {} beats".format(jmx_norm[0],jmx_norm[1],jmx_norm[2]))
f.close()
