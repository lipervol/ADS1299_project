import threading
import time
import zmq
import numpy as np
import re
from threading import Thread
import sys
import os
from surface import Ui_Dialog
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
import pyqtgraph as pg

pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


def recv_data(addr, dat):
    context = zmq.Context()
    socket = context.socket(zmq.PULL)
    socket.connect(addr)
    while True:
        msg = socket.recv_string()
        msg = msg[1:-1]
        msg = re.sub("\n", "", msg)
        msg = re.sub("\s+", " ", msg)
        msg = re.sub("\s$", "", msg)
        msg = re.sub("^\s", "", msg)
        msg = msg.split(" ")
        msg = list(map(float, msg))
        dat.append(msg)


class MainWindow(QtWidgets.QMainWindow, Ui_Dialog):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.gridlayout = QtWidgets.QGridLayout(self.groupBox)
        self.state = 0
        self.t = QtCore.QTimer()
        self.t.timeout.connect(self.updateData)
        self.ctrlFlow_context = zmq.Context()
        self.ctrlFlow_socket = self.ctrlFlow_context.socket(zmq.REQ)
        self.ctrlFlow_socket.setsockopt(zmq.SNDTIMEO, 3500)
        self.ctrlFlow_socket.setsockopt(zmq.RCVTIMEO, 3500)

        # Get Setting
        # 1.
        self.comboBox_5.addItems(["250", "500", "1000", "2000"])
        self.IP = ""
        self.port = ""
        self.sample_rate = 0
        self.duration = 0
        self.num_channels = 0
        self.ctrlFlow_addr = ""
        self.address = ""
        self.raw_data = []
        self.recv_data_th = None
        self.pushButton.clicked.connect(self.clickButton1)
        # 2.
        self.plot_channel = [0, 0, 0, 0]
        self.time_width = 2
        self.horizontalSlider.valueChanged.connect(self.valueChange)
        self.pushButton_2.clicked.connect(self.clickButton2)
        # 3.
        self.save_data = None
        self.save_path = None
        self.pushButton_3.clicked.connect(self.clickButton3)
        self.pushButton_4.clicked.connect(self.clickButton4)
        # Logo
        self.label_16.setPixmap(QtGui.QPixmap(get_resource_path("logo.png")))
        # Plot1
        self.pw1 = pg.PlotWidget()
        self.pw1.setLabel("left", "Value", units="V")
        self.pw1.setLabel("bottom", "Time", units="s")
        self.pl1 = self.pw1.plot()
        self.pl1.setPen((210, 105, 30))
        self.gridlayout.addWidget(self.pw1, 2, 0)
        # Plot2
        self.pw2 = pg.PlotWidget()
        self.pw2.setLabel("left", "Value", units="V")
        self.pw2.setLabel("bottom", "Time", units="s")
        self.pl2 = self.pw2.plot()
        self.pl2.setPen((160, 32, 240))
        self.gridlayout.addWidget(self.pw2)
        # Plot3
        self.pw3 = pg.PlotWidget()
        self.pw3.setLabel("left", "Value", units="V")
        self.pw3.setLabel("bottom", "Time", units="s")
        self.pl3 = self.pw3.plot()
        self.pl3.setPen((0, 0, 205))
        self.gridlayout.addWidget(self.pw3)
        # Plot4
        self.pw4 = pg.PlotWidget()
        self.pw4.setLabel("left", "Value", units="V")
        self.pw4.setLabel("bottom", "Time", units="s")
        self.pl4 = self.pw4.plot()
        self.pl4.setPen((0, 139, 139))
        self.gridlayout.addWidget(self.pw4)

    def recv_data(self, addr, dat):
        context = zmq.Context()
        socket = context.socket(zmq.PULL)
        socket.connect(addr)
        socket.setsockopt(zmq.RCVTIMEO, 1000)
        while self.state:
            try:
                msg = socket.recv_string()
                msg = msg[1:-1]
                msg = re.sub("\n", "", msg)
                msg = re.sub("\s+", " ", msg)
                msg = re.sub("\s$", "", msg)
                msg = re.sub("^\s", "", msg)
                msg = msg.split(" ")
                msg = list(map(float, msg))
                dat.append(msg)
            except zmq.error.Again:
                break

    def updateData(self):
        if self.state != 0:
            num_points = int(self.time_width * self.sample_rate)
            xd = np.linspace(0, 1, num_points) * self.time_width
            if len(self.raw_data) < num_points + 2:
                yd = np.zeros((num_points, self.num_channels))
            else:
                yd = np.array(self.raw_data[-1 * num_points - 1:-1])
            self.pl1.setData(x=xd, y=yd[:, self.plot_channel[0]])
            self.pl2.setData(x=xd, y=yd[:, self.plot_channel[1]])
            self.pl3.setData(x=xd, y=yd[:, self.plot_channel[2]])
            self.pl4.setData(x=xd, y=yd[:, self.plot_channel[3]])

    def clickButton1(self):
        # Get
        # 1
        self.IP = self.lineEdit.text()
        self.port = self.lineEdit_2.text()
        self.sample_rate = int(self.comboBox_5.currentText())
        self.duration = int(self.lineEdit_3.text())
        self.num_channels = int(self.lineEdit_4.text())
        # 2
        if self.comboBox.count() != self.num_channels:
            self.comboBox.clear()
            self.comboBox.addItems(["%d" % (i + 1) for i in range(self.num_channels)])
            self.comboBox_2.clear()
            self.comboBox_2.addItems(["%d" % (i + 1) for i in range(self.num_channels)])
            self.comboBox_3.clear()
            self.comboBox_3.addItems(["%d" % (i + 1) for i in range(self.num_channels)])
            self.comboBox_4.clear()
            self.comboBox_4.addItems(["%d" % (i + 1) for i in range(self.num_channels)])
        # Ctrl and Data
        self.ctrlFlow_addr = "tcp://" + self.IP + ":5555"
        self.address = "tcp://" + self.IP + ":" + self.port
        if self.state == 0:
            # Ctrl send
            try:
                self.ctrlFlow_socket.connect(self.ctrlFlow_addr)
                self.ctrlFlow_socket.send_string(
                    "s:" + self.port + ":" + self.lineEdit_3.text() + ":" + self.lineEdit_4.text() + ":"
                    + self.comboBox_5.currentText())
                response = self.ctrlFlow_socket.recv_string()
                self.ctrlFlow_socket.disconnect(self.ctrlFlow_addr)
                if response == "ACK":
                    # Data recv
                    self.state = 1
                    self.recv_data_th = Thread(target=self.recv_data, args=(self.address, self.raw_data))
                    self.recv_data_th.start()
                    self.t.start(int(1000 / self.sample_rate) if int(1000 / self.sample_rate) > 0 else 1)
                    self.pushButton.setText("Stop")
                else:
                    # todo
                    pass
            except zmq.error.Again:
                self.ctrlFlow_socket.close()
                self.ctrlFlow_socket = self.ctrlFlow_context.socket(zmq.REQ)
                self.ctrlFlow_socket.setsockopt(zmq.SNDTIMEO, 3000)
                self.ctrlFlow_socket.setsockopt(zmq.RCVTIMEO, 3000)
                QtWidgets.QMessageBox.information(self, "Parameter settings", "Connection timed out!",
                                                  QtWidgets.QMessageBox.Yes)
        else:
            if len(self.raw_data) != 0:
                self.save_data = np.array(self.raw_data[1:])
                self.label_13.setText(str(self.save_data.shape))
                self.raw_data.clear()
            try:
                self.ctrlFlow_socket.connect(self.ctrlFlow_addr)
                self.ctrlFlow_socket.send_string("e")
                response = self.ctrlFlow_socket.recv_string()
                self.ctrlFlow_socket.disconnect(self.ctrlFlow_addr)
                if response == "ACK":
                    self.state = 0
                    self.t.stop()
                    self.pushButton.setText("Set")
                else:
                    # todo
                    pass
            except zmq.error.Again:
                self.ctrlFlow_socket.close()
                self.ctrlFlow_socket = self.ctrlFlow_context.socket(zmq.REQ)
                self.ctrlFlow_socket.setsockopt(zmq.SNDTIMEO, 3000)
                self.ctrlFlow_socket.setsockopt(zmq.RCVTIMEO, 3000)
                QtWidgets.QMessageBox.information(self, "Parameter settings", "Connection timed out!",
                                                  QtWidgets.QMessageBox.Yes)

    def valueChange(self):
        v = self.horizontalSlider.value()
        self.time_width = float(v) * 0.1 + 0.1
        self.label_11.setText("%.1fs" % (float(v) * 0.1 + 0.1))

    def clickButton2(self):
        self.plot_channel[0] = int(self.comboBox.currentIndex())
        self.plot_channel[1] = int(self.comboBox_2.currentIndex())
        self.plot_channel[2] = int(self.comboBox_3.currentIndex())
        self.plot_channel[3] = int(self.comboBox_4.currentIndex())
        QtWidgets.QMessageBox.information(self, "Display settings", "Channel display set successfully!",
                                          QtWidgets.QMessageBox.Yes)

    def clickButton3(self):
        self.save_path = QtWidgets.QFileDialog.getExistingDirectory(self, "Select file save directory", "./",
                                                                    QtWidgets.QFileDialog.ShowDirsOnly)
        self.label_15.setText("Path:" + self.save_path)

    def clickButton4(self):
        if self.save_path is not None and self.save_data is not None:
            t = time.localtime()
            file_name = "ADS1299_{:4d}{:0>2d}{:0>2d}{:0>2d}{:0>2d}{:0>2d}.npy".format(t.tm_year, t.tm_mon, t.tm_mday,
                                                                                      t.tm_hour, t.tm_min,
                                                                                      t.tm_sec)
            np.save(self.save_path + "/" + file_name, self.save_data)
            QtWidgets.QMessageBox.information(self, "Data saving settings", "Data saved successfully!",
                                              QtWidgets.QMessageBox.Yes)
        else:
            if self.save_path is None:
                QtWidgets.QMessageBox.information(self, "Data saving settings", "Save path is empty!",
                                                  QtWidgets.QMessageBox.Yes)
            if self.save_data is None:
                QtWidgets.QMessageBox.information(self, "Data saving settings", "There is no data to save!",
                                                  QtWidgets.QMessageBox.Yes)


app = pg.mkQApp()
win = MainWindow()
win.setWindowIcon(QtGui.QIcon(get_resource_path("icon.ico")))
win.show()
while app.exec() == 0:
    win.state = 0
    time.sleep(1)
    sys.exit(0)
