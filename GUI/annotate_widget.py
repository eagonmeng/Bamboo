import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from core.data import settings


# Signal class
class UpdateSignal(QtCore.QObject):

    annotations_updated = QtCore.pyqtSignal(tuple)


# Annotation widget for individual depths
class AnnotateWidget(QtGui.QWidget):
	def __init__(self, src, patient, depth, channel):
		super(AnnotateWidget, self).__init__()

		self.init_ui()

		self.patient = patient
		self.src = src
		self.id = (depth, channel)

		# Connect update signal
		self.src.s.annotation_list_added.connect(self.add_tag)

		# Populate list widget
		self.list_items = list(settings.depth_labels)

		# Check if the patient already has selected depth labels
		preloaded = False
		if self.patient is not None:
			if self.id in self.patient.depth_labels:
				preloaded = True
				for label in self.patient.depth_labels[self.id]:
					if label not in self.list_items:
						self.list_items.append(label)

		# Add all items
		for item in self.list_items:
			list_item = QtGui.QListWidgetItem(item)
			self.list_widget.addItem(list_item)

			# Select the item if already loaded
			if preloaded:
				if item in self.patient.depth_labels[self.id]:
					self.list_widget.setItemSelected(list_item, True)

		# Connect item selection signal
		self.list_widget.itemSelectionChanged.connect(self.selection_changed)

	def init_ui(self):

		layout = QtGui.QVBoxLayout()

		# Add new tag
		add_layout = QtGui.QHBoxLayout()
		add_layout.addWidget(QtGui.QLabel('Add:'))
		self.new_tag_line = QtGui.QLineEdit('')
		self.new_tag_line.editingFinished.connect(self.emit_tag)
		add_layout.addWidget(self.new_tag_line)

		# List Widget
		self.list_widget = QtGui.QListWidget()
		self.list_widget.setSelectionMode(QtGui.QAbstractItemView.MultiSelection)

		layout.addWidget(self.list_widget)
		layout.addLayout(add_layout)

		self.setLayout(layout)

	def emit_tag(self):
		text = self.new_tag_line.text()

		if text not in self.list_items and text != '':
			self.list_items.append(text)
			list_item = QtGui.QListWidgetItem(text)
			self.list_widget.addItem(list_item)
			list_item.setSelected(True)

			# Notify all other annotation widgets
			if 'depth_tags' not in settings.modified:
				settings.modified.append('depth_tags')
			settings.depth_labels.append(str(text))
			self.src.s.annotation_list_added.emit(text)

	def add_tag(self, text):
		if text not in self.list_items and text != '':
			self.list_items.append(text)
			list_item = QtGui.QListWidgetItem(text)
			self.list_widget.addItem(list_item)

	# def add_tag(self):
	# 	text = self.new_tag_line.text()
	# 	if text not in self.list_items and text != '':
	# 		self.list_items.append(text)
	# 		list_item = QtGui.QListWidgetItem(text)
	# 		self.list_widget.addItem(list_item)
	# 		list_item.setSelected(True)

	def selection_changed(self):
		if self.patient is not None:
			self.patient.depth_labels[self.id] = [str(item.text()) for item in self.list_widget.selectedItems()]
			self.src.s.repaint_dc.emit()


# Annotation widget for depth control 
class AnnotateDepths(QtGui.QWidget):
	def __init__(self, src, dc):
		super(AnnotateDepths, self).__init__()

		self.src = src
		self.dc = dc
		self.annotate = AnnotateWidget(src, None, None, None)

		# Signal for updating all the other annotations
		self.s = UpdateSignal()

		self.init_ui()

		# Connect annotation updated signal
		self.dc.s.selected_annotated.connect(self.annotate_selected)

	def init_ui(self):
		layout = QtGui.QVBoxLayout()
		layout.setMargin(0)
		layout.setContentsMargins(0,0,0,0)
		layout.setSpacing(0)
		layout.addWidget(self.annotate)

		self.button = QtGui.QPushButton('Annotate')
		self.button.setCheckable(True)
		self.button.clicked.connect(self.toggle)

		layout.addWidget(self.button)

		self.setLayout(layout)
		self.show()
		self.annotate.hide()

	def toggle(self):
		if self.button.isChecked():
			self.annotate.show()
			self.annotate.setFixedHeight(settings.plot_height * 3/4.)
			self.dc.annotation_mode = True

		else:
			self.annotate.hide()
			self.annotate.list_widget.clearSelection()
			self.dc.annotation_mode = False

	def annotate_selected(self, depths):
		labels = [str(item.text()) for item in self.annotate.list_widget.selectedItems()]
		self.s.annotations_updated.emit((depths, labels))



# Annotation widget for patient diagnosis
class AnnotateControl(QtGui.QWidget):

	def __init__(self, src):
		super(AnnotateControl, self).__init__()

		self.src = src
		self.patient = None
		self.buttons = []
		self.tags = []

		self.init_ui()

		self.show()

	def init_ui(self):
		layout = QtGui.QHBoxLayout()

		layout.addWidget(QtGui.QLabel('Annotation:'), stretch=0)
		self.save_button = QtGui.QPushButton('Save')
		self.save_button.clicked.connect(self.save)
		layout.addWidget(self.save_button, stretch=0)

		layout.addWidget(QtGui.QLabel('Patient: '), stretch=0)
		self.patient_line = QtGui.QLineEdit()
		self.patient_line.setReadOnly(True)
		layout.addWidget(self.patient_line, stretch=0)

		layout.addWidget(QtGui.QLabel('Diagnosis:'), stretch=0)

		self.buttons_layout = QtGui.QHBoxLayout()

		layout.addLayout(self.buttons_layout, stretch=2)
		layout.addStretch(1)
		layout.addWidget(QtGui.QLabel('Add:'), stretch=0)
		self.add_line = QtGui.QLineEdit()
		self.add_line.editingFinished.connect(self.new_button)
		layout.addWidget(self.add_line)

		layout.setMargin(0)

		self.setLayout(layout)


	def patient_updated(self, patient):
		self.patient_line.setText(patient)
		self.patient = self.src.patients[str(patient)]

		# Add buttons
		for button in self.buttons:
			button.close()
		self.buttons = []
		self.tags = []

		tags = settings.patient_labels
		# for tag in settings.patient_labels:
		# 	self.add_button(tag)

		for tag in self.patient.patient_label:
			if tag not in tags:
				tags.append(tag)

		for tag in tags:
			check = tag in self.patient.patient_label
			self.add_button(tag, check)

	def add_button(self, tag, check=True):
		if tag not in self.tags:
			self.tags.append(tag)
			button = QtGui.QPushButton(tag)
			button.setCheckable(True)
			button.clicked.connect(self.buttons_updated)

			self.buttons.append(button)

			self.buttons_layout.addWidget(button)
			button.setChecked(check)
			return True
		return False

	def new_button(self):
		text = str(self.add_line.text())
		if self.add_button(text):
			# Notify core program
			settings.patient_labels.append(text)

			if 'patient_tags' not in settings.modified:
				settings.modified.append('patient_tags')

		self.buttons_updated()

	def save(self):
		self.src.save_patient_annotation(self.patient.name)

	def buttons_updated(self):
		patient_labels = []
		for button in self.buttons:
			if button.isChecked():
				patient_labels.append(str(button.text()))

		self.patient.patient_label = patient_labels