from atom.api import Atom, Unicode, Range, Bool, Int, List, Dict, observe, ContainerList
from enaml.core.declarative import d_

class AppParams(Atom):
    fig_height = Int()
    nr_figs = Int()

class PatientModel(Atom):
    depths = List()
    fig_ids = List()

class FigureModels(Atom):
    models = d_(ContainerList())
