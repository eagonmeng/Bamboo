from patient import Patient
from core.data import settings
import os
from matplotlib.figure import Figure
from model import Memory, FigModel, SourceData


class Source(object):
    '''
    Core logic and data analysis access
    Handles data read and write requests
    '''

    def __init__(self, path=settings.source_path):
        # All the stuffs
        self.memory = Memory()
        self.d = SourceData()

        self.initialize(path)

    def initialize(self, path):
        # Add separator if necessary
        self.d.path = os.path.join(path, '')

        # Simple catch for bad paths
        if not os.path.isdir(self.d.path):
            print 'Directory does not exist: ' + self.d.path
            self.d.path = ''
            self.d.patient_folders = []
            self.patients = {}
        else:
            self.d.patient_folders = next(os.walk(path))[1]

            # Initialize all patient objects
            self.patients = {}
            for i in self.d.patient_folders:
                self.patients[i] = Patient(os.path.join(self.d.path, i, ''), self)

        # Refresh cache
        self.memory.cache.clear()

        # Initialize null views
        self.create_figure(('fig', 'null', 'null'))

    def load(self, data_id, data):
        '''
        Function to cache
        NEED MEMORY HANDLING
        '''
        self.memory.cache[data_id] = data
        print 'Added following to cache: ' + str(data_id)

    def write(self, storage, params):
        '''
        Function to write from shared memory to disk
        '''
        pass

    def create_figure(self, fig_id):
        '''
        Function to create matplotlib figure from data in cache
        '''
        # fig_id = ('fig', data_id)
        data_id = fig_id[1]
        key = fig_id[2]
        fig = Figure()

        if fig_id not in self.memory.cache:
            if data_id != 'null':
                axis = fig.add_subplot(111)
                try:
                    data = self.memory.cache[data_id][key]
                    if data.size == 1:
                        text = key + ' = ' + str(data.squeeze())
                        axis.text(0.2, .8, text, verticalalignment='top', fontsize=15)
                    else:
                        axis.plot(data.squeeze())
                except KeyError:
                    print 'Could not plot fig_id = ' + str(fig_id)
                    axis.text(0.2, .8, 'Missing channel', verticalalignment='top', color='green', fontsize=15)
                except AttributeError:
                    # axis.plot(data)
                    print 'Could not plot fig_id = ' + str(fig_id)
                    axis.text(0.2, .8, 'Data type exception', verticalalignment='top', color='green', fontsize=15)

            self.load(fig_id, fig)
            # Cache contents
            # print(map(str, self.memory.cache.keys()))

        else:
            pass



    def gen_fig_model(self, init_patient, init_height=200, init_channel=''):
        '''
        Function to return an atom FigModel
        '''
        return FigModel(patient=init_patient, channel=init_channel, height=init_height)

    def get_channels(self, patient, src_depth_idx=0):
        '''
        Function to return list of channels
        '''
        try:
            cur_patient = self.patients[patient]
        except KeyError:
            return []
        if not cur_patient.depths:
            return []
        src_depth = cur_patient.depths[src_depth_idx]
        data_id = ('channels', patient, src_depth)
        if data_id not in self.memory.cache:
            file_id = cur_patient.load(src_depth)
            channels = self.memory.cache[file_id].keys()
            self.load(data_id, channels)

        return self.memory.cache[data_id]

    def get_depths(self, patient):
        '''
        Function to return depths of a patient
        '''

        try:
            return self.patients[str(patient)].depths
        except KeyError:
            return []
