from .bt_server import bt_server
import signal
import time

run = dict()
run['state'] = True

def SIGTERM_handler(*args):
	run['state'] = False

def serve(*args, **kwargs):
	signal.signal(signal.SIGTERM, SIGTERM_handler)
	pipe_to_host = kwargs['server_pipe']
	rfcomm_device = kwargs['rfcomm_device']

	server = bt_server(pipe_to_host=pipe_to_host, rfcomm_dev=rfcomm_device)

	while run['state']:
		if server.connect():
			server.start()

			while server.connected and run['state']:
				time.sleep(5)
				print("RX: {0} ::: TX {1}".format(server.received, server.sent))

			print("Server disconnected, will retry in 10 seconds...")
			time.sleep(10)

		else:
			print("Failed to connect. Retrying in 10 seconds...")
			time.sleep(10)

	server.stop()


