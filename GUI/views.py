from PyQt4 import QtGui, QtCore
from core.source import Source
from core.data import settings
import GUI
import control


class UpdateSignal(QtCore.QObject):
    update_docks = QtCore.pyqtSignal()
    link_removed = QtCore.pyqtSignal('int')
    removed = QtCore.pyqtSignal('PyQt_PyObject')
    new_link = QtCore.pyqtSignal('PyQt_PyObject')


class QDockWidget(QtGui.QDockWidget):
    '''
    Override
    '''

    def __init__(self, title):
        super(QDockWidget, self).__init__(title)
        self.s = UpdateSignal()

        # Dock title bar widget
        self.title = GUI.DockTitleBar(self)
        self.toggle_title(False)
        # self.topLevelChanged.connect(self.toggle_title)

        # Dock options
        self.setAllowedAreas(QtCore.Qt.BottomDockWidgetArea)
        dock_features = QtGui.QDockWidget.DockWidgetMovable
        dock_features |= QtGui.QDockWidget.DockWidgetClosable
        self.setFeatures(dock_features)

    # Destory
    def hide(self):
        # Purge from view link if exists
        link = self.widget().cur_link
        if link is not None:
            link.purge(self.widget())

            # Check if view link only has 1 link
            if len(link.linked) == 1:
            # if not link.linked:
                # Notify Views() to remove this link group
                self.s.link_removed.emit(link.link_id)

        super(QDockWidget, self).hide()
        self.s.removed['PyQt_PyObject'].emit(self)

    # Hack for displaying proper window flags while floating
    def toggle_title(self, floating):
        if floating: 
            self.setTitleBarWidget(None)
        else:
            self.setTitleBarWidget(self.title)

    @QtCore.pyqtSlot(str)
    def update_title(self, title):
        if self.widget().cur_link is not None:
            link_id = str(self.widget().cur_link.link_id)
            self.title.link_label.setText('Link: ' + link_id)
        else:
            self.title.link_label.setText('')
        self.title.label.setText(title)


