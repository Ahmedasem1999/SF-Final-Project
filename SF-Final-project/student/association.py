# ---------------------------------------------------------------------
# Project "Track 3D-Objects Over Time"
# Copyright (C) 2020, Dr. Antje Muntzinger / Dr. Andreas Haja.
#
# Purpose of this file : Data association class with single nearest neighbor association and gating based on Mahalanobis distance
#
# You should have received a copy of the Udacity license together with this program.
#
# https://www.udacity.com/course/self-driving-car-engineer-nanodegree--nd013
# ----------------------------------------------------------------------
#

# imports
import numpy as np
from scipy.stats.distributions import chi2
import math

# add project directory to python path to enable relative imports
import os
import sys
PACKAGE_PARENT = '..'
SCRIPT_DIR = os.path.dirname(os.path.realpath(os.path.join(os.getcwd(), os.path.expanduser(__file__))))
sys.path.append(os.path.normpath(os.path.join(SCRIPT_DIR, PACKAGE_PARENT)))

import misc.params as params 

class Association:
    '''Data association class with single nearest neighbor association and gating based on Mahalanobis distance'''
    def __init__(self):
        self.association_matrix = np.matrix([])
        self.unassigned_tracks = []
        self.unassigned_meas = []
        
    def associate(self, track_list, meas_list, KF):
             
        ############
        # TODO Step 3: association:
        # - replace association_matrix with the actual association matrix based on Mahalanobis distance (see below) for all tracks and all measurements
        # - update list of unassigned measurements and unassigned tracks
        ############
        
        # the following only works for at most one track and one measurement
        self.association_matrix = np.matrix([]) # reset matrix
        self.unassigned_tracks = [] # reset lists
        self.unassigned_meas = []
        track_matrix = []  # start with a blank temporary association matrix.
        
        if len(meas_list) > 0:
            self.unassigned_meas = np.arange(len(meas_list)).tolist()
        if len(track_list) > 0:
            self.unassigned_tracks = np.arange(len(track_list)).tolist()
        
        if len(meas_list) > 0 and len(track_list) > 0:
            # iterate over track list
            for track in track_list:
                # for each track define an empty list to store distances from each measurement
                dists = []
                # iterate over each measurement
                for meas in meas_list:
                    # compute Mahalanobis distance
                    mh_dist = self.MHD(track, meas, KF)
                    # check if measurement lies inside gate
                    if self.gating(mh_dist, meas.sensor):
                        dists.append(mh_dist)
                    else:
                        # set distance as infinite
                        dists.append(np.inf)
                track_matrix.append(dists)

            self.association_matrix = np.matrix(track_matrix)
        
        ############
        # END student code
        ############ 
                
    def get_closest_track_and_meas(self):
        ############
        # TODO Step 3: find closest track and measurement:
        # - find minimum entry in association matrix
        # - delete row and column
        # - remove corresponding track and measurement from unassigned_tracks and unassigned_meas
        # - return this track and measurement
        ############

        # the following only works for at most one track and one measurement        
        ind_track, ind_meas = np.unravel_index(self.association_matrix.argmin(), self.association_matrix.shape)

        # delete row and column
        self.association_matrix = np.delete(self.association_matrix, ind_track, axis=0)
        self.association_matrix = np.delete(self.association_matrix, ind_meas, axis=1)

        # from the unassigned_tracks and unassigned_meas folders, delete the associated track and measurement.
        update_track = self.unassigned_tracks[ind_track]
        update_meas = self.unassigned_meas[ind_meas]

        self.unassigned_tracks.remove(update_track)
        self.unassigned_meas.remove(update_meas)

        return update_track, update_meas
            
        ############
        # END student code
        ############     

    def gating(self, MHD, sensor): 
        ############
        # TODO Step 3: return True if measurement lies inside gate, otherwise False
        ############
        
        df = sensor.dim_meas - 1
        return MHD < chi2.ppf(params.gating_threshold, df=df)  
        
        ############
        # END student code
        ############ 
        
    def MHD(self, track, meas, KF):
        ############
        # TODO Step 3: calculate and return Mahalanobis distance
        ############
        
        y = KF.gamma(track, meas)
        S = KF.S(track, meas, meas.sensor.get_H(track.x))
        
        return math.sqrt(y.transpose() * S.I * y)
        
        ############
        # END student code
        ############ 
    
    def associate_and_update(self, manager, meas_list, KF):
        # associate measurements and tracks
        self.associate(manager.track_list, meas_list, KF)
    
        # update associated tracks with measurements
        while self.association_matrix.shape[0]>0 and self.association_matrix.shape[1]>0:
            
            # search for next association between a track and a measurement
            ind_track, ind_meas = self.get_closest_track_and_meas()
            if np.isnan(ind_track):
                print('---no more associations---')
                break
            track = manager.track_list[ind_track]
            
            # check visibility, only update tracks in fov    
            if not meas_list[0].sensor.in_fov(track.x):
                continue
            
            # Kalman update
            print('update track', track.id, 'with', meas_list[ind_meas].sensor.name, 'measurement', ind_meas)
            KF.update(track, meas_list[ind_meas])
            
            # update score and track state 
            manager.handle_updated_track(track)
            
            # save updated track
            manager.track_list[ind_track] = track
            
        # run track management 
        manager.manage_tracks(self.unassigned_tracks, self.unassigned_meas, meas_list)
        
        for track in manager.track_list:            
            print('track', track.id, 'score =', track.score)