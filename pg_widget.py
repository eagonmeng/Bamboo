from enaml.core.declarative import d_
from enaml.widgets.api import RawWidget
from atom.api import List, set_default, Unicode, Dict, observe, Tuple
import numpy as np

import pyqtgraph as pg
# PyQt
from PyQt4 import QtGui, QtCore
from enaml.qt.qt_control import QtControl

# Custom QGraphicsPathItem with proper bounds
class MultiLine(pg.QtGui.QGraphicsPathItem):
    def __init__(self, x, y):
        conn = np.ones(x.shape, dtype=bool)
        conn[:,-1] = 0 
        self.path = pg.arrayToQPath(x.flatten(), y.flatten(), conn.flatten())

        pg.QtGui.QGraphicsPathItem.__init__(self, self.path)
        self.setPen(pg.mkPen('w')) # White pen

    def shape(self):
        return pg.QtGui.QGraphicsItem.shape(self)

    def boundingRect(self):
        return self.path.boundingRect()


class PyQtGraph(RawWidget):

    hug_width = set_default('ignore')
    hug_height = set_default('ignore')
    resist_height = set_default('strong')
    resist_width = set_default('strong')

    title = d_(Unicode())
    cache = d_(Dict())
    key = d_(Tuple())
    channel = d_(Unicode())
    text = d_(Unicode())

    def create_widget(self, parent):
        widget = PyQtGraphWidget(parent)
        self.safe_plot(widget)
        # widget.set_title(self.title)
        # widget.set_text(self.text)
        return widget

    def safe_plot(self, widget):
        widget.clear()
        if self.key != ():
            try:
                data = self.cache[self.key][self.channel].squeeze()
                if data.size == 1:
                    widget.text_mode()
                    text = str(self.channel) + ' = ' + str(data)
                    widget.set_text(text)
                else:
                    widget.plot_data(data)
            except KeyError:
                print 'Could not plot data_id = ' + str(self.key) + ' channel: ' + str(self.channel)
                widget.text_mode()
                widget.set_text('Missing channel')


    @observe('key', 'title', 'text', 'channel')
    def key_update(self, change):
        if change['type'] == 'update':
            widget = self.get_widget()
            if widget is not None:
                switch = change['name']

                # Update based on observed change
                if switch == 'key' or switch == 'channel':
                    widget.clear()
                    self.safe_plot(widget)
                if switch == 'title':
                    widget.set_title(change['value'])
                if switch == 'text':
                    widget.set_text(change['value'])


class PyQtGraphWidget(QtGui.QWidget):

    def __init__(self, parent):
        super(PyQtGraphWidget, self).__init__(parent)

        self.widget = pg.PlotWidget()
        self.widget.setDownsampling(auto=True)

        vbox = QtGui.QVBoxLayout()
        vbox.addWidget(self.widget)
        self.setLayout(vbox)
        # self.widget.getViewBox().setMouseMode(pg.ViewBox.RectMode)

        self.show()

    def wheelEvent(self, event):
        # Prevent scrolling in the larger scroll area
        event.accept()

    def plot_data(self, data):
        self.widget.showButtons()
        try:
            points = data.shape[0]
            lines = data.shape[1]
            if lines > 1:
                self.widget.getViewBox().disableAutoRange()

                # Color option for separate multiple plots
                # for i in range(lines):
                #     item = PathItem(np.arange(points), data[:,i].flatten())
                #     item.setPen(pg.mkPen((i, lines)))
                #     self.widget.addItem(item)

                xdata = np.tile(np.arange(points), (lines, 1))
                item = MultiLine(xdata, data.T)
                item.setPen(pg.mkPen('w'))
                self.widget.addItem(item)

                self.widget.getViewBox().enableAutoRange()
        except IndexError:
            self.widget.plot(data)
            self.widget.getViewBox().enableAutoRange()

    def set_title(self, title):
        self.widget.setTitle(title)

    def clear(self):
        self.widget.getViewBox().disableAutoRange()
        self.widget.clear()

    def set_text(self, text):
        text_item = pg.TextItem(text)
        self.widget.addItem(text_item)
        self.widget.getViewBox().setRange(xRange=(0,1), yRange=(0,1))
        text_item.setPos(0, 1)

    def text_mode(self):
        self.widget.getViewBox().disableAutoRange()
        self.widget.hideButtons()