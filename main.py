import enaml
from enaml.qt.qt_application import QtApplication
import sys

import matplotlib
matplotlib.use('TkAgg') # Maybe this helps?

import enaml_files
import settings

from atom.api import ContainerList, Atom
from enaml.core.declarative import d_

# Temp import from model
# sys.path.insert(0, settings.core_path)
import core
from core.model import *
# sys.path.pop(0)

# Main
if __name__ == '__main__':
    with enaml.imports():
        from enaml_files.main import Main
        from enaml_files.figure import FigDisplay

    src = core.Source()
    app = QtApplication()
    params = AppParams()
    params = settings.load_params(params)

    figures = FigureModels()
    figures.models = []

    # Load display
    main = Main(main_src=src, app_params = params, main_figures = [figures])
    main.show()

    app.start()
