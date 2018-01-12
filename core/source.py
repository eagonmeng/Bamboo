from patient import Patient
from core.data import settings
import core.data
import os
import re
import csv
from tqdm import tqdm
import numpy as np


class Source(object):
    '''
    Core logic and data analysis access
    Handles data read and write requests
    '''

    def __init__(self, path=settings.source_path):
        # All the stuffs
        self.cache = {}

        # Settings
        self.init_settings()

        # Add separator if necessary
        self.path = os.path.join(path, '')
        self.patients = {}

        # Simple catch for bad paths
        if not os.path.isdir(self.path):
            print('Directory does not exist: ' + self.path)
            self.path = ''
            self.patient_folders = []
        else:
            self.patient_folders = next(os.walk(path))[1]

            # Remove preprocessing folder
            if settings.preprocessing_path in self.patient_folders:
                self.patient_folders.remove(settings.preprocessing_path)

            # Initialize all patient objects
            for i in self.patient_folders:
                patient = Patient(
                    os.path.join(self.path, i, ''),
                    self)
                self.patients[i] = patient

                # Preprocess if necessary   
                if settings.preprocess_hashes and patient.hashrates is None:
                    self.save_patient_hashrates(patient)



        # Annotation stuffs
        self.list_items = list(settings.depth_labels)

        # Global signals unit
        self.s = core.data.global_signals.SourceSignal()

    def init_settings(self):
        self.only_data_channels = settings.only_data_channels
        self.only_spike_channels = settings.only_spike_channels

        # Load appropriate labels
        self.patient_labels = settings.patient_labels
        self.depth_labels = settings.depth_labels

    def load(self, data_id, data):
        '''
        Function to cache
        '''
        self.cache[data_id] = data

    def write(self, storage, params):
        '''
        Function to write from shared memory to disk
        '''
        pass

    def get_channels(self, patient, src_depth_idx=0):
        '''
        Function to return list of channels
        '''

        # Test for existence of patient and if they have depths
        try:
            cur_patient = self.patients[patient]
        except KeyError:
            return []
        if not cur_patient.depths:
            return []

        # If default src_depth_idx=0, assume all channels can be found
        src_depth = cur_patient.depths[src_depth_idx]
        data_id = ('channels', patient, src_depth)
        if data_id not in self.cache:
            file_id = cur_patient.load(src_depth)

            # Load raw channel names
            channels = self.cache[file_id].keys()

            # Parse channels
            channels = core.data.CleanChannels(channels)

            self.load(data_id, channels)

        return self.cache[data_id]

    '''
    Custom methods to be separated into another file and
    automatically added on to source by setting attributes
    '''
    def parse_data_channels(self, channels):
        remove = set(channels) - set(settings.data_channels)
        return sorted(list(set(channels) - remove))

    def parse_spike_channels(self, channels):
        remove = set(channels) - set(settings.spike_channels)
        return sorted(list(set(channels) - remove))

    def get_parallel_channels(self, channel):
        for reg in settings.reg_data:
            success = re.match(reg, channel)
            if success:
                base = success.group(1)
                return [base + str(i) for i in [1, 2, 3]]
        return []

    def get_channel_number(self, channel):
        if channel in settings.data_channels:
            return int(channel[-2:])
        else:
            return 0

    '''
    Methods to save data to files
    '''

    # Save annotations
    def save_patient_annotation(self, patient):
        if patient not in self.patients:
            print('Patient not found!')
            return

        filename = settings.annotation_name % patient

        # Create directory if non-existent
        if not os.path.exists(settings.annotation_path):
            os.makedirs(settings.annotation_path)

        path = os.path.join(settings.annotation_path, filename)
        with open(path, 'wb') as out:
            csv_writer = csv.writer(out, delimiter=',')
            csv_writer.writerow(self.patients[patient].patient_label)
            for key, value in self.patients[patient].depth_labels.iteritems():
                csv_writer.writerow([key[0], key[1]] + value)

    # Save hash rates
    def save_patient_hashrates(self, patient):
        if patient.name not in self.patients:
            print('Patient not found!')
            return

        hashes = {}
        print('Calculating hashrates for patient: %s' % patient.name)

        # Find the appropriate channels in this patient
        spike_channels = []
        file = self.cache[patient.load(patient.depths[0])]
        for channel in settings.spike_channels:
            if channel in file:
                spike_channels.append(channel)
        spike_channels.sort()

        # Compute noisefloor
        noise_floor = {}
        with tqdm(total=(len(spike_channels)*len(patient.depths))) as pbar:
            for channel in spike_channels:
                noise_floor[channel] = []
                for depth in patient.depths:
                    data = self.cache[patient.load(depth)][channel]    
                    noise_floor[channel].append(core.data.noise_floor(data, settings.data_hz, depth))
                    pbar.update()
        for channel in noise_floor:
            noise_floor[channel] = np.nanmedian(noise_floor[channel])

        # Compute hashrates
        for channel in spike_channels:
            hashes[channel] = []
            idx = 0
            for depth in patient.depths:
                data = self.cache[patient.load(depth)][channel]
                hashes[channel].append(depth)
                hashes[channel].append(core.data.hash_rate(data, settings.data_hz, depth, noise_floor[channel]))

        # for depth in patient.depths:
        #     data_id = patient.load(depth)
        #     file = self.cache[data_id]
        #     for channel in spike_channels:
        #         data = file[channel]
        #         if channel not in hashes:
        #             hashes[channel] = []
        #         hashes[channel].append(float(depth))
        #         hashes[channel].append(core.data.hash_rate(data, settings.data_hz, noise_floor[channel]))

        # Save to file
        filename = settings.hashrates_filename % patient.name
        folderpath = os.path.join(self.path, settings.preprocessing_path, settings.hashrates_folder)
        if not os.path.exists(folderpath):
            os.makedirs(folderpath)

        path = os.path.join(folderpath, filename)
        with open(path, 'wb') as out:
            csv_writer = csv.writer(out, delimiter=',')
            for key, value in hashes.items():
                csv_writer.writerow([key] + value)

        # Load into patient
        patient.hashrates = {}
        patient.hash_depth_list = {}
        for channel, hashvalues in hashes.items():
            patient.hashrates[channel] = {}
            patient.hash_depth_list[channel] = []
            for idx in range(len(hashvalues)/2):
                patient.hashrates[channel][hashvalues[idx*2]] = hashvalues[idx*2+1]
                patient.hash_depth_list[channel].append(hashvalues[idx*2+1])

            # Normalize the depth list
            d_list = np.array(patient.hash_depth_list[channel])
            d_list = d_list / float(np.max(d_list))
            patient.hash_depth_list[channel] = dict(zip(patient.depths, d_list))
