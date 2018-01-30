from PyQt4 import QtCore


# Control for maintaining linked views
class ViewLink(object):
	def __init__(self, linked, link_id):
		# Expect linked views as list
		self.linked = []
		self.link_id = link_id

		# Guard against infinite update loops
		self.guard = False

		for view in linked:
			self.add_link(view)

	def add_link(self, view):
		# Depth control syncing
		view.dc.s.selected_updated.connect(self.depths_updated)
		view.dc.s.set_defaults.connect(self.dc_set_defaults)
		view.dc.s.wheel_updated.connect(self.dc_wheel_event)
		view.dc.s.translation_updated.connect(self.dc_translation)

		# Graph area syncing
		view.pcombo.currentIndexChanged[str].connect(self.patient_updated)
		view.scroll.verticalScrollBar().valueChanged.connect(self.scroll_updated)
		view.cur_link = self

		self.sync(view)
		self.linked.append(view)

		# Re-center all depth control views
		self.dc_set_defaults()

	def purge(self, view):
		view.cur_link = None
		idx = self.linked.index(view)
		self.linked.pop(idx)

	# Syncs given view with rest of the link members
	def sync(self, view):
		if self.linked:
			depths = self.linked[0].dc.selected
			patient = str(self.linked[0].pcombo.currentText())
			sld_value = self.linked[0].scroll.verticalScrollBar().value()

			# We want to update only the values, so enable guard
			self.guard = True
			view.dc.selected = depths
			view.dc.s.selected_updated.emit(depths)
			idx = view.pcombo.findText(patient)
			view.pcombo.setCurrentIndex(idx)
			view.scroll.verticalScrollBar().setValue(sld_value)
			self.guard = False

	@QtCore.pyqtSlot(list)
	def depths_updated(self, depths):
		if not self.guard:
			self.guard = True
			for view in self.linked:
				# Prevent updating the one actively selected
				if view.dc.active_select:
					view.dc.active_select = False
				else:
					view.dc.selected = depths
					view.dc.s.selected_updated.emit(depths)
			self.guard = False

	@QtCore.pyqtSlot(str)
	def patient_updated(self, patient):
		if not self.guard:
			self.guard = True
			for view in self.linked:
				idx = view.pcombo.findText(patient)
				view.pcombo.setCurrentIndex(idx)
			self.guard = False

	@QtCore.pyqtSlot(int)
	def scroll_updated(self, sld_value):
		if not self.guard:
			self.guard = True
			for view in self.linked:
				view.scroll.verticalScrollBar().setValue(sld_value)
			self.guard = False

	'''
	For all these depth control syncing features, we probably don't need self.guard
	But just incase we want to sync them in the future, I'm keeping the structure
	A decorator would also have saved a few lines
	'''
	@QtCore.pyqtSlot()
	def dc_set_defaults(self):
		if not self.guard:
			self.guard = True
			for view in self.linked:
				if view.dc.active_select:
					view.dc.active_select = False
				else:
					view.dc.set_defaults()
					view.dc.repaint()
			self.guard = False

	@QtCore.pyqtSlot(QtCore.QEvent)
	def dc_wheel_event(self, event):
		if not self.guard:
			self.guard = True
			for view in self.linked:
				if view.dc.active_select:
					view.dc.active_select = False
				else:
					view.dc.wheel_zoom(event)
			self.guard = False

	@QtCore.pyqtSlot(float)
	def dc_translation(self, dy):
		if not self.guard:
			self.guard = True
			for view in self.linked:
				if view.dc.active_select:
					view.dc.active_select = False
				else:
					view.dc.translation(dy)
			self.guard = False

