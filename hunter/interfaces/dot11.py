import os
import time
import threading
import subprocess
from scapy.all import AsyncSniffer
from scapy.layers.dot11 import Dot11, Dot11FCS
from scapy.error import Scapy_Exception
from scapy.all import raw
from ..utils import load_targets

PIPE = subprocess.PIPE

class dot11intf:
	def __init__(self, iface_name, pkt_buffer, **kwargs):
		self.iface_name = iface_name
		self.NULL = open(os.devnull, 'w')
		self.pkt_buffer = pkt_buffer
		self.sniffer = AsyncSniffer(prn=self.packet_handler, iface=iface_name, store=False)
		self.settings = kwargs
		self.passive = False

		if kwargs.get('TARGETS'):
			self.target_set, self.target_list = load_targets(kwargs['TARGETS'])
			self.target_list = kwargs['TARGETS']
		else:
			self.target_set = set()
			self.target_list = []

		self.running = False
		self.hopper = None
		self.i = 0

		self.channels = kwargs['CHANNELS']
		self.subtype_filter = set(kwargs['SUBTYPES'])

	def set_interface_mode(self, mode):

		exit_code = True

		# down interface
		cmd = ['ip', 'link', 'set', self.iface_name, 'down']
		down = subprocess.Popen(cmd)
		down.wait()

		# set mode
		cmd = ['iw', 'dev', self.iface_name, 'set', 'type', mode]
		mode = subprocess.Popen(cmd)
		mode.wait()

		# up interface
		cmd = ['ip', 'link', 'set', self.iface_name, 'up']
		up = subprocess.Popen(cmd)
		up.wait()

		return not(exit_code and bool(down.returncode) and bool(mode.returncode) and bool(up.returncode))

	def set_channel(self, ch, dwell_time=0.5):

		if isinstance(ch, list):
			self.hopper = threading.Thread(target=self.channel_hopper, args=[dwell_time])
			self.hopper.start()

			return True
		else:
			cmd = ['iw', 'dev', self.iface_name, 'set', 'channel', str(ch)]
			channel_change = subprocess.Popen(cmd)
			channel_change.wait()

			return not channel_change.returncode

	def channel_hopper(self, dwell_time=0.5):
		channels = self.channels
		while self.running:
			for ch in channels:
				if not self.running:
					print("self.running is false!")
					break
				set_channel = subprocess.Popen(['iw', 'dev', self.iface_name, 'set', 'channel', str(ch)], stderr=PIPE, stdout=PIPE)
				set_channel.wait()

				if set_channel.returncode != 0:
					channels.remove(ch)
					print("Removed ch: %d" % ch)
				else:
					time.sleep(dwell_time)

		return 0

	def packet_handler(self, pkt):
		time.sleep(0.01)
		if not self.pkt_buffer.full():
			if pkt.subtype in self.subtype_filter and pkt.type == 0:
				addr_bytes = raw(pkt)[36:54]
				intersect = set([addr_bytes[i:i + 6] for i in range(0, len(addr_bytes), 6)]) & self.target_set

				if intersect:
					addrs = list({pkt['Dot11FCS'].addr2, pkt['Dot11FCS'].addr3})
					output_event = {
						'TYPE': 'HIT',
						'BODY': {
							'channel': pkt['RadioTap'].ChannelFrequency,
							'rssi': pkt['RadioTap'].dBm_AntSignal,
							'bssid': pkt['Dot11Elt'].info.decode('utf-8'),
							'mac': addrs,
							'fcs': pkt.fcs
						}
					}
					self.pkt_buffer.put(output_event)

	def start(self, dwell_time=0.5):
		if self.set_interface_mode('monitor'):
			self.sniffer.start()
			self.running = True
			self.set_channel(self.channels, dwell_time=dwell_time)
		else:
			print("Couldn't set monitor mode on interface {}".format(self.iface_name))

	def stop(self):
		self.running = False
		try:
			self.sniffer.stop()
			self.sniffer.join()
			self.hopper.join()
		except Scapy_Exception:
			pass
		self.set_interface_mode('managed')

