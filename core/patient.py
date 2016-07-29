import glob
import os
from core.data import settings
from core.data import depths
from core.data import loading


class Patient(object):
    '''
    Patient metadeta, recording depths, etc.
    '''

    def __init__(self, path, source):
        self.path = os.path.join(path, '')
        self.name = os.path.split(self.path[:-1])[-1]
        self.load_depths()
        self.source = source

    def load_depths(self):
        '''
        Load all files with accepted filetype and grab depths
        '''

        self.files = []
        self.filenames = []
        self.depths = []

        # Get filenames, filepaths and depths
        for i in settings.INPUT_FILETYPES:
            files = glob.glob(os.path.join(self.path, ('*' + i)))
            for j in files:
                fn = os.path.split(j)[-1]
                depth = depths.default_parse(fn)
                # Check that file is supported, if not throw it out
                if depth is not None:
                    self.filenames.append(fn)
                    # Append parsed depth
                    self.depths.append(depth)
                    self.files.append(j)

        # Sort each attribute according to depth if not empty
        if self.depths:
            self.depths = map(float, self.depths)
            zipped = zip(self.depths, self.files, self.filenames)
            depth_sorted = zip(*sorted(zipped, reverse=True))
            [self.depths, self.files, self.filenames] = map(list, depth_sorted)

    def load(self, depth):
        '''
        Load a specific depth into memory
        '''

        if depth not in self.depths:
            return None

        # Standard depth file data ID
        data_id = ('std', self.name, depth)

        if data_id not in self.source.memory.cache:
            idx = self.depths.index(depth)
            ext = self.filenames[idx].split('.')[-1]

            if ext == 'mat':
                data = loading.load_matfile(self.files[idx])
            else:
                return None
            self.source.load(data_id, data)

        return data_id