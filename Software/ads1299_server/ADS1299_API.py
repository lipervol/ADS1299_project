#!/usr/bin/python
import struct
import time
import spidev
import RPi.GPIO as GPIO
import numpy as np

nRESET_PIN = 23
nPWRDN_PIN = 24
DRDY_PIN = 25


class ADS1299(object):
    def __init__(self, num_channels=8, sampling_rate=250, clientUpdateHandles=[]):
        self.spi = spidev.SpiDev()
        self.SCALE_TO_UVOLT = 0.0000000121
        self.channels_per_chip = 8
        self.num_channels = num_channels
        self.sampling_rate = sampling_rate
        self.clientUpdateHandles = clientUpdateHandles
        # PIN
        self.nRESET_PIN = nRESET_PIN
        self.nPWRDN_PIN = nPWRDN_PIN
        self.DRDY_PIN = DRDY_PIN
        # REG
        self.REG_CONFIG1 = 0x01
        self.REG_CONFIG2 = 0x02
        self.REG_CONFIG3 = 0x03
        self.REG_CHnSET_BASE = 0x05
        self.REG_MISC = 0x15
        self.REG_BIAS_SENSP = 0x0D
        self.REG_BIAS_SENSN = 0x0E
        # COMMANDS
        self.RDATAC = 0x10
        self.SDATAC = 0x11

    def setnReset(self, state):
        if state:
            GPIO.output(self.nRESET_PIN, GPIO.HIGH)
        else:
            GPIO.output(self.nRESET_PIN, GPIO.LOW)

    def toggleReset(self):
        self.setnReset(False)
        time.sleep(0.2)
        self.setnReset(True)
        time.sleep(0.2)

    def setnPWRDN(self, state):
        if state:
            GPIO.output(self.nPWRDN_PIN, GPIO.HIGH)
        else:
            GPIO.output(self.nPWRDN_PIN, GPIO.LOW)

    def SPI_transmitByte(self, byte):
        self.spi.xfer2([byte])

    def SPI_writeSingleReg(self, reg, byte):
        self.spi.xfer2([reg | 0x40, 0x00, byte])

    def SPI_writeMultipleReg(self, start_reg, byte_array):
        tmp = [start_reg | 0x40]
        tmp.append(len(byte_array) - 1)
        for i in range(0, len(byte_array)):
            tmp.append(byte_array[i])
        self.spi.xfer2(tmp)

    def SPI_readMultipleBytes(self, nb_bytes):
        return self.spi.xfer2([0x00] * nb_bytes)

    def setSamplingRate(self):
        temp_reg_value = 0x90
        if self.sampling_rate == 2000:
            temp_reg_value |= 0x03
        elif self.sampling_rate == 1000:
            temp_reg_value |= 0x04
        elif self.sampling_rate == 500:
            temp_reg_value |= 0x05
        else:
            temp_reg_value |= 0x06
        self.SPI_writeSingleReg(self.REG_CONFIG1, temp_reg_value)

    def resetOngoingState(self):
        self.SPI_transmitByte(self.SDATAC)
        self.SPI_writeSingleReg(self.REG_CONFIG3, 0xE0)
        self.setSamplingRate()
        self.SPI_writeSingleReg(self.REG_CONFIG2, 0xC0)
        self.SPI_writeSingleReg(self.REG_BIAS_SENSP, 0x00)
        self.SPI_writeSingleReg(self.REG_BIAS_SENSN, 0x00)
        tx_buf = [0] * self.channels_per_chip
        for i in range(0, self.channels_per_chip):
            tx_buf[i] = 0x01
        self.SPI_writeMultipleReg(self.REG_CHnSET_BASE, tx_buf)

    def ADS1299Startup(self):
        self.setnReset(True)
        self.setnPWRDN(True)
        time.sleep(1)
        self.toggleReset()
        # self.resetOngoingState()
        # self.SPI_transmitByte(self.RDATAC)

    def openDevice(self):
        # SPI CONFIG
        self.spi.open(0, 0)
        self.spi.max_speed_hz = 1000000
        self.spi.mode = 0b01
        # GPIO CONFIG
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.nRESET_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.nPWRDN_PIN, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(self.DRDY_PIN, GPIO.IN)
        GPIO.add_event_detect(self.DRDY_PIN, GPIO.FALLING, callback=self.drdy_callback)

        # ADS1299 CONFIG
        self.ADS1299Startup()

    def closeDevice(self):
        self.spi.close()
        GPIO.cleanup()

    def conv24bitsToFloat(self, unpacked):
        literal_read = struct.pack('3B', unpacked[0], unpacked[1], unpacked[2])
        if (unpacked[0] > 127):
            pre_fix = bytes(bytearray.fromhex('FF'))
        else:
            pre_fix = bytes(bytearray.fromhex('00'))
        literal_read = pre_fix + literal_read;
        myInt = struct.unpack('>i', literal_read)[0]
        return myInt * self.SCALE_TO_UVOLT

    def drdy_callback(self, state):
        num_data = ((self.num_channels - 1) // 8 + 1) + self.num_channels
        bit_values = self.SPI_readMultipleBytes(num_data * 3)
        data_array = np.zeros(self.num_channels)
        idx = 0
        for i in range(num_data):
            data = bit_values[i * 3:(i + 1) * 3]
            if i % 9 != 0:
                data_array[idx] = self.conv24bitsToFloat(data)
                idx += 1
        for handle in self.clientUpdateHandles:
            handle(data_array)

    def setupEEGMode(self):
        tx_buf = [0] * self.channels_per_chip
        for i in range(0, self.channels_per_chip):
            tx_buf[i] = 0x60;
        self.SPI_writeMultipleReg(self.REG_CHnSET_BASE, tx_buf)
        self.SPI_writeSingleReg(self.REG_MISC, 0x20)

    def startEEGStream(self):
        self.resetOngoingState()
        self.setupEEGMode()
        self.SPI_transmitByte(self.RDATAC)

    def setupTestMode(self):
        self.SPI_writeSingleReg(self.REG_CONFIG2, 0xD0)
        tx_buf = [0] * self.channels_per_chip
        for i in range(0, self.channels_per_chip):
            tx_buf[i] = 0x65
        self.SPI_writeMultipleReg(self.REG_CHnSET_BASE, tx_buf)

    def startTestStream(self):
        self.resetOngoingState()
        self.setupTestMode()
        self.SPI_transmitByte(self.RDATAC)

    def stopStream(self):
        self.SPI_transmitByte(self.SDATAC)

    def get_num_channels(self, num_channels):
        self.num_channels = num_channels

    def get_sampling_rate(self, sampling_rate):
        self.sampling_rate = sampling_rate


if __name__ == "__main__":
    def DefaultCallback(data):
        print(str(data))


    print("[*]Start TEST")
    dev = ADS1299(num_channels=32, sampling_rate=250, clientUpdateHandles=[DefaultCallback])
    dev.openDevice()
    dev.startTestStream()
    time.sleep(10)
    dev.stopStream()
    dev.closeDevice()
    time.sleep(1)
    print("[*]TEST Over")
