import serial
import numpy as np
from scipy.signal import butter, filtfilt
from collections import deque
from PyQt5 import QtWidgets, QtCore
import pyqtgraph as pg
import sys

# =====================================================
# Konfiguration
# =====================================================
PORT = "COM3"          # anpassen!
BAUD = 115200          # Baudrate der Seriellen Schnittstelle (muss mit Arduino übereinstimmen)
SAMPLE_RATE = 250      # Frequenz der vom Arduino ankommenden EEG-Werte in Hz
BUFFER_SEC = 5
N_SAMPLES = SAMPLE_RATE * BUFFER_SEC
CHANNELS = 2

# =====================================================
# Bandpass Filter
# =====================================================
def bandpass(data, low, high, fs, order=2):
    nyq = fs * 0.5
    b, a = butter(order, [low / nyq, high / nyq], btype='band')
    return filtfilt(b, a, data)

# =====================================================
# GUI Klasse
# =====================================================
class EEGViewer(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EEG Motor Imagery Viewer")
        self.resize(1000, 700)

        # Serielle Verbindung
        self.ser = serial.Serial(PORT, BAUD, timeout=1)

        # Ringpuffer
        self.buffers = [deque(maxlen=N_SAMPLES) for _ in range(CHANNELS)]

        # Dropdown
        self.modeBox = QtWidgets.QComboBox()
        self.modeBox.addItems([
            "Rohsignal",
            "µ-Band (8–12 Hz)",
            "β-Band (13–30 Hz)"
        ])

        # Plot Setup
        self.graph = pg.GraphicsLayoutWidget()
        self.plots = []
        self.curves = []

        for i in range(CHANNELS):
            p = self.graph.addPlot(row=i, col=0)
            p.setLabel("left", f"CH {i+1}")
            p.showGrid(x=True, y=True)
            p.setYRange(-300, 300)

            curve = p.plot(pen=pg.mkPen(width=1))
            self.plots.append(p)
            self.curves.append(curve)

        self.plots[-1].setLabel("bottom", "Samples")

        # Layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.modeBox)
        layout.addWidget(self.graph)
        self.setLayout(layout)

        # Timer
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(15)

    def update(self):
        # Daten einlesen
        while self.ser.in_waiting:
            try:
                line = self.ser.readline().decode().strip()
                values = list(map(int, line.split(',')))
                if len(values) == CHANNELS:
                    for i in range(CHANNELS):
                        self.buffers[i].append(values[i])
            except:
                pass

        if len(self.buffers[0]) < N:
            return

        mode = self.modeBox.currentText()

        for i in range(CHANNELS):
            data = np.array(self.buffers[i], dtype=float)

            # DC-Offset entfernen
            data -= np.mean(data)

            # Modusabhängige Verarbeitung
            if mode == "µ-Band (8–12 Hz)":
                data = bandpass(data, 8, 12, SAMPLE_RATE)
                self.plots[i].setYRange(-100, 100)

            elif mode == "β-Band (13–30 Hz)":
                data = bandpass(data, 13, 30, SAMPLE_RATE)
                self.plots[i].setYRange(-100, 100)

            else:
                self.plots[i].setYRange(-300, 300)

            self.curves[i].setData(data)

# =====================================================
# Main
# =====================================================
if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    viewer = EEGViewer()
    viewer.show()
    sys.exit(app.exec_())
