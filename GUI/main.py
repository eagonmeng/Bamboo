from PyQt4 import QtGui, QtCore
import GUI
from core.data import settings

# Dock options for main window
_DOCK_OPTS = QtGui.QMainWindow.AllowTabbedDocks
_DOCK_OPTS |= QtGui.QMainWindow.AnimatedDocks


class Main(QtGui.QMainWindow):

    def __init__(self):
        super(Main, self).__init__()

        # Set up dock area
        self.setDockOptions(_DOCK_OPTS)
        self.dock_widgets = []
        self.setTabPosition(
            QtCore.Qt.BottomDockWidgetArea,
            QtGui.QTabWidget.South)

        #TEMP!
        self.setStyleSheet('''
        QMainWindow::separator {
            background: rgb(200, 200, 200);
            width: 2px;
            height: 2px;
        }''')

        self.init_UI()

        # Flags for modified settings
        settings.modified = []

    # Initialize the window
    def init_UI(self):
        '''
        Initial window geometry
        TODO: save last geometry
        '''
        self.init_window()

        # Status bar
        self.statusBar().showMessage('')

        # Title
        self.setWindowTitle('Bamboo version -1.0')

        self.widget = GUI.Views()
        self.widget.sig.update_docks.connect(self.docks_updated)

        # Don't need a central widget
        dummy = QtGui.QWidget()
        dummy.hide()
        self.setCentralWidget(dummy)

        # Set up static control dock
        self.control_dock = QtGui.QDockWidget()
        self.control_dock.setAllowedAreas(QtCore.Qt.TopDockWidgetArea)
        self.control_dock.setFeatures(QtGui.QDockWidget.NoDockWidgetFeatures)
        self.control_dock.setWidget(self.widget)
        self.control_dock.setTitleBarWidget(QtGui.QWidget())
        self.addDockWidget(QtCore.Qt.TopDockWidgetArea, self.control_dock)

        # Annotation mode
        if self.widget.src.path != '' and settings.annotation_on:
            self.widget.annotation_mode()


        # Menubar
        self.init_menubar()

        self.init_window()
        self.show()

    def init_window(self):
        space = QtGui.QDesktopWidget().availableGeometry()

        # Resize and center the window
        percentage = 2 / 3.0
        self.resize(space.size() * percentage)
        frame = self.frameGeometry()
        frame.moveCenter(space.center())
        self.move(frame.topLeft())

    def init_menubar(self):
        menubar = self.menuBar()

        # Actions
        exit_action = QtGui.QAction(QtGui.QIcon('exit.png'), '&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.setStatusTip('Exit application')
        exit_action.triggered.connect(QtGui.qApp.quit)

        add_view_action = QtGui.QAction('&Add View', self)
        add_view_action.setShortcut('Ctrl+A')
        add_view_action.setStatusTip('Add a view')
        add_view_action.triggered.connect(self.widget.add_view)

        # File
        file_menu = menubar.addMenu('&File')
        file_menu.addAction(exit_action)

        # Views
        view_menu = menubar.addMenu('&Views')
        view_menu.addAction(add_view_action)

    def docks_updated(self):
        new = set(self.widget.docks)
        old = set(self.dock_widgets)
        to_update = list(new - old)
        to_remove = list(old - new)
        # print 'update'

        for widget in to_remove:
            self.dock_widgets.remove(widget)
            widget.deleteLater()
            self.removeDockWidget(widget)

        for widget in to_update:
            self.dock_widgets.append(widget)
            self.addDockWidget(QtCore.Qt.BottomDockWidgetArea, widget)

            # Testing
            widget.s.removed.connect(self.widget_removed)

    def widget_removed(self, widget):
        # Remove dock from main's list of docks
        self.dock_widgets.remove(widget)

        # Remove widget from view's list of docks
        self.widget.docks.remove(widget)

        # Remove content widget from view's list of widgets
        self.widget.widgets.remove(widget.widget())

        # Delete content widget
        widget.widget().deleteLater()
        
        # Delete dock itself
        widget.deleteLater()

    # Save modified settings
    def closeEvent(self, *args, **kwargs):
        super(Main, self).closeEvent(*args, **kwargs)
        if len(settings.modified) != 0:
            print('\n')
            for item in settings.modified:
                if item == 'depth_tags':
                    print('\nNote: Depth labels for annotation have been modified! They are now: ')
                    print('depth_labels = ' + str(settings.depth_labels))
                elif item == 'patient_tags':
                    print('\nNote: Patient labels for annotation have been modified! They are now: ')
                    print('patient_labels = ' + str(settings.patient_labels))

            print('\nUpdate core/data/settings.py to keep these changes.')


