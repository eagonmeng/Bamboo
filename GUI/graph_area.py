import pyqtgraph as pg
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.dockarea import DockArea, Dock
from core.data import settings
pg.setConfigOption('useOpenGL', False)
import GUI

from time import time
import tqdm

# import cProfile, pstats, StringIO

# Timing decorator
# def timeit(method):
#     def func(self):
#         start = time()
#         result = method(self)
#         end = time()
#         print('%r %.4f (s)' % (method.__name__, end-start))

#         return result
#     return func

# def timeit(method):
#     def func(self):
#         pr = cProfile.Profile()
#         pr.enable()
#         result = method(self)
#         pr.disable()
#         s = StringIO.StringIO()
#         sortby = 'cumulative'
#         ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
#         print('Profiling: %r' % method.__name__)
#         ps.print_stats()
#         print s.getvalue()

#         return result
#     return func

# Override scroll area behavior
class ScrollArea(pg.QtGui.QScrollArea):
    def __init__(self):
        super(ScrollArea, self).__init__()

    def wheelEvent(self, event):
        # Prevent scrolling in larger scroll area
        event.accept()


class GraphLayout(pg.GraphicsLayoutWidget):
    def __init__(self, border=(100, 100, 100)):
        super(GraphLayout, self).__init__(border=border)

class XAxisControl(pg.PlotWidget):
    def __init__(self):
        super(XAxisControl, self).__init__()

        self.showAxis('left', False)
        self.hideButtons()
        self.line = self.addLine(y=0, hoverPen=(0,0,0), label='y={value:0.2f}mm', movable=False,
            labelOpts={'color': (255,255,255), 'movable': True, 'fill': (100, 100, 100, 100)})

# Override floating dock behavior
class TempAreaWindow(QtGui.QMainWindow):
    def __init__(self, area, parent_area, **kwargs):
        QtGui.QMainWindow.__init__(self, **kwargs)
        self.setCentralWidget(area)
        self.parent_area = parent_area

    def closeEvent(self, *args, **kwargs):

        docks = self.centralWidget().findAll()[1]
        for dock in docks.values():
            self.parent_area.moveDock(dock, 'bottom', None)

            #Realign new dock
            self.parent_area.realign(dock)

        QtGui.QMainWindow.closeEvent(self, *args, **kwargs)


# Extended DockArea to prevent collapsing
class DockArea(DockArea):
    def makeContainer(self, typ):
        new = super(DockArea, self).makeContainer(typ)
        try:
            new.setChildrenCollapsible(False)
        except AttributeError:
            pass
        return new

    def addTempArea(self):
        if self.home is None:
            area = DockArea(temporary=True, home=self)
            self.tempAreas.append(area)
            win = TempAreaWindow(area, self)
            area.win = win
            win.show()
        else:
            area = self.home.addTempArea()
        #print 'added temp area', area, area.window()
        return area

    # Realign the new dock in terms of its depth
    def realign(self, target):
        new = None
        for dock in self.docks:
            dock = self.docks[dock]
            if target.depth > dock.depth:
                try:
                    if dock.depth > new.depth:
                        new = dock
                except AttributeError:
                    new = dock

        if new is not None:
            self.moveDock(target, 'top', new)


# Class override for depth handling
class Dock(Dock):
    def __init__(self, depth, **kwargs):
        self.depth = depth
        title = 'Depth: %f' % self.depth
        super(Dock, self).__init__(title, **kwargs)


# Signal class
class UpdateSignal(QtCore.QObject):

    x_range_updated = QtCore.pyqtSignal(tuple)
    y_range_updated = QtCore.pyqtSignal(tuple)


