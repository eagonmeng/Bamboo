from atom.api import Atom, Unicode, Range, Bool, List, Tuple, Dict, observe, Str, Float, Int


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

