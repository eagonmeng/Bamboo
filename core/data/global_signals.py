from pyqtgraph import QtCore

class SourceSignal(QtCore.QObject):

	annotation_list_added = QtCore.pyqtSignal(str)