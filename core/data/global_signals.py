from pyqtgraph import QtCore

class SourceSignal(QtCore.QObject):

	# Global communication for annotation list updates
	annotation_list_added = QtCore.pyqtSignal(str)

	# Sync all audio components
	stop_audio = QtCore.pyqtSignal()
