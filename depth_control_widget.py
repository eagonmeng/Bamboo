from enaml.core.declarative import d_
from enaml.widgets.api import RawWidget
from atom.api import Atom, Int, set_default, ContainerList, Bool, Event

# PyQt
from PyQt4 import QtGui, QtCore

# Signal class
class UpdateSignal(QtCore.QObject):

    selected_updated = QtCore.pyqtSignal()


class DepthControl(RawWidget):

    hug_width = set_default('ignore')
    hug_height = set_default('ignore')
    resist_height = set_default('strong')
    resist_width = set_default('medium')

    depths = d_(ContainerList())
    selected = d_(ContainerList())

    on_select = d_(Event(bool), writable=False)

    def create_widget(self, parent):

        widget = QtDepthControl(parent)
        widget.depths = self.depths
        widget.selected = self.selected

        widget.s.selected_updated.connect(self.on_selection)

        return widget

    def _observe_selected(self, change):

        if change['type'] == 'update':
            widget = self.get_widget()
            if widget is not None:
                widget.updateSelected(change['value'])
                widget.repaint()
                print 'SELECTED UPDATED'

    def _observe_depths(self, change):

        if change['type'] == 'update':
            widget = self.get_widget()
            if widget is not None:
                widget.updateSelected(None)
                widget.updateDepths(change['value'])
                widget.repaint()
                print 'DEPTHS UPDATED'

    # Signal handlers

    def on_selection(self):
        pass
        widget = self.get_widget()
        if widget is not None:
            self.selected = widget.selected
            widget.repaint()
            self.on_select(True)
            print 'SELECTED STUFF'


class QtDepthControl(QtGui.QWidget):

    def __init__(self, parent):
        super(QtDepthControl, self).__init__(parent)

        self.rubberband = QtGui.QRubberBand(
            QtGui.QRubberBand.Rectangle, self)
        self.setMouseTracking(True)
        self.initUI()

    def initUI(self):

        self.depths = []
        self.depth_heights = []
        self.selected = []
        self.range = range(30, -6, -1)
        self.vpf = 10  # Vertical padding fraction (of height)

        # Signal
        self.s = UpdateSignal()

    def updateSelected(self, new):

        # Remove list in place if necessary
        if new is not None:
            self.selected = new
        else:
            del self.selected[:]

    def updateDepths(self, new):

        self.depths = new

    def paintEvent(self, e):

        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()

    def drawWidget(self, qp):

        self.drawAxis(qp)

        size = self.size()
        width = size.width()
        height = size.height()

        # Vertical padding (top and bottom) for axis
        v_padding = height / self.vpf
        axis_height = height - (2 * v_padding)

        # Draw dots
        qpen = QtGui.QPen()
        qpen.setWidth(3)

        unit_height = float(axis_height) / (self.range[0] - self.range[-1])

        self.depth_heights = []
        for depth in self.depths:
            depth_height = v_padding + int((self.range[0] - depth) * unit_height)

            # Set pen color
            if depth in self.selected:
                qpen.setBrush(QtCore.Qt.red)
                qp.setPen(qpen)
            else:
                qpen.setBrush(QtCore.Qt.blue)
                qp.setPen(qpen)

            qp.drawPoint(width / 2, depth_height)
            self.depth_heights.append(depth_height)

    def drawAxis(self, qp):

        size = self.size()
        width = size.width()
        height = size.height()

        # Vertical padding (top and bottom) for axis
        v_padding = height / self.vpf
        axis_height = height - 2 * v_padding

        # Notches
        notch_width = width / 5

        notch_x1 = (width - notch_width) / 2
        notch_x2 = (width + notch_width) / 2

        # Axis line
        qp.drawLine(width / 2, v_padding, width / 2, v_padding + axis_height)

        # Draw notches
        nr_notches = len(self.range)
        i = 0
        metrics = qp.fontMetrics()
        for notch in self.range:
            nh = (i * axis_height / (nr_notches - 1)) + v_padding

            # Draw large notch and number for every 5 mm
            if notch % 5 == 0:
                # Numbers
                fw = metrics.width(str(notch))
                fh = metrics.height() / 3  # Not sure why 3, seems to work
                nr_x = notch_x1 - notch_width * 2 / 3
                qp.drawText(nr_x - fw / 2, nh + fh, str(notch))
                qp.drawLine(notch_x1, nh, notch_x2, nh)

            else:
                notch_shrink = notch_width / 4
                qp.drawLine(notch_x1 + notch_shrink, nh, notch_x2 - notch_shrink, nh)

            i += 1

    def mousePressEvent(self, event):

        self.origin = event.pos()
        self.rubberband.setGeometry(
            QtCore.QRect(self.origin, QtCore.QSize()))
        self.rubberband.show()
        QtGui.QWidget.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):

        if self.rubberband.isVisible():
            self.rubberband.setGeometry(
                QtCore.QRect(self.origin, event.pos()).normalized())
        QtGui.QWidget.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if self.rubberband.isVisible():
            self.rubberband.hide()
            rect = self.rubberband.geometry()

            # Find selected
            del self.selected[:]
            depths = zip(self.depths, self.depth_heights)
            for depth in depths:
                point = (self.size().width() / 2, depth[1])
                if rect.contains(*point):
                    self.selected.append(depth[0])

            if self.selected:
                print 'Selected: ' + str(self.selected)

            self.s.selected_updated.emit()
            # self.repaint()