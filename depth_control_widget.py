from enaml.core.declarative import d_
from enaml.widgets.api import RawWidget
from atom.api import Atom, Int, set_default, ContainerList, Bool, Event
import math
import numpy as np
from bisect import bisect_left

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
                print('SELECTED UPDATED')

    def _observe_depths(self, change):

        if change['type'] == 'update':
            widget = self.get_widget()
            if widget is not None:
                widget.updateSelected(None)
                widget.updateDepths(change['value'])
                widget.repaint()
                print('DEPTHS UPDATED')

    # Signal handlers

    def on_selection(self):
        pass
        widget = self.get_widget()
        if widget is not None:
            self.selected = widget.selected
            widget.repaint()
            self.on_select(True)
            print('SELECTED STUFF')


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

        self.set_defaults()

        # Size parameters (fractions of total size)
        self.notch_width_fraction = 1. / 5

        # Vertical padding fraction (of height)
        self.vpf = 1. / 10

        # Zoom stuffs
        cutoffs = [5, 2]
        levels = 3
        self.set_zoom(np.array(cutoffs), levels)
        self.zoom = 1.1  # Zoom speed (enlarge axis)

        # Text and axis width
        self.text_width = 1

        # Drag internal variables
        self.drag = False
        self.drag_origin = 0

        # Signal
        self.s = UpdateSignal()

    def set_defaults(self, start=25, end=-5, unit_value=1, notch_disp=5):
        self.start = start  # Value associated with top pixel of axis
        self.end = end
        self.mid = (self.start + self.end) / 2
        self.unit_value = unit_value
        self.notch_disp = notch_disp  # Display every notch_disp units
        self.z_change = 1  # Zoom coefficient
        self.updateNotches()

    def get_axis_height(self):
        size = self.size()
        width = size.width()
        height = size.height()

        # Vertical padding (top and bottom) for axis
        v_padding = height * self.vpf
        return height - (2 * v_padding)

    def get_unit_height(self):
        axis_height = self.get_axis_height()
        return float(axis_height) / ((self.start - self.end))

    def set_zoom(self, cutoffs, levels):
        # Custom zoom vector
        total_scale = np.prod(cutoffs)
        scale_up = np.cumprod(np.tile(cutoffs, levels))
        scale_down = np.cumprod(np.tile(1. / cutoffs[::-1], levels))

        # Vector of change cutoffs
        self.z_vector = np.concatenate((
            scale_down[::-1],
            [1],
            scale_up))

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
        v_padding = height * self.vpf
        axis_height = height - (2 * v_padding)

        # Draw dots
        qpen = QtGui.QPen()
        pen_width = 3
        qpen.setWidth(pen_width)

        # unit_height = float(axis_height) / (self.start - self.end)
        unit_height = self.get_unit_height()

        self.depth_heights = []
        depth_widths = []
        adjusted_depths = []
        for depth in self.depths:
            depth_height = (height / 2.) - (depth - self.mid) * unit_height
            depth_width = width / 2
            if (depth_height >= v_padding - qpen.width() and
                    depth_height <= v_padding + axis_height):
                # Set pen color
                if depth in self.selected:
                    qpen.setBrush(QtCore.Qt.red)
                    qp.setPen(qpen)
                else:
                    qpen.setBrush(QtCore.Qt.blue)
                    qp.setPen(qpen)

                qp.drawPoint(depth_width, depth_height)
            self.depth_heights.append(depth_height)
            depth_widths.append(depth_width)
            adjusted_depths.append(depth)

        # Setup appropriate tooltips
        self.d_tooltips = DepthTooltip(
            adjusted_depths, depth_widths, self.depth_heights, pen_width)

    def drawAxis(self, qp):

        size = self.size()
        width = size.width()
        height = size.height()

        # Vertical padding (top and bottom) for axis
        v_padding = height * self.vpf
        axis_height = height - 2 * v_padding

        # Axis line
        qp.drawLine(width / 2, v_padding, width / 2, v_padding + axis_height)

        # Notch coordinates
        notch_width = width * self.notch_width_fraction
        notch_x1 = (width - notch_width) / 2
        notch_x2 = (width + notch_width) / 2

        # Draw notches
        metrics = qp.fontMetrics()
        unit_height = self.get_unit_height()

        # Get pen
        qpen = QtGui.QPen()
        qpen.setWidth(self.text_width)
        pen_width = qpen.width()
        qp.setPen(qpen)

        for notch in self.notches:
            nh = (height / 2.) - (notch - self.mid) * unit_height

            if nh > v_padding + axis_height:
                continue  # Get around bad floating point division

            # Draw large notch and number every multiple of notch_disp
            # Work around for really terrible floating point division
            comp1 = float(notch) / self.notch_disp
            comp2 = np.round((float(notch) / self.notch_disp))

            if np.isclose(comp1, comp2):
                # Numbers
                fw = metrics.width(str(notch))
                fh = metrics.height() / 3  # 3 seems to work for text
                nr_x = notch_x1 - notch_width / 2
                qp.drawText(nr_x - fw, nh + fh, str(notch))
                qp.drawLine(
                    notch_x1,
                    nh,
                    notch_x2 + pen_width,
                    nh)  # Adjust for balance on either side

            else:
                notch_shrink = notch_width / 4
                qp.drawLine(
                    notch_x1 + notch_shrink,
                    nh,
                    notch_x2 - notch_shrink + pen_width,
                    nh)

    def translation(self, dy):
        self.mid += dy
        self.start += dy
        self.end += dy

        self.updateNotches()
        self.repaint()

    def updateNotches(self):
        start = math.floor(
            self.start / self.unit_value) * float(self.unit_value)
        end = math.ceil(
            self.end / self.unit_value) * float(self.unit_value) - self.unit_value
        self.notches = np.arange(start, end, -self.unit_value)

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton and not self.drag:
            self.origin = event.pos()
            self.rubberband.setGeometry(
                QtCore.QRect(self.origin, QtCore.QSize()))
            self.rubberband.show()

        if (event.button() == QtCore.Qt.RightButton and not
                self.rubberband.isVisible()):
            self.drag = True
            self.drag_origin = event.pos().y()

        if (event.button() == QtCore.Qt.MiddleButton and not
                self.rubberband.isVisible() and not
                self.drag):
            self.set_defaults()
            self.repaint()

        QtGui.QWidget.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):

        if self.rubberband.isVisible():
            self.rubberband.setGeometry(
                QtCore.QRect(self.origin, event.pos()).normalized())
        elif self.drag:
            dy = event.pos().y() - self.drag_origin
            self.drag_origin = event.pos().y()
            self.translation(float(dy) / self.get_unit_height())

        # Check for tooltips
        text = self.d_tooltips.tooltip(event.pos())
        if text:
            QtGui.QToolTip.showText(self.mapToGlobal(event.pos()), text, self)
        else:
            QtGui.QToolTip.hideText()
        QtGui.QWidget.mouseMoveEvent(self, event)

    def mouseReleaseEvent(self, event):
        if (self.rubberband.isVisible() and
                event.button() == QtCore.Qt.LeftButton):
            self.rubberband.hide()
            rect = self.rubberband.geometry()

            # Find selected
            del self.selected[:]
            depths = zip(self.depths, self.depth_heights)
            for depth in depths:

                # Assuming depth x = middle line, depth y in list
                point = (self.size().width() / 2, depth[1])
                if rect.contains(*point):
                    self.selected.append(depth[0])

            if self.selected:
                print('Selected: ' + str(self.selected))

            self.s.selected_updated.emit()
            # self.repaint()
        elif event.button() == QtCore.Qt.RightButton:
            self.drag = False

    def wheelEvent(self, event):
        dz = event.delta() / 120  # Standard 120 unit per notch scroll speed
        change = self.zoom ** int(-dz)
        self.start = ((self.start - self.mid) * change) + self.mid
        self.end = self.mid - ((self.mid - self.end) * change)

        # Update notches and display at specific zoom levels
        self.z_change *= change
        positive = 0
        # if self.z_change < 1:
        #     positive = 1
        zero = list(self.z_vector).index(1)
        index = bisect_left(self.z_vector, self.z_change) + positive

        # Boundary conditions
        if index > zero:
            max_index = len(self.z_vector) - 1
            index = index - 1 if index < max_index else max_index - 1
        elif index <= zero:
            index = index if index > 0 else 1

        self.unit_value = self.z_vector[index]
        self.notch_disp = self.z_vector[index + 1]

        self.updateNotches()
        self.repaint()

        QtGui.QWidget.wheelEvent(self, event)


class DepthTooltip(QtGui.QWidget):
    def __init__(self, depths, depth_widths, depth_heights, pen_width):

        self.depths = np.array(depths)
        self.depth_widths = np.array(depth_widths)
        self.depth_heights = np.array(depth_heights)
        self.pen_width = pen_width / 2.
        self.length = self.depths.size

        # Adjust for minor display discrepancies
        self.offsets()

    def offsets(self):
        # Point drawing shifts it over by 1 pixel
        self.depth_widths = self.depth_widths + 1

        # Makes it easier to acquire a point
        self.pen_width = self.pen_width + .7

    def tooltip(self, pos):
        x_vec = np.abs(np.ones(self.length) * pos.x() - self.depth_widths)
        y_vec = np.abs(np.ones(self.length) * pos.y() - self.depth_heights)
        close_y = y_vec <= self.pen_width

        text = ''
        # Check x is close
        if x_vec[close_y].size != 0:
            x_ind_min = np.argmin(x_vec[close_y])
            ind_min = np.where(close_y)[0][x_ind_min]
            # Check y is close
            if x_vec[ind_min] <= self.pen_width:
                depth = self.depths[ind_min]
                text = str(depth)

        return text
