import time
import threading
import os
import serial
import json
from serial.serialutil import SerialException


class bt_server:
    def __init__(self,  pipe_to_host=None, rfcomm_dev=None):
        self.pipe = pipe_to_host
        self.rfcomm_dev = rfcomm_dev
        self.rfcomm_socket = None

        self.rx = None
        self.tx = None

        self.run = False
        self.connected = False
        self.sent = 0
        self.received = 0

    def tx_thread(self):
        while self.connected:
            time.sleep(0.1)
            if self.pipe.poll(5):
                pkt = self.pipe.recv()
            else:
                pkt = None

            if pkt:
                pkt_bytes = json.dumps(pkt).encode('utf-8')
                if pkt_bytes[-1] != b'\n':
                    pkt_bytes += b'\n'
                try:
                    self.rfcomm_socket.write(pkt_bytes)
                    self.sent += 1
                except OSError:
                    self.connected = False

    def rx_thread(self):
        while self.connected:
            time.sleep(0.1)
            try:
                pkt = self.rfcomm_socket.readline()
            except SerialException as e:
                print("[bt_sever][SerialException]self.rfcomm_socket.readline exception: {}".format(e))
                self.rfcomm_socket.close()
                self.connected = False
                pkt = None
            except TypeError as e:
                print(print("[bt_sever][TypeError]self.rfcomm_socket.readline exception: {}".format(e)))
                self.rfcomm_socket.close()
                self.connected = False
                pkt = None

            if pkt:
                print("RX: Got pkt: {}".format(pkt.decode('utf-8')))
                self.received += 1

                msg = pkt[2:]
                self.pipe.send(msg)

    def connect(self):
        if os.path.exists(self.rfcomm_dev):
            try:
                self.rfcomm_socket = serial.Serial(self.rfcomm_dev, 9600, timeout=10)
            except serial.SerialException:
                return False

            self.connected = True
            print("Connected!")
            return True
        else:
            return False

    def start(self):
        self.received = 0
        self.sent = 0

        self.tx = threading.Thread(target=self.tx_thread)
        self.rx = threading.Thread(target=self.rx_thread)
        self.tx.start()
        self.rx.start()

    def stop(self):
        print("Caught stop")
        self.connected = False
        if self.rfcomm_socket:
            self.rfcomm_socket.close()