class GraphArea(pg.QtGui.QWidget):
    def __init__(self, parent=None, src=None):
        super(GraphArea, self).__init__(parent)
        self.src = src

        # TODO: Save defaults
        self.cur_patient = self.src.patient_folders[0]
        self.auto_default_range = settings.auto_default_range

        # Depth control
        if settings.annotation_on:
            self.dc = GUI.DepthControl(vpf=1./40)
        else:
            self.dc = GUI.DepthControl()
        
        self.dc.s.selected_updated.connect(self.depths_updated)
        self.dc.display_hashes = settings.preprocess_hashes

        # Dict of depths with their plot widgets
        self.selected_depths = {}

        # Current link group
        self.cur_link = None

        # Try out other horizontal policies
        # self.setSizePolicy(
        #     pg.QtGui.QSizePolicy.MinimumExpanding,
        #     pg.QtGui.QSizePolicy.Ignored)
        # self.setMinimumWidth(1)

        # Signals for interacting with all children
        self.s = UpdateSignal()

        # Progress bar
        self.pbar = None

        self.init_UI()


    def init_UI(self):
        # Patient selection
        hbox = pg.QtGui.QHBoxLayout()
        self.patient_txt = pg.QtGui.QLabel('Patient: ')
        self.pcombo = pg.ComboBox(
            items=self.src.patient_folders,
            default=self.cur_patient)

        # Connect patient update signal
        self.pcombo.currentIndexChanged.connect(self.patient_update)
        hbox.addWidget(self.patient_txt, stretch=0)
        hbox.addWidget(self.pcombo, stretch=1)

        # Channel selection
        self.channel_txt = pg.QtGui.QLabel('Channel: ')

        '''
        Assuming all channels found in first depth - change later!
        '''
        channels = self.src.get_channels(self.cur_patient, 0)

        self.ccombo = pg.ComboBox(items=channels)

        # Add context menu channel combobox to manage channels
        self.init_channel_menu()
        self.ccombo.setContextMenuPolicy(pg.QtCore.Qt.CustomContextMenu)
        self.ccombo.customContextMenuRequested.connect(self.channel_menu)

        # Connect channel update signal
        self.ccombo.currentIndexChanged.connect(self.update_plots)
        hbox.addWidget(self.channel_txt, stretch=0)
        hbox.addWidget(self.ccombo, stretch=1)

        # Button to toggle annotations
        if settings.annotation_on:
            self.toggle_annotation = QtGui.QPushButton('Annotate')
            self.toggle_annotation.setCheckable(True)
            self.toggle_annotation.setChecked(not settings.hide_annotation)
            hbox.addWidget(self.toggle_annotation, stretch=0)

        ## View controls for all plots ##
        view_hbox = QtGui.QHBoxLayout()
        # view_hbox.addWidget(QtGui.QLabel('Range Controls:'), stretch=0)
        view_hbox.addStretch(1)

        self.update_x_range_button = QtGui.QPushButton('X')
        view_hbox.addWidget(self.update_x_range_button, stretch=0)

        self.x_range_min = QtGui.QLineEdit(str(settings.default_x_range[0]))
        self.x_range_max = QtGui.QLineEdit(str(settings.default_x_range[1]))

        view_hbox.addWidget(QtGui.QLabel('Min (ms):'), stretch=0)
        view_hbox.addWidget(self.x_range_min, stretch=0)
        view_hbox.addWidget(QtGui.QLabel('Max (ms):'), stretch=0)
        view_hbox.addWidget(self.x_range_max, stretch=0)

        self.update_y_range_button = QtGui.QPushButton('Y')
        view_hbox.addWidget(self.update_y_range_button, stretch=0)

        self.y_range_min = QtGui.QLineEdit(str(settings.default_y_range[0]))
        self.y_range_max = QtGui.QLineEdit(str(settings.default_y_range[1]))

        view_hbox.addWidget(QtGui.QLabel('Min (mV):'), stretch=0)
        view_hbox.addWidget(self.y_range_min, stretch=0)
        view_hbox.addWidget(QtGui.QLabel('Max (mV):'), stretch=0)
        view_hbox.addWidget(self.y_range_max, stretch=0)

        # Connect signal
        # self.update_x_range_button.clicked.connect(
        #     lambda: self.s.x_range_updated.emit(
        #         (float(self.x_range_min.text()), float(self.x_range_max.text()))
        #     )
        # )

        # self.update_y_range_button.clicked.connect(
        #     lambda: self.s.y_range_updated.emit(
        #         (float(self.y_range_min.text()), float(self.y_range_max.text()))
        #     )
        # )

        self.update_x_range_button.clicked.connect(self.emit_x_range_updated)
        self.update_y_range_button.clicked.connect(self.emit_y_range_updated)

        # Scroll area
        self.scroll = ScrollArea()

        # Main display
        self.dock_area = DockArea()
        self.min_plot_height = settings.plot_height

        # Scroll widget
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.dock_area)

        # Refresh
        self.update_plots()
        self.update_depths()

        # Construct layout
        vbox = pg.QtGui.QVBoxLayout()
        vbox.addLayout(hbox)

        # Hide individual control (Give dynamic option to enable later?)
        # vbox.addLayout(view_hbox)

        # Position depth control and main displays
        hbox2 = pg.QtGui.QHBoxLayout()
        vbox2 = pg.QtGui.QVBoxLayout()
        vbox2.setMargin(0)
        hbox2.setMargin(0)

        # Add horizontal slider
        # self.horizontal_axis = XAxisControl()
        vbox2.addWidget(self.scroll, stretch=9)
        # vbox2.addWidget(self.horizontal_axis, stretch=1)

        # 90% to 10% graph to depth control split; add customizability?
        hbox2.addLayout(vbox2, stretch=9)

        # Set the depth control inside an optional vbox for annotation possibility
        if settings.annotation_on:
            vbox3 = pg.QtGui.QVBoxLayout()
            vbox3.setMargin(0)
            vbox3.setSpacing(2)
            vbox3.setContentsMargins(0,0,0,0)

            # Depth control
            depth_annotate = GUI.AnnotateDepths(self.src, self.dc)
            depth_annotate.s.annotations_updated.connect(self.update_annotations)
            # depth_annotate.hide()
            # depth_annotate.setSizePolicy(pg.QtGui.QSizePolicy.Minimum, pg.QtGui.QSizePolicy.Minimum)
            vbox3.addWidget(self.dc, stretch=10)
            vbox3.addWidget(depth_annotate, stretch=0)
            hbox2.addLayout(vbox3, stretch=1)
        else:
            hbox2.addWidget(self.dc, stretch=1)

        vbox.addLayout(hbox2)
        self.setLayout(vbox)

        '''
        Default settings for channel combo box
        '''
        # Set default checked state based on settings
        only_data = self.src.only_data_channels
        only_spike = self.src.only_spike_channels
        if only_data and not only_spike:
            self.only_data_action.setChecked(True)
            self.only_data()
        if only_spike and not only_data:
            self.only_spike_action.setChecked(True)
            self.only_spike()

        self.show()

    # Initialize channel context menu
    def init_channel_menu(self):
        self.cmenu = pg.QtGui.QMenu(self)
        self.only_data_action = pg.QtGui.QAction('Only Data', self.cmenu, checkable=True)
        # self.only_data_action.setStatusTip('Only display channels with data')
        self.only_data_action.triggered.connect(self.only_data)
        self.only_spike_action = pg.QtGui.QAction('Only Spikes', self.cmenu, checkable=True)
        # self.only_spike_action.setStatusTip('Only display RAW data')
        self.only_spike_action.triggered.connect(self.only_spike)

        # Add to menu
        self.cmenu.addAction(self.only_spike_action)
        self.cmenu.addAction(self.only_data_action)

    # Display channel context menu at right location
    def channel_menu(self, point):
        self.cmenu.exec_(self.ccombo.mapToGlobal(point))

    def only_data(self):
        channels = self.src.get_channels(self.cur_patient, 0)
        only_data = self.only_data_action.isChecked()
        only_spike = self.only_spike_action.isChecked()
        if only_data:
            channels = self.src.parse_data_channels(channels)
            if only_spike:
                # Also toggle off the other filter, since not compatible
                self.only_spike_action.toggle()

        self.ccombo.setItems(channels)

    def only_spike(self):
        channels = self.src.get_channels(self.cur_patient, 0)
        only_data = self.only_data_action.isChecked()
        only_spike = self.only_spike_action.isChecked()
        if only_spike:
            channels = self.src.parse_spike_channels(channels)
            if only_data:
                self.only_data_action.toggle()

        self.ccombo.setItems(channels)

    def update_depths(self):
        # Update depth control
        patient = self.src.patients[self.cur_patient]
        self.dc.updateDepths(patient.depths)

        # Update patient and hashrates if necessary
        if settings.preprocess_hashes:
            self.dc.updatePatient(patient)

        self.dc.updateSelected(None)
        self.dc.repaint()

    def patient_update(self):
        # Update current patient and channel list
        self.cur_patient = self.pcombo.value()

        '''
        Assuming all channels found in first depth
        '''
        channels = self.src.get_channels(self.cur_patient, 0)
        if self.only_data_action.isChecked():
            channels = self.src.parse_data_channels(channels)
        elif self.only_spike_action.isChecked():
            channels = self.src.parse_spike_channels(channels)
        self.ccombo.setItems(channels)

        # Clear and reset various parts of GUI when patient changes
        self.update_depths()

        # Just run an update to notify everything about channel as well
        self.update_plots()

        # Remove all selected depths
        # self.selected_depths.clear()
        for depth in self.selected_depths.keys():
            # Clear docks
            self.selected_depths[depth].close()
            self.selected_depths.pop(depth)

        self.update_layout()
        self.update_plots()

    # @timeit
    def update_plots(self):
        # Update individual plots
        patient = self.src.patients[self.cur_patient]
        channel = self.ccombo.value()
        auto_range = False

        # Notify depth control if necessary
        if settings.preprocess_hashes:
            if channel in settings.spike_channels:
                self.dc.updateChannel(channel)
                self.emit_x_range_updated()
                self.emit_y_range_updated()
            else:
                self.dc.updateChannel(None)
                auto_range = True
            self.dc.repaint()

        # Progress bar update
        if self.pbar is not None:
            self.pbar.set_description('Plotting data')

        # Update all the split dock widgets
        for depth, dock in self.selected_depths.iteritems():
            dock.widgets[0].update(self.src, patient, channel, depth)
            if auto_range:
                dock.widgets[0].auto_range_contents()
            if self.pbar is not None:
                self.pbar.update(1)

    # @timeit
    def depths_updated(self):
        self.dc.repaint()
        previous = set(self.selected_depths.iterkeys())
        updated = set(self.dc.selected)

        # Remove depths in previous not in updated
        purge = previous - updated

        # Add plot items necessary for new depths
        add = updated - previous

        # Instantiate progress bar
        total_length = len(purge) + len(add) + (2 * len(updated))

        if total_length > 0:
            print('\nVisualizing for channel: %s' % self.ccombo.value())
            self.pbar = tqdm.tqdm(total=total_length)

        ### Delete previous docks ###

        # cur = time()

        for depth in purge:
            # Progress bar description
            if self.pbar is not None:
                self.pbar.set_description('Deleting docks')

            # Clear widget
            # Seems bugged - does this actually close the widget?
            self.selected_depths[depth].widgets[0].close()

            ### Disconnect signals ###
            self.s.x_range_updated.disconnect(self.selected_depths[depth].widgets[0].main_widget.set_x_range)
            self.s.y_range_updated.disconnect(self.selected_depths[depth].widgets[0].main_widget.set_y_range)

            if settings.annotation_on:
                self.toggle_annotation.toggled.disconnect(self.selected_depths[depth].widgets[0].toggle_second_widget)

            # Clear docks
            self.selected_depths[depth].close()

            self.selected_depths.pop(depth)

            if self.pbar is not None:
                self.pbar.update(1)


        ### Add new docks ###

        # print('Time to delete: %f' % (time() - cur))
        # cur = time()

        for depth in add:
            # Progress bar update
            if self.pbar is not None:
                self.pbar.set_description('Loading data')

            # Wrap the widget in a dock
            widget =  GUI.DefaultPlotWidget(self.src)
            self.add_plot_dock(depth, widget)

            if self.pbar is not None:
                self.pbar.update(1)

        # print('Time to add: %f' % (time() - cur))
        # cur = time()

        ### Update layout ###
        self.update_layout()

        # print('Time to update layout: %f' % (time() - cur))
        # cur = time()

        ### Update plots ###

        self.update_plots()
        # print('Time to update plots: %f' % (time() - cur))


        # Update annotate toggle
        if settings.annotation_on:
            self.toggle_annotation.setChecked(not settings.hide_annotation)

        # Update views
        # print('updating')
        if self.auto_default_range:
            self.emit_x_range_updated()
            self.emit_y_range_updated()
        # print('updated')

        if self.pbar is not None:
            self.pbar.close()
            self.pbar = None

    # @timeit
    def update_layout(self):
        length = len(self.selected_depths)
        self.dock_area.setMinimumSize(0, length * self.min_plot_height)

        # Progress bar update
        if self.pbar is not None:
            self.pbar.set_description('Populating visual elements')

        for depth in sorted(self.selected_depths.iterkeys(), reverse=True):
            dock = self.selected_depths[depth]
            self.dock_area.addDock(dock, position='bottom')

            if self.pbar is not None:
                self.pbar.update(1)

    def add_plot_dock(self, depth, widget):
        dock = Dock(depth, size=(1,1), closable=False, autoOrientation=False)
        split_dock_widget = SplitDockWidget(widget)

        ### Connect signals ###
        self.s.x_range_updated.connect(widget.set_x_range)
        self.s.y_range_updated.connect(widget.set_y_range)
        widget.s.title_updated.connect(dock.setTitle)

        if settings.annotation_on:
            self.toggle_annotation.toggled.connect(split_dock_widget.toggle_second_widget)

        dock.addWidget(split_dock_widget)
        self.selected_depths[depth] = dock       

    ## Emit the signals necessary to update all the plots ##
    def emit_x_range_updated(self):
        self.s.x_range_updated.emit(
            (float(self.x_range_min.text()), float(self.x_range_max.text()))
        )

    def emit_y_range_updated(self):
        self.s.y_range_updated.emit(
            (float(self.y_range_min.text()), float(self.y_range_max.text()))
        )

    # Update annotations across all the necessary depths for the patient
    def update_annotations(self, update):
        # Update is tuple of form (depths, labels)
        depths, labels = update

        ch_nr = self.src.get_channel_number(self.ccombo.value())
        patient = self.src.patients[self.cur_patient]

        for depth in depths:
            # Update all annotation widgets
            if depth in self.selected_depths:
                dock = self.selected_depths[depth]
                dock.widgets[0].update_annotation(labels)
            # Update patient for depths not currently displayed
            else:
                # Calculate current id
                cur_id = (depth, ch_nr)

                # Check if depth_labels already has labels
                if cur_id not in patient.depth_labels:
                    patient.depth_labels[cur_id] = labels
                else:
                    for label in labels:
                        if label not in patient.depth_labels[cur_id]:
                            patient.depth_labels[cur_id].append(label)

