from patient import Patient
from core.data import settings
import os
from matplotlib.figure import Figure


class Source(object):
    '''
    Core logic and data analysis access
    Handles data read and write requests
    '''

    def __init__(self, path=settings.source_path):
        # All the stuffs
        self.cache = {}

        # Add separator if necessary
        self.path = os.path.join(path, '')

        # Simple catch for bad paths
        if not os.path.isdir(self.path):
            raise IOError('Directory does not exist' + self.path)
        self.patient_folders = next(os.walk(path))[1]

        # Initialize all patient objects
        self.patients = {}
        for i in self.patient_folders:
            self.patients[i] = Patient(os.path.join(self.path, i, ''), self)

        # Initialize null views
        self.create_figure(('fig', 'null'))

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

    def create_figure(self, fig_id, key=0):
        '''
        Function to create figure from data in cache
        '''
        # fig_id = ('fig', data_id)
        data_id = fig_id[1] 

        fig = Figure()
        axis = fig.add_subplot(111)
        # try:
        if data_id != 'null':
            axis.plot(self.cache[data_id][key].squeeze())

        # except:
        #     pass

        self.load(fig_id, fig)
        print map(str, self.cache.keys())



