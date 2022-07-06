from .bt_server import bt_server
import signal
import time
import json

run = dict()
run['state'] = True

def SIGTERM_handler(*args):
	run['state'] = False

def serve(*args, **kwargs):
	signal.signal(signal.SIGTERM, SIGTERM_handler)
	pipe_to_host = kwargs['server_pipe']
	rfcomm_device = kwargs['rfcomm_device']

	server = bt_server(pipe_to_host=pipe_to_host, rfcomm_dev=rfcomm_device)
	passive = True
	while run['state']:
		if server.connect():
			server.start()

			while server.connected and run['state']:
				passive = False
				time.sleep(5)
				print("RX: {0} ::: TX {1}".format(server.received, server.sent))
			if not passive:
				print("Sending GO_PASSIVE")
				GO_PASSIVE = {"TYPE": "SYSTEM_MESSAGE",
							  "REQUEST": {"ACTION": "GO_PASSIVE", "ARGS": {}, "SETTINGS": {}}}

				GO_PASSIVE_BYTES = json.dumps(GO_PASSIVE).encode('utf-8')
				pipe_to_host.send(GO_PASSIVE_BYTES)
				passive = True
			print("Server disconnected, will retry in 10 seconds...")
			time.sleep(10)

		else:
			print("Failed to connect. Retrying in 10 seconds...")
			time.sleep(10)

	server.stop()


