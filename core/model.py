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
    fig_id = Tuple()
    patient = Str()
    channel = Str()
    depth = Float()
    height = Int()

class SourceData(Atom):
    patient_folders = d_(ContainerList())
    path = d_(Unicode())

class AppParams(Atom):
    fig_height = Int()
    nr_figs = Int()

class FigureModels(Atom):
    models = d_(ContainerList())