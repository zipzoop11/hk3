import json
import socket


class rfcommConnection:

	def __init__(self, responder_socket):
		self.socket = responder_socket
		self.acknowledgements = set()

	def recv(self, pkt_bytes):

		pkt = json.loads(pkt_bytes.decode('utf-8'))

		if pkt['type'] == 'SYN':
			self.acknowledgements.clear()
			self.ack(pkt)
			return pkt

		if pkt['seq'] not in self.acknowledgements:
			self.ack(pkt)
			self.acknowledgements.add(pkt['seq'])

			if len(self.acknowledgements) > 1000:
				self.acknowledgements.clear()

			return pkt
		else:
			return None

	def ack(self, pkt):
		print("ACKing {}".format(pkt))
		ACK = {'type': 'ACK', 'ack': pkt['seq']}


		pkt_bytes = json.dumps(ACK).encode('utf-8')
		print("Sending: {}".format(pkt_bytes))
		try:
			self.socket.send(pkt_bytes)
			return True
		except OSError:
			print("Failed to send!")
			return False

