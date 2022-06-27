import threading
import time


def get_packet_info(pkt):
	ret = dict()

	try:

		ret['channel'] = pkt['RadioTap'].ChannelFrequency
		ret['rssi'] = pkt['RadioTap'].dBm_AntSignal
		ret['ssid'] = pkt['Dot11Elt'].info.decode('utf-8')
		ret['fcs'] = pkt.fcs
	except Exception as e:
		print(e)
		pkt.show()

	return ret


class packetParser:
	def __init__(self, pkt_buffer, out_queue):
		self.pkt_buffer = pkt_buffer
		self.task_thread = None
		self.running = False
		self.out_queue = out_queue
		self.fcs_seen = set()

	def parser(self):
		while self.running:
			while not self.pkt_buffer.empty():
				pkt = self.pkt_buffer.get()
				if not self.out_queue.full():
					self.out_queue.put(get_packet_info(pkt))

			time.sleep(0.01)

		return 0

	def start(self):
		self.running = True
		self.task_thread = threading.Thread(target=self.parser)
		self.task_thread.start()

	def stop(self):
		self.running = False
		self.task_thread.join()