class Views(QtGui.QWidget):

    def __init__(self):
        super(Views, self).__init__()

        self.src = Source()
        self.sig = UpdateSignal()

        self.init_UI()

    # Initialize the window
    def init_UI(self):
        '''
        Initial window geometry
        TODO: save last geometry
        '''
        self.widgets = []
        self.docks = []

        vbox = QtGui.QVBoxLayout()
        hbox = QtGui.QHBoxLayout()
        hbox2 = QtGui.QHBoxLayout()

        # Directory controls
        directory_lbl = QtGui.QLabel('Current directory: ')
        self.directory_text = QtGui.QLineEdit(self.src.path)
        self.directory_text.setReadOnly(True)
        change_dir = QtGui.QPushButton('Load new')
        change_dir.clicked.connect(self.update_source)
        hbox.addWidget(directory_lbl, stretch=0)
        hbox.addWidget(self.directory_text, stretch=1)
        hbox.addWidget(change_dir, stretch=0)

        # View controls (TEMPORARY)
        views_lbl = QtGui.QLabel('View controls: ')
        views_add = QtGui.QPushButton('Add')
        views_add.clicked.connect(self.add_view)
        hbox2.addWidget(views_lbl, stretch=0)
        hbox2.addWidget(views_add, stretch=0)
        hbox2.addStretch(1)

        vbox.addLayout(hbox)
        # vbox.addLayout(hbox2)

        # Annotation settings if necessary
        if settings.annotation_on:
            self.annotation_control = GUI.AnnotateControl(self.src)
            vbox.addWidget(self.annotation_control)

        ## View controls for all plots ##
        view_hbox = QtGui.QHBoxLayout()
        view_hbox.addWidget(QtGui.QLabel('Range Controls:'), stretch=0)
        view_hbox.addStretch(1)

        self.update_x_range_button = QtGui.QPushButton('Update X')
        view_hbox.addWidget(self.update_x_range_button, stretch=0)

        self.x_range_min = QtGui.QLineEdit(str(settings.default_x_range[0]))
        self.x_range_max = QtGui.QLineEdit(str(settings.default_x_range[1]))

        view_hbox.addWidget(QtGui.QLabel('Min (ms):'), stretch=0)
        view_hbox.addWidget(self.x_range_min, stretch=0)
        view_hbox.addWidget(QtGui.QLabel('Max (ms):'), stretch=0)
        view_hbox.addWidget(self.x_range_max, stretch=0)

        self.update_y_range_button = QtGui.QPushButton('Update Y')
        view_hbox.addWidget(self.update_y_range_button, stretch=0)

        self.y_range_min = QtGui.QLineEdit(str(settings.default_y_range[0]))
        self.y_range_max = QtGui.QLineEdit(str(settings.default_y_range[1]))

        view_hbox.addWidget(QtGui.QLabel('Min (mV):'), stretch=0)
        view_hbox.addWidget(self.y_range_min, stretch=0)
        view_hbox.addWidget(QtGui.QLabel('Max (mV):'), stretch=0)
        view_hbox.addWidget(self.y_range_max, stretch=0)

        # Connect signals
        self.update_x_range_button.clicked.connect(self.update_all_x_ranges)
        self.update_y_range_button.clicked.connect(self.update_all_y_ranges)

        vbox.addLayout(view_hbox)

        self.setLayout(vbox)

        # View links
        self.view_links = []
        self.link_ids = []

        # Size policies
        # self.setSizePolicy(
        #     QtGui.QSizePolicy.Ignored,
        #     QtGui.QSizePolicy.Ignored)
        self.setFixedHeight(self.minimumSizeHint().height())

        self.show()

    def update_all_x_ranges(self):
        for widget in self.widgets:
            widget.s.x_range_updated.emit(
                    (float(self.x_range_min.text()), float(self.x_range_max.text()))
                )
            widget.x_range_min.setText(self.x_range_min.text())
            widget.x_range_max.setText(self.x_range_max.text())

    def update_all_y_ranges(self):
        for widget in self.widgets:
            widget.s.y_range_updated.emit(
                    (float(self.y_range_min.text()), float(self.y_range_max.text()))
                )
            widget.y_range_min.setText(self.y_range_min.text())
            widget.y_range_max.setText(self.y_range_max.text())


    def update_views(self):
        self.sig.update_docks.emit()

    # Returns a created (widget, dock)
    def create_view(self):
        widget = GUI.GraphArea(self, self.src)

        # Add dock
        dock = QDockWidget(widget.cur_patient)
        dock.setWidget(widget)

        # Connect title to patient name
        widget.pcombo.currentIndexChanged[str].connect(dock.update_title)

        # Connect new link button
        dock.s.new_link.connect(self.new_link)

        return (widget, dock)

    def add_view(self, annotation=False):
        widget, dock = self.create_view()

        # Add in annotation link if necessary
        if annotation:
            widget.pcombo.currentIndexChanged[str].connect(self.annotation_control.patient_updated)
            self.annotation_control.patient_updated(widget.cur_patient)

        self.widgets.append(widget)
        self.docks.append(dock)
        self.update_views()

    def update_source(self):
        path = str(
            QtGui.QFileDialog.getExistingDirectory(self, "Select Directory"))
        self.src = Source(path)
        self.directory_text.setText(path)
        self.widgets = []
        self.docks = []
        self.add_view()
        self.update_views()

    # Creates a view link with 2 items or extends an existing one
    def new_link(self, view):
        # Parameter is the view to extend
        widget, dock = self.create_view()
        if view.cur_link is not None:
            view_link = view.cur_link
            view_link.add_link(widget)
        else:
            # Calculate the next link id
            if self.link_ids:
                next_id = self.link_ids[-1] + 1
            else:
                next_id = 0

            # Make new view link control
            view_link = control.ViewLink([view, widget], next_id)
            self.view_links.append(view_link)
            self.link_ids.append(next_id)

            # Refresh first widget's title bar with link id
            title = widget.pcombo.currentText()
            view.parentWidget().update_title(title)

            # Connect first widget's removal signal
            view.parentWidget().s.link_removed.connect(self.remove_link)

        # Refresh new widget's titlebar with link id
        title = widget.pcombo.currentText()
        dock.update_title(title)

        # Connect link removal signal
        dock.s.link_removed.connect(self.remove_link)

        # Insert new widget after the view to be extended
        # This doesn't work right now, fix Main() logic
        view_idx = self.widgets.index(view) + 1
        self.widgets.insert(view_idx, widget)
        self.docks.insert(view_idx, dock)

        # Update all docks
        self.update_views()

    @QtCore.pyqtSlot(int)
    def remove_link(self, link_id):
        idx = self.link_ids.index(link_id)
        link = self.view_links[idx]

        # Remove link from last view
        view = link.linked[0]
        view.cur_link = None
        title = view.pcombo.currentText()
        view.parentWidget().update_title(title)

        self.view_links.pop(idx)
        self.link_ids.pop(idx)

    # Function to initialize plots if annotation mode is on
    def annotation_mode(self):
        # Add the main annotation graph area
        self.add_view(True)

        # Activate the triple channel method of the graph area
        if settings.three_channels:
            self.docks[0].title.triple()

        # Make all docks non-closable
        # for dock in self.docks:
        #     dock.title.close_button.setEnabled(False)

