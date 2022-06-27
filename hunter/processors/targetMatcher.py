import queue
import threading
import stat
import os
import socket
from scapy.all import raw
import json





def get_mac(mac_bytes):
	i = []
	for b in mac_bytes:
		i.append(f'{b:X}')
	return ':'.join(i)


def get_packet_info(pkt):
	ret = dict()

	try:

		ret['channel'] = pkt['RadioTap'].ChannelFrequency
		ret['rssi'] = pkt['RadioTap'].dBm_AntSignal
		ret['ssid'] = pkt['Dot11Elt'].info.decode('utf-8')
	except Exception as e:
		print(e)
		pkt.show()

	return ret


class targetMatcher:

	def __init__(self, pktbuffer, target_list, local_socket=None, local_socket_path=None):
		self.pktbuffer = pktbuffer

		self.running = False
		self.reconnect_socket = False

		if not local_socket:
			raise FileNotFoundError("Missing socket!")

		if not local_socket_path:
			raise ValueError("Missing local socket path!")

		if not isinstance(local_socket, socket.socket):
			raise AttributeError("local_socket is not of type socket!")

		self.local_socket = local_socket
		self.local_socket_path = local_socket_path
		self.target_list, self.target_strings = self.load_targets(target_list)

	def load_targets(self, targets):
		if not isinstance(targets, list):
			raise TypeError("Targets has to be list!")

		target_list = set()
		for t in targets:
			mac_address = t.upper()
			addr = b''
			for b in mac_address.split(':'):
				addr += bytes.fromhex(b)

			target_list.add(addr)
		return target_list, targets

	def matcher(self):
		if threading.current_thread() is threading.main_thread():
			try:
				raise ValueError("Calling matcher directly is not supported. Use .start")
			except ValueError as e:
				print("MATCHER: " + str(e))
				return 1

		while self.running:

			if self.reconnect_socket:
				try:
					self.local_socket.connect(self.local_socket_path)
					self.reconnect_socket = False
				except OSError:
					self.reconnect_socket = True

			try:
				pkt = self.pktbuffer.get(timeout=5)
			except queue.Empty as e:
				print("Queue empty")
				continue

			pkt_bytes = raw(pkt)
			mac_bytes = pkt_bytes[42:48]
			candidate = set()
			candidate.add(mac_bytes)

			intersect = self.target_list & candidate

			if intersect:
				info = get_packet_info(pkt)
				info['mac'] = get_mac(mac_bytes)
				info_bytes = (json.dumps(info)).encode('utf-8')
				try:
					self.local_socket.send(info_bytes)
				except OSError as e:
					if e.errno == 107:
						self.reconnect_socket = True
		return 0

	def start(self):
		if not self.running:
			self.running = True
			self.filterThrd = threading.Thread(target=self.matcher)
			self.filterThrd.start()

		else:
			print("Can't start twice!")

	def stop(self):
		if not self.running:
			print("No filter to stop!")
		else:
			self.running = False
			self.filterThrd.join()
