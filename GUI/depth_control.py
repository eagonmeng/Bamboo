import math
import numpy as np
from bisect import bisect_left
from PyQt4 import QtGui, QtCore
from scipy.signal import savgol_filter, butter, filtfilt
from core.data import settings


# Constant settings
VERTICAL_PADDING_FRACTION = 1. / 20
HASH_LINE_COLOR = (50, 50, 50, 128)
HASH_BACKGROUND_COLOR = (150, 150, 150, 128)
DOTS_COLOR = (0, 0, 0)


# Signal class
class UpdateSignal(QtCore.QObject):

    selected_updated = QtCore.pyqtSignal(list)
    selected_annotated = QtCore.pyqtSignal(list)
    set_defaults = QtCore.pyqtSignal()
    wheel_updated = QtCore.pyqtSignal(QtCore.QEvent)
    translation_updated = QtCore.pyqtSignal(float)


class DepthControl(QtGui.QWidget):

    def __init__(self, vpf=VERTICAL_PADDING_FRACTION):
        super(DepthControl, self).__init__()

        self.rubberband = QtGui.QRubberBand(
            QtGui.QRubberBand.Rectangle, self)
        self.setMouseTracking(True)

        # Control bool for active selection
        self.active_select = False

        # Vertical padding fraction (of height)
        self.vpf = vpf

        self.initUI()

    def initUI(self):

        self.depths = []
        self.depth_heights = []
        self.selected = []

        # For hash rate display
        self.display_hashes = False
        self.patient = None
        self.channel = None

        self.set_defaults()

        # Size parameters (fractions of total size)
        self.notch_width_fraction = 1. / 5

        # Zoom stuffs
        cutoffs = [5, 2]
        levels = 3
        self.set_zoom(np.array(cutoffs), levels)
        self.zoom = 1.1  # Zoom speed (enlarge axis)

        # Text and axis width
        self.axis_width = 1

        # Drag internal variables
        self.drag = False
        self.drag_origin = 0

        # Signal
        self.s = UpdateSignal()

        # Annotation mode
        self.annotation_mode = False

    def set_defaults(self, start=settings.depth_control_axis[0], end=settings.depth_control_axis[1], unit_value=1, notch_disp=5):
        self.start = start  # Value associated with top pixel of axis
        self.end = end
        self.mid = (self.start + self.end) / 2
        self.unit_value = unit_value
        self.notch_disp = notch_disp  # Display every notch_disp units
        self.z_change = 1  # Zoom coefficient
        self.updateNotches()

    def get_axis_height(self):
        size = self.size()
        height = size.height()

        # Vertical padding (top and bottom) for axis
        v_padding = height * self.vpf
        return height - (2 * v_padding)

    def get_unit_height(self):
        axis_height = self.get_axis_height()
        return float(axis_height) / ((self.start - self.end))

    def set_zoom(self, cutoffs, levels):
        # Custom zoom vector
        # total_scale = np.prod(cutoffs)
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

    def updatePatient(self, patient):
        self.patient = patient

    def updateChannel(self, channel):
        self.channel = channel

    def paintEvent(self, e):

        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawWidget(qp)
        qp.end()

    def drawWidget(self, qp):

        # Draw the axis
        self.drawAxis(qp)

        # Draw the smoothed hashrates
        self.draw_smoothed_hash(qp)

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

                # Draw hash display if needed:
                if self.display_hashes:
                    if self.patient is not None and self.channel is not None:
                        hashpen = QtGui.QPen()
                        hashpen.setWidth(2)
                        color = QtGui.QColor(*HASH_LINE_COLOR)
                        hashpen.setColor(color)
                        qp.setPen(hashpen)

                        # Calculate relative width
                        w_ratio = self.patient.hash_depth_list[self.channel][depth]
                        x1 = max(int((1-w_ratio)*float(width)/2), 0)
                        x2 = width - x1
                        qp.drawLine(x1, depth_height, x2, depth_height)

                # Draw the point itself
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
        if self.display_hashes and self.patient is not None and self.channel is not None:
            hashrates = self.patient.hashrates[self.channel]
        else:
            hashrates = None

        self.d_tooltips = DepthTooltip(
            adjusted_depths, depth_widths, self.depth_heights, 
            pen_width, hashrates)

        # Draw the bar display on the side
        self.draw_annotation_bar(qp)

    # Draw the axis
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

        # Additional calculations
        unit_height = self.get_unit_height()
        max_label_width = (width - notch_width) / 2. - 1

        # Get pen
        qpen = QtGui.QPen()
        qpen.setWidth(self.axis_width)
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
                # Adjust font width
                metrics = qp.fontMetrics()
                fw = metrics.width(str(notch))
                if fw > max_label_width:
                    scale_down = float(max_label_width) / fw
                    font = qp.font()
                    font.setPointSize(
                        font.pointSize() * scale_down)
                    qp.setFont(font)

                # Draw numbers
                fh = metrics.height() / 3  # 3 seems to work for text
                fw = metrics.width(str(notch))
                nr_x = (notch_x1 - fw) / 2.
                qp.drawText(nr_x, nh + fh, str(notch))
                # qp.drawLine(notch_x1, nh, notch_x2, nh)
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
                    notch_x2 - notch_shrink + pen_width / 4.,
                    nh)

    def translation(self, dy):
        dy = float(dy) / self.get_unit_height()

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

    # Draw the smoothed hashfunction
    def draw_smoothed_hash(self, qp):
        if self.display_hashes and self.patient is not None and self.channel is not None:

            # Constants
            size = self.size()
            width = size.width()
            height = size.height()
            v_padding = height * self.vpf
            axis_height = height - (2 * v_padding)
            unit_height = self.get_unit_height()

            # Vector to smooth
            smoothed = np.zeros(int(self.get_axis_height())+1)

            # Offset factor used in main drawWidget method
            pen_width = 3

            # Loop through all relevant depths
            current = []
            for depth in self.depths:
                depth_height = (height / 2.) - (depth - self.mid) * unit_height
                depth_width = width / 2
                if (depth_height >= v_padding - pen_width and
                        depth_height <= v_padding + axis_height):
                # if (depth_height >= v_padding and
                #         depth_height <= v_padding + axis_height):

                    # Normalized hash value
                    normalized = self.patient.hash_depth_list[self.channel][depth]
                    smoothed[int(depth_height - v_padding)] = normalized
                    current.append(normalized)

            # Saviztky-Golay implementation
            # smoothed = savgol_filter(smoothed, settings.smooth_window, settings.smooth_polynomial)
            if current:
                # Forward-background filter
                b, a = butter(settings.smooth_order, settings.smooth_cutoff)
                smoothed = filtfilt(b, a, smoothed)

                # Normalize
                if np.max(smoothed) != 0:
                    smoothed = smoothed/float(np.max(smoothed))
                    smoothed = smoothed * float(np.max(current))

                # Cutoff all values exceeding depth boundaries
                # last_height = (height / 2.) - (self.depths[-1] - self.mid) * unit_height - v_padding
                # first_height = (height / 2.) - (self.depths[0] - self.mid) * unit_height - v_padding
                # first_height = max(int(first_height), 0)
                # last_height = min(len(smoothed), int(last_height))
                # smoothed[last_height:] = 0
                # smoothed[:first_height] = 0

                # Alternative cutoff based on axis maximums
                first_height = (height/2.)-(settings.depth_control_axis[0]-self.mid)*unit_height-v_padding
                last_height = (height/2.)-(settings.depth_control_axis[1]-self.mid)*unit_height-v_padding
                first_height = max(int(first_height), 0)
                last_height = min(len(smoothed), int(last_height))
                smoothed[first_height] = 0
                smoothed[last_height:] = 0

                import pyqtgraph as pg
                # pg.plot(smoothed)
                # Now draw the smoothed background
                for idx, w_ratio in enumerate(smoothed):
                    if w_ratio > 0:
                        hashpen = QtGui.QPen()
                        hashpen.setWidth(2)
                        color = QtGui.QColor(*HASH_BACKGROUND_COLOR)
                        hashpen.setColor(color)
                        qp.setPen(hashpen)

                        # Calculate relative width
                        x1 = max(int((1-w_ratio)*float(width)/2), 0)
                        x2 = width - x1
                        qp.drawLine(x1, v_padding + idx, x2, v_padding + idx)

    # Draw annotation progress bar
    def draw_annotation_bar(self, qp):
        if self.patient is not None and self.channel is not None:

            # Constants
            size = self.size()
            width = size.width()
            height = size.height()
            v_padding = height * self.vpf
            axis_height = height - (2 * v_padding)
            unit_height = self.get_unit_height()

            # Depth mapping dictionary
            depths_dict = dict(zip(self.depths, self.depth_heights))

            bar, dots = self.patient.get_annotation_markers(self.channel)

            # Draw all bars
            pen = QtGui.QPen()
            pen.setWidth(3)
            for item in bar:
                depths, label, color = item
                color = QtGui.QColor(*color)
                pen.setColor(color)
                qp.setPen(pen)

                # If the bar is just a point
                if depths[0] == depths[1]:
                    qp.drawPoint(width, depths_dict[depths[0]])
                else:
                    qp.drawLine(width, depths_dict[depths[0]], width, depths_dict[depths[1]])
                
                # Load the tooltip for bars
                self.d_tooltips.load_bar((depths, label))

            # Draw all dots
            pen.setColor(QtGui.QColor(*DOTS_COLOR))
            qp.setPen(pen)
            for dot in dots:
                qp.drawPoint(width, depths_dict[dot[0]])

                # Load the tooltip for dots
                self.d_tooltips.load_dot(dot)

    '''
    Interactive elements (mouse control, etc.)
    '''
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
            self.active_select = True
            self.s.set_defaults.emit()

        QtGui.QWidget.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):

        if self.rubberband.isVisible():
            self.rubberband.setGeometry(
                QtCore.QRect(self.origin, event.pos()).normalized())
        elif self.drag:
            dy = event.pos().y() - self.drag_origin
            self.drag_origin = event.pos().y()

            # Translate and notify others
            self.active_select = True
            self.s.translation_updated.emit(float(dy))
            self.translation(float(dy))

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
            newly_selected = []
            depths = zip(self.depths, self.depth_heights)
            for depth in depths:

                # Assuming depth x = middle line, depth y in list
                point = (self.size().width() / 2, depth[1])
                if rect.contains(*point):
                    # self.selected.append(depth[0])
                    newly_selected.append(depth[0])


            if self.annotation_mode:
                self.s.selected_annotated.emit(newly_selected)
                self.repaint()
            else:
                del self.selected[:]
                self.selected = newly_selected
                if self.selected:
                    print('\nSelected: ' + str(self.selected))

                # Make sure to set self as actively being selected
                self.active_select = True

                self.s.selected_updated.emit(self.selected)

            # self.repaint()
        elif event.button() == QtCore.Qt.RightButton:
            self.drag = False

    def wheelEvent(self, event):
        # Notify other links
        self.active_select = True
        self.s.wheel_updated.emit(event)
        self.wheel_zoom(event)

    def wheel_zoom(self, event):

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
    def __init__(self, depths, depth_widths, depth_heights, pen_width, hashrates):

        self.depths = np.array(depths)
        self.depth_widths = np.array(depth_widths)
        self.depth_heights = np.array(depth_heights)
        self.pen_width = pen_width / 2.
        self.length = self.depths.size
        self.hashrates = hashrates

        # Empty storage for custom displays
        self.bars = []
        self.dots = []

        # Create depth dictionary
        self.depth_dict = dict(zip(self.depths, self.depth_heights))

        # Adjust for minor display discrepancies
        self.offsets()

    def offsets(self):
        # Point drawing shifts it over by 1 pixel
        self.depth_widths = self.depth_widths + 1

        # Makes it easier to acquire a point
        self.pen_width = self.pen_width + .7

        # Alternative option for even greater ease
        self.fat_width = self.pen_width + 2


    '''
    Annotation methods
    '''
    # Initialize tooltips for bars
    def load_bar(self, bar):
        # Format of bar is ((d1, d2), text)
        depths, text = bar
        if depths[0] == depths[1]:
            self.load_dot((depths[0], text))
        else:
            new = ((self.depth_dict[depths[0]], self.depth_dict[depths[1]]), text)
            if new not in self.bars:
                self.bars.append(new)

    # Initialize tooltip for dots
    def load_dot(self, dot):
        # Format of dot is (depth, text)
        depth, text = dot
        text = ', '.join(text)
        new = (self.depth_dict[depth], text)
        if new not in self.dots:
            self.dots.append(new)

    '''
    Tooltip
    '''
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
                if self.hashrates is None:
                    text = str(depth)
                else:
                    text = str(depth) + ', HR: ' + str(self.hashrates[depth]) + 'Hz'

        # In order of priority, we overlay the bar on the right
        width = self.depth_widths[0] * 2
        if np.abs(pos.x() - width) <= self.fat_width:
            # Now we check for bars first
            for bar in self.bars:
                depths, label = bar
                if depths[0]-self.fat_width <= pos.y() and pos.y() <= depths[1]+self.fat_width:
                    text = label

            # Check for dots
            for dot in self.dots:
                depth, label = dot
                if depth-self.fat_width <= pos.y() and pos.y() <= depth+self.fat_width:
                    if text != '':
                        text = text + ' and ' + label
                    else:
                        text = label
                    break

        return text
