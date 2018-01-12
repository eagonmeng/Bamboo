import pyqtgraph as pg
from pyqtgraph import QtCore
from core.data import settings
from core.data import preprocess_audio
pg.setConfigOption('useOpenGL', False)
import numpy as np
import sounddevice as sd

AUDIO_TIMER_UPDATE = 10 # In ms

class MultiLine(pg.QtGui.QGraphicsPathItem):
    def __init__(self, x, y):
        conn = np.ones(x.shape, dtype=bool)
        conn[:, -1] = 0
        self.path = pg.arrayToQPath(x.flatten(), y.flatten(), conn.flatten())

        pg.QtGui.QGraphicsPathItem.__init__(self, self.path)
        self.setPen(pg.mkPen('w'))  # White pen

    def shape(self):
        return pg.QtGui.QGraphicsItem.shape(self)

    def boundingRect(self):
        return self.path.boundingRect()


class UpdateSignal(QtCore.QObject):

    title_updated = QtCore.pyqtSignal(str)


class BothClickButton(pg.QtGui.QPushButton):

    right_clicked = pg.QtCore.pyqtSignal()

    def __init__(self, string):
        super(BothClickButton, self).__init__(string)

    def mousePressEvent(self, event):
        super(BothClickButton, self).mousePressEvent(event)

        if event.button() == pg.QtCore.Qt.RightButton:
            self.right_clicked.emit()


class DefaultPlotWidget(pg.PlotWidget):

    def __init__(self, src=None):
        super(DefaultPlotWidget, self).__init__()

        self.src = src
        self._title = ''

        # Modes: subsample, mean, peak
        self.getPlotItem().setDownsampling(ds=True, auto=True, mode='subsample')

        # self.getViewBox().setMouseMode(pg.ViewBox.RectMode)

        # self.show()

        self.data = []

        # Default plot settings
        self.x_scale = float(settings.data_hz)
        self.setLabel('bottom', text=settings.data_x_label, units=settings.data_x_units, **settings.label_style)
        # self.setLabel('bottom', text=settings.data_x_label, units=settings.data_x_units)
        self.y_scale = float(settings.data_gain)
        # self.setLabel('left', text=settings.data_y_label)

        # Signal for updating title of dock
        self.s = UpdateSignal()


        '''
        Audio play back features
        '''

        # Button for audio playback
        button = BothClickButton('Audio')
        button.setCheckable(True)

        # width = button.fontMetrics().boundingRect(button.text()).width() + 15
        # height = button.fontMetrics().boundingRect(button.text()).height() + 7  
        # button.setMaximumWidth(width)
        # button.setMaximumHeight(height)

        button.setStyleSheet('''QPushButton { background-color: #000000; 
                                border:1px solid #cccccc;
                                color: #cccccc }
                            '''
                            'QPushButton:checked { background-color: #eeeeee;color: #000000 }')

        self.play_button = button

        # Add signals to button
        self.play_button.clicked.connect(self.play_audio)
        self.play_button.right_clicked.connect(self.swap_audio)

        # Add buttons
        self.scene().addWidget(self.play_button)

        self.play_spike_audio = settings.default_spike_audio

        ## Progress line
        self.audio_line = None
        self.audio_timer = pg.QtCore.QTimer()

    # def wheelEvent(self, event):
    #     # Prevent scrolling in the larger scroll area
    #     event.ignore()

    ''' 
    Audio Methods
    '''

    # Play audio
    def play_audio(self):
        if self.play_button.isChecked():
            data = preprocess_audio(self.data, spikes_only=self.play_spike_audio)

            # Track progress
            self.audio_line = self.addLine(x=0)
            self.audio_timer = pg.QtCore.QTimer()
            self.audio_timer.setInterval(AUDIO_TIMER_UPDATE)
            self.audio_timer.timeout.connect(self.update_audio_line)
            sd.play(data)
            self.audio_timer.start()
            
        else:
            sd.stop()
            self.audio_timer.stop()
            self.audio_line.hide()
            self.audio_line = None

    # Swap the audio mode
    def swap_audio(self):
        if self.play_spike_audio:
            self.play_button.setText('Audio')
            self.play_button.resize(self.play_button.sizeHint().width(), self.play_button.sizeHint().height())
            self.play_spike_audio = False
        else:
            self.play_button.setText('Audio (spikes)')
            self.play_button.resize(self.play_button.sizeHint().width(), self.play_button.sizeHint().height())
            self.play_spike_audio = True
        self.play_button.setChecked(False)

    # Update the line
    def update_audio_line(self):
        value = self.audio_line.value() + AUDIO_TIMER_UPDATE/float(1000)
        if value > (len(self.data) / self.x_scale):
            self.play_button.setChecked(False)
            self.play_audio()
        else:
            self.audio_line.setValue(value)

    '''
    Data Methods
    '''

    def plot_data(self, data):
        self.clear()
        self.showButtons()
        self.data = data
        try:
            points = data.shape[0]
            lines = data.shape[1]
            if lines > 1:
                self.getViewBox().disableAutoRange()

                # Color option for separate multiple plots
                # for i in range(lines):
                #     item = PathItem(np.arange(points), data[:,i].flatten())
                #     item.setPen(pg.mkPen((i, lines)))
                #     self.widget.addItem(item)

                xdata = np.tile(np.arange(points), (lines, 1))

                # Assume data is vertical
                item = MultiLine(xdata, data.T)
                item.setPen(pg.mkPen('w'))
                self.addItem(item)

                self.getViewBox().enableAutoRange()
        except IndexError:
            self.plot(np.arange(len(data)) / self.x_scale, data / self.y_scale, pen=pg.mkPen(width=1))

            # Update title
            text = 'Recording length: %f (s)' % (len(data) / self.x_scale)
            self.s.title_updated.emit(text)

            # self.getViewBox().enableAutoRange()

    def set_text(self, text):
        text_item = pg.TextItem(text)
        self.addItem(text_item, ignoreBounds=True)
        self.getViewBox().setRange(xRange=(0, 1), yRange=(0, 1))
        text_item.setPos(0, 1)

    def text_mode(self):
        self.getViewBox().disableAutoRange()
        self.hideButtons()

    def update_plot(self):
        # Load complete depth file
        self.data_id = self.patient.load(self.depth)
        data = self.src.cache[self.data_id][self.channel].squeeze()

        self.clear()

        '''
        Handling of data types to be done modularly?
        '''
        # Text display for single value (usually constant)
        if data.size == 1:
            self.text_mode()
            text = str(self.channel) + ' = ' + str(data)
            self.set_text(text)
        else:
            self.plot_data(data)

    def update_values(self, patient, channel, depth):
        self.patient = patient
        self.channel = channel
        self.depth = depth

        # Title used to indicate depth for now
        self._title = 'Depth: %.2f' % depth
        self.setTitle(self._title)

        self.update_plot()
        return self.data_id  # Maybe useful eventually

    def get_title(self):
        return self._title

    # Slot for external x range control
    def set_x_range(self, x_range):
        # We receive in terms of ms
        for _ in range(2):
            self.getViewBox().setXRange(x_range[0]/1000., x_range[1]/1000.)

    # Slot for external y range control
    def set_y_range(self, y_range):
        for _ in range(2):
            self.getViewBox().setYRange(*y_range)
