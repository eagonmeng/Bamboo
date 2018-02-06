import glob
import os
from core.data import settings
from core.data import depths
from core.data import loading
import numpy as np
import colorsys


class Patient(object):
    '''
    Patient metadeta, recording depths, etc.
    '''

    def __init__(self, path, source):
        self.path = os.path.join(path, '')
        self.name = os.path.split(self.path[:-1])[-1]
        self.load_depths()
        self.source = source

        # Annotation data
        self.patient_label = []
        self.depth_labels = {}

        self.load_annotation_labels()

        # Hash rates
        self.hashrates = None
        self.hash_depth_list = None
        self.load_hashrates()

        # Load colormap
        self.annotation_color_map()

    def load_depths(self):
        '''
        Load all files with accepted filetype and grab depths
        '''

        self.files = []
        self.depths = []

        # Get filenames, filepaths and depths
        for i in settings.INPUT_FILETYPES:
            files = glob.glob(os.path.join(self.path, ('*' + i)))
            for j in files:
                fn = os.path.split(j)[-1]
                depth, file_nr = depths.default_parse(fn)
                # Check that file is supported, if not throw it out
                if depth is not None:
                    if depth not in self.depths:
                        # Append parsed depth
                        self.depths.append(depth)
                        self.files.append([j])
                    else:
                        idx = self.depths.index(depth)
                        self.files[idx].append(j)

        # Sort each attribute according to depth if not empty
        if self.depths:
            self.depths = map(float, self.depths)
            zipped = zip(self.depths, self.files)
            depth_sorted = zip(*sorted(zipped, reverse=True))
            [self.depths, self.files] = map(list, depth_sorted)

    def load(self, depth):
        '''
        Load a specific depth into memory
        '''

        if depth not in self.depths:
            return None

        # Standard depth file data ID
        data_id = ('std', self.name, depth)

        if data_id not in self.source.cache:
            idx = self.depths.index(depth)
            current = self.files[idx]
            ext = current[0].split('.')[-1]

            if ext == 'mat':
                if len(current) == 1:
                    data = loading.load_matfile(current[0])
                else:
                    data = self.load_multiple(current)

            else:
                return None
            self.source.load(data_id, data)

        return data_id

    def load_multiple(self, data):
        data = sorted(data)
        return loading.load_matfile(data[0])


    '''
    Annotation methods
    '''

    def load_annotation_labels(self):
        # Load filenames
        filename = settings.annotation_name % self.name
        filepath = os.path.join(settings.annotation_path, filename)
        if os.path.isfile(filepath):
            with open(filepath, 'rb') as csvfile:
                self.patient_label = csvfile.readline().splitlines()[0].split(',')
                for line in csvfile:
                    labels = line.splitlines()[0].split(',')

                    # Format for key: Depth, Channel Nr.
                    label_id = (float(labels[0]), int(labels[1]))
                    self.depth_labels[label_id] = labels[2:]

    # Create annotation color map
    def annotation_color_map(self):
        self.colormap = {}
        for i, label in enumerate(settings.continuous_labels):
            transform = (i)
            hue = transform / float(len(settings.continuous_labels))
            color = np.array(colorsys.hsv_to_rgb(hue, .7, 1)) * 255
            self.colormap[label] = np.rint(color).astype(int)

    # Compute annotation status bar
    def get_annotation_markers(self, channel):
        # Loop through all depths
        bar = []
        dots = []
        current_label = None
        start = None
        prev = None

        # Convert channel to channel_nr
        channel_nr = self.source.get_channel_number(channel)

        for depth in self.depths:
            label_id = (depth, channel_nr)
            if label_id in self.depth_labels:
                labels = set(self.depth_labels[label_id])
                
                # Find the union of the labels
                area = set(settings.continuous_labels).intersection(labels)
                dot = set(settings.dot_labels).intersection(labels)

                # Append all the dot notifications
                if len(dot) > 0:
                    dots.append((depth, list(dot)))

                # Calculate the bar component
                if len(area) == 1:
                    # Start not being None means we're in a bar
                    if start is not None:

                        # Extend if we're in the same label
                        if area.pop() == current_label:
                            prev = depth
                            # Skip over while necessary
                            continue

                    # Otherwise create a new bar
                    else:
                        start = depth
                        prev = depth
                        current_label = area.pop()
                        # Skip over while necessary
                        continue

            # If we haven't continued, that means we need to break
            if start is not None:
                # Format is ((start, end), label)
                bar.append(((start, prev), current_label, self.colormap[current_label]))
                start = None
                current_label = None
                prev = None

        # Wrap up last iteration
        if start is not None:
            bar.append(((start, depth), current_label, self.colormap[current_label]))

        return (bar, dots)

    '''
    Preprocessing methods
    '''

    def load_hashrates(self):
        # Load filenames
        filename = settings.hashrates_filename % self.name
        filepath = os.path.join(self.source.path, settings.preprocessing_path, settings.hashrates_folder, filename)
        if os.path.isfile(filepath):
            self.hashrates = {}
            self.hash_depth_list = {}
            with open(filepath, 'rb') as csvfile:
                for line in csvfile:
                    current = line.splitlines()[0].split(',')
                    self.hashrates[current[0]] = {}
                    self.hash_depth_list[current[0]] = []
                    for idx in range((len(current)-1)/2):
                        self.hashrates[current[0]][float(current[idx*2+1])] = float(current[idx*2+2])
                        self.hash_depth_list[current[0]].append(float(current[idx*2+2]))

                    # Normalize depths
                    d_list = np.array(self.hash_depth_list[current[0]])
                    d_list = d_list / float(np.max(d_list))
                    self.hash_depth_list[current[0]] = dict(zip(self.depths, d_list))

