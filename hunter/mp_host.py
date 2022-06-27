from .interfaces.dot11 import dot11intf
import queue
import time
import signal
import json

buf = queue.Queue(maxsize=10)
out_queue = queue.Queue(maxsize=10)

run = dict()
run['state'] = True


def SIGTERM_handler(*args):
	print("[SIGTERM_handler][{}]Caught SIGTERM".format(run['name']))
	run['state'] = False


def serve(*args, **kwargs):
	signal.signal(signal.SIGTERM, SIGTERM_handler)

	pipe_to_host = kwargs['hunter_pipe']
	msg_pipe = kwargs['msg_pipe']
	run['name'] = kwargs['interface']
	print('[mp_host][{}]Got settings {}'.format(run['name'], kwargs['settings']))
	interface = dot11intf(kwargs['interface'], buf, **kwargs['settings'])

	interface.start()

	while run['state']:
		if not buf.empty():
			buf_bytes = json.dumps(buf.get()).encode('utf-8')
			pipe_to_host.put(buf_bytes)
		if msg_pipe.poll(0.2):
			msg = msg_pipe.recv()
			if msg['type'] == 'REQUEST':
				if msg['REQUEST'] == 'GET_SETTINGS':
					response = {
						'type': 'RESPONSE',
						'RESPONSE': interface.settings
					}
					msg_pipe.send(response)
				elif msg['REQUEST'] == 'UPDATE_SETTINGS':
					old_settings = interface.settings
					requested_settings = msg['BODY']
					new_settings = dict()
					try:
						for key in old_settings:
							if key in requested_settings:
								print("UPDATE_SETTINGS updating settings: {} with value {}".format(key, requested_settings[key]))
								new_settings[key] = requested_settings[key]
							else:
								print("UPDATE_SETTINGS keeping old value {} for setting {}".format(old_settings[key], key))
								new_settings[key] = old_settings[key]

						print("[mp_host][{0}] Stopping interface {0} in response to 'UPDATE_SETTINGS'".format(run['name']))
						interface.stop()
						print("[mp_host][{}]Starting new interface in response to 'UPDATE_SETTINGS'".format(run['name']))
						interface = dot11intf(kwargs['interface'], buf, **new_settings)
						interface.start()

						response = {
							'type': 'RESPONSE',
							'RESPONSE': new_settings
						}
					except TypeError:
						response = {
							'type': 'RESPONSE',
							'RESPONSE': 'BAD_COMMAND'
						}

					msg_pipe.send(response)

				else:
					response = {
						'type': 'RESPONSE',
						'RESPONSE': 'BAD_COMMAND'
					}
					msg_pipe.send(response)

		time.sleep(0.2)

	interface.stop()




