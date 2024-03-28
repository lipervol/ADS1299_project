#!/usr/bin/python
import sys
import zmq
from ADS1299_API import *
import time
from threading import Thread

try:
	port = int(sys.argv[1])
	duration = int(sys.argv[2])
	num_channels = int(sys.argv[3])
except:
	print("[*]Usage:python test.py [port] [duration] [num_channels]")
	exit(0)

context = zmq.Context()
socket = context.socket(zmq.PUSH)
socket.bind("tcp://*:%d"%(port))
def Callback(data):
	socket.send_string(str(data))

print("[*]Server start on port:%d"%(port))
dev = ADS1299(num_channels=num_channels, sampling_rate=250, clientUpdateHandles=[Callback])
dev.openDevice()
dev.startTestStream()
time.sleep(duration)
dev.stopStream()
dev.closeDevice()
time.sleep(1)
print("[*]Stop after running for %ds"%(duration))