''' 
Old update method
    def update_layout(self):
        self.gl.clear()
        length = len(self.selected_depths)
        self.gl.setMinimumSize(0, length * self.min_plot_height)
        for depth in sorted(self.selected_depths.iterkeys(), reverse=True):
            self.gl.addItem(self.selected_depths[depth])
            self.gl.nextRow()
'''


class SplitDockWidget(QtGui.QWidget):
    def __init__(self, widget):
        super(SplitDockWidget, self).__init__()

        self.main_widget = widget
        self.second_widget = None
        self.box_layout = QtGui.QHBoxLayout()
        self.box_layout.setMargin(0)

        self.splitter = QtGui.QSplitter()
        self.splitter.addWidget(self.main_widget)
        self.splitter.setStretchFactor(0, 10)

        # self.main_widget.setSizePolicy(policy)
        self.box_layout.addWidget(self.splitter)
        self.setLayout(self.box_layout)

    def add_second_widget(self, widget):
        # Remove old widget 
        self.remove_second_widget()

        self.second_widget = widget
        self.splitter.addWidget(self.second_widget)
        self.splitter.setStretchFactor(1, 1)

        # Default hide second widget
        if settings.hide_annotation:
            # self.splitter.moveSplitter(self.splitter.getRange(0)[1], 0)
            self.splitter.moveSplitter(self.splitter.getRange(1)[1], 1)

    def remove_second_widget(self):
        if self.second_widget is not None:
            self.second_widget.close()
            self.second_widget = None

    def update(self, src, patient, channel, depth):
        self.main_widget.update_values(patient, channel, depth)
        if src.get_channel_number(channel) and settings.annotation_on:
            self.add_second_widget(GUI.AnnotateWidget(src, patient, depth, src.get_channel_number(channel)))
        else:
            self.remove_second_widget()

    # Resize all elements to the automatic range
    def auto_range_contents(self):
        self.main_widget.autoRange()   

    def toggle_second_widget(self, checked):
        if self.second_widget is not None:
            width = self.second_widget.minimumSizeHint().width()
            max_range = self.splitter.getRange(1)[1]

            # Toggle hidden
            if checked:
                self.splitter.moveSplitter(max_range - width, 1)
            else:
                self.splitter.moveSplitter(max_range, 1)


    '''
    Application specific methods (not for general split dock)
    '''
    # Annotation method
    def update_annotation(self, labels):
        # Assuming that the second widget is an annotation widget
        if self.second_widget is not None:
            for label in labels:
                found = self.second_widget.list_widget.findItems(label, QtCore.Qt.MatchExactly)
                if len(found) > 0:
                    self.second_widget.list_widget.setItemSelected(found[0], True)



