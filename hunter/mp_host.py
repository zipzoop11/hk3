from .interfaces.dot11 import dot11intf
import queue
import time
import signal
import json
import threading
import subprocess

buf = queue.Queue(maxsize=10)
out_queue = queue.Queue(maxsize=10)

run = dict()
run['state'] = True


def SIGTERM_handler(*args):
	print("[SIGTERM_handler][{}]Caught SIGTERM".format(run['name']))
	run['state'] = False


def get_status(host_pipe):
	interface = run['interface']
	temp = subprocess.check_output(['vcgencmd', 'measure_temp'])
	temp = temp.decode('utf-8').strip().split('=')[-1]
	status_message = {
						'TYPE': 'STATUS',
						'BODY': {
							'pps': (interface.pkt_counter/10),
							'hps': (interface.hit_counter/10),
							'temp': temp[0:-2],
							'iface': interface.iface_name
						}
					}

	host_pipe.put(status_message)
	interface.pkt_counter = 0
	if interface.hit_counter > 0:
		interface.hit_counter = 0

	run['status_thread'] = threading.Timer(10.0, get_status, args=[host_pipe])
	run['status_thread'].start()


def serve(*args, **kwargs):
	signal.signal(signal.SIGTERM, SIGTERM_handler)

	pipe_to_host = kwargs['hunter_pipe']
	msg_pipe = kwargs['msg_pipe']
	run['name'] = kwargs['interface']
	print('[mp_host][{}]Got settings {}'.format(run['name'], kwargs['settings']))
	interface = dot11intf(kwargs['interface'], buf, **kwargs['settings'])
	stored_settings = kwargs['settings']
	name = kwargs['interface']
	interface.start()
	run['status_thread'] = threading.Timer(10.0, get_status, args=[pipe_to_host])
	run['status_thread'].start()
	run['interface'] = interface

	while run['state']:
		if not buf.empty():
			pipe_to_host.put(buf.get())
		if msg_pipe.poll(0.2):
			msg = msg_pipe.recv()
			request = msg['REQUEST']
			args = msg['ARGS']
			settings = msg['SETTINGS']

			if request == 'GET_SETTINGS':
				msg_pipe.send(interface.settings)
			elif request == 'UPDATE_SETTINGS':
				old_settings = interface.settings
				requested_settings = settings
				new_settings = dict()

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
				run['interface'] = interface
				stored_settings = new_settings

				msg_pipe.send(interface.settings)
				NEW_SETTINGS = {"TYPE": "SYSTEM_MESSAGE",
							  "REQUEST": {"ACTION": "NEW_SETTINGS", "ARGS": {'interface_name': name}, "SETTINGS": interface.settings}}

				NEW_SETTINGS_BYTES = json.dumps(NEW_SETTINGS).encode('utf-8')
				msg_pipe.send(NEW_SETTINGS_BYTES)

			elif request == 'GO_PASSIVE':
				if not interface.passive:
					print("Got go passive")
					interface.stop()
					interface.passive = True
			elif request == 'GO_ACTIVE':
				if interface.passive:
					print("Got go active")
					interface = dot11intf(kwargs['interface'], buf, **stored_settings)
					interface.start()
					interface.passive = False
			else:
				msg_pipe.send('BAD_COMMAND')

		time.sleep(0.2)

	interface.stop()
	run['status_thread'].cancel()





