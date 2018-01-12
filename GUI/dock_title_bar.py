from PyQt4 import QtGui, QtCore


class DockTitleBar(QtGui.QFrame):
    def __init__(self, parent):
        super(DockTitleBar, self).__init__(parent)

        # Using frame to give title bar a border
        self.setFrameStyle(QtGui.QFrame.Plain | QtGui.QFrame.StyledPanel)

        # Make sure to capture mouse events
        self.setMouseTracking(True)
        self.drag = False

        # Layout for title box
        layout = QtGui.QHBoxLayout(self)
        layout.setSpacing(1)
        layout.setMargin(1)

        self.label = QtGui.QLabel(parent.windowTitle())
        self.link_label = QtGui.QLabel('')

        # Proper button sizes
        icon_size = QtGui.QApplication.style().standardIcon(
            QtGui.QStyle.SP_TitleBarNormalButton).actualSize(
                QtCore.QSize(100, 100))
        button_size = icon_size + QtCore.QSize(5, 5)

        # Add link
        self.add_link = QtGui.QToolButton(self)
        self.add_link.setAutoRaise(True)
        self.add_link.setMaximumSize(button_size)
        self.add_link.setIcon(QtGui.QApplication.style().standardIcon(26))
        self.add_link.clicked.connect(self.new_link)

        # Context menu to add link button
        self.init_link_menu()
        self.add_link.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.add_link.customContextMenuRequested.connect(self.link_menu)

        # Close dock button
        self.close_button = QtGui.QToolButton(self)
        self.close_button.setAutoRaise(True)
        self.close_button.setMaximumSize(button_size)
        self.close_button.setIcon(QtGui.QApplication.style().standardIcon(
            QtGui.QStyle.SP_DockWidgetCloseButton))
        self.close_button.clicked.connect(self.close_parent)

        # Setup layout
        layout.addWidget(self.label)
        layout.addStretch(1)
        layout.addWidget(self.link_label)
        layout.addStretch(1)
        layout.addWidget(self.add_link)
        layout.addWidget(self.close_button)

    def new_link(self):
        # Do something when custom button is pressed
        parent_view = self.parentWidget().widget()
        self.parentWidget().s.new_link['PyQt_PyObject'].emit(parent_view)

    def close_parent(self):
        self.parent().hide()

    def init_link_menu(self):
        self.lmenu = QtGui.QMenu(self)
        self.triple_channel = QtGui.QAction('Three channels', self.lmenu)
        # self.triple_channel.setStatusTip('Expand to three channels view')
        self.triple_channel.triggered.connect(self.triple)

        # Add to menu
        self.lmenu.addAction(self.triple_channel)

    def link_menu(self, point):
        expandable = (self.parentWidget().widget().cur_link is None)
        self.triple_channel.setEnabled(expandable)
        self.lmenu.exec_(self.add_link.mapToGlobal(point))

    # Create three channels linked together
    def triple(self):
        parent_view = self.parentWidget().widget()
        for i in range(2):
            self.parentWidget().s.new_link['PyQt_PyObject'].emit(parent_view)
        # other_views = [x for x in parent_view.cur_link.linked if x != parent_view]
        channels = parent_view.src.get_parallel_channels(parent_view.ccombo.value())

        # Assume we find three channels if at all
        if channels:
            i = 0
            for view in parent_view.cur_link.linked:
                view.ccombo.setValue(channels[i])
                i += 1

