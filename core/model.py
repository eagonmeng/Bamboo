from atom.api import Atom, Unicode, Range, Bool, ContainerList, Tuple, Dict, observe, Str, Float, Int
from enaml.core.declarative import d_


class Memory(Atom):
    '''
    Atom model holding all the data
    '''
    cache = Dict()
    # @observe('cache')
    # def debug_print(self, change):
    #     print 'help'
    #     print change

class FigModel(Atom):
    data_id = d_(Tuple())
    patient = d_(Unicode())
    channel = d_(Unicode())
    depth = d_(Float())
    height = d_(Int())
    display = d_(Str('RAW'))

    # @observe('display', 'patient', 'depth')
    # def update_data_id(self, change):
    #     '''
    #     Update data_id when components change
    #     '''
    #     if self.display == 'RAW':
    #         self.data_id = ('std', self.patient, self.depth)

class SourceData(Atom):
    patient_folders = d_(ContainerList())
    path = d_(Unicode())

class AppParams(Atom):
    fig_height = d_(Int())
    nr_figs = d_(Int())

class FigureModels(Atom):
    models = d_(ContainerList())