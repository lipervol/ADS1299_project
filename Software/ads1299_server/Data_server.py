#!/usr/bin/python
import sys
import zmq
from ADS1299_API import *
import time
from threading import Thread


class Dataflow(object):
    def __init__(self):
        super().__init__()
        self.state = 0
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.PUSH)
        self.dev = ADS1299(num_channels=8, sampling_rate=250, clientUpdateHandles=[self.callback])
        self.dev.openDevice()

    def callback(self, data):
        self.socket.send_string(str(data))

    def send_data(self, port, duration, num_channels, sampling_rate):
        self.socket.bind("tcp://*:%d" % port)
        print("[*]Data Flow start on port:%d" % port)
        self.dev.get_num_channels(num_channels)
        self.dev.get_sampling_rate(sampling_rate)
        self.dev.startTestStream()
        running_time = 0
        while self.state != 0:
            time.sleep(1)
            running_time += 1
            if running_time == duration:
                break
        self.socket.unbind(self.socket.last_endpoint)
        self.dev.stopStream()
        self.state = -1
        print("[*]Stop after running for %ds" % running_time)


dataFlow = Dataflow()
ctrlFlow_context = zmq.Context()
ctrlFlow_socket = ctrlFlow_context.socket(zmq.REP)
ctrlFlow_socket.bind("tcp://*:5555")
print("[*]Server Listening on 5555")
while True:
    com = ctrlFlow_socket.recv_string()
    print("[*]Recv Command:", com)
    if com[0] == "s":
        if dataFlow.state == 1:
            dataFlow.state = 0
            while dataFlow.state == 0:
                pass
        com = com.split(":")
        p, d, n, s = int(com[1]), int(com[2]), int(com[3]), int(com[4])
        dataFlow_th = Thread(target=dataFlow.send_data, args=(p, d, n, s))
        dataFlow.state = 1
        dataFlow_th.start()
    else:
        if dataFlow.state == 1:
            dataFlow.state = 0
            while dataFlow.state == 0:
                pass
    ctrlFlow_socket.send_string("ACK")
