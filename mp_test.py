import subprocess
import multiprocessing
import time
import sys
from protocol import execute_command
from protocol import load_settings
import hunter
import bt_server
import signal
import json

PIPE = subprocess.PIPE
run = dict()
run['state'] = True
run['servers'] = []


def SIGINT_HANDLER(*args):
	run['state'] = False


signal.signal(signal.SIGINT, SIGINT_HANDLER)

interface = sys.argv[1]
rfcomm_device = sys.argv[2]

targets = ['30:23:03:DC:16:E1', '30:23:03:DC:16:E3', '30:23:03:DC:16:E2']

hunter_queue = multiprocessing.Queue()
server_parent, server_child = multiprocessing.Pipe()

interfaces = dict()

bt_server_args = {
	'server_pipe': server_child,
	'rfcomm_device': rfcomm_device,
}

server = multiprocessing.Process(target=bt_server.serve, kwargs=bt_server_args)
seen_requests = set()

print("Starting ....")
# hunter.start()
server.start()

while run['state']:
	while not hunter_queue.empty():
		msg = hunter_queue.get()
		server_parent.send(msg)

	if server_parent.poll(0.2):
		msg = server_parent.recv()
		pkt = json.loads(msg.decode('utf-8'))
		COMMAND = False
		request_id = pkt.get('SEQ')

		response = {
			'TYPE': 'RESPONSE',
			'ACK': request_id
		}

		if pkt['TYPE'] == 'SYN':
			print("GOT A SYN")
			COMMAND = False
			seen_requests.clear()

		if pkt['TYPE'] == 'REQUEST':
			print("GOT A REQUEST")
			command = pkt.get('REQUEST')
			COMMAND = True
		else:
			command = {'ACTION': None, 'ARGS': {}}

		if request_id in seen_requests:
			print(f"We have already seen the request {pkt} before. Ignoring...")
			COMMAND = False

		if COMMAND:
			try:
				interface_name = command['ARGS'].get('interface_name')
			except KeyError:
				interface_name = None

			ACTION = command.get('ACTION')

			if ACTION == 'START':
				print("GOT COMMAND 'START")

				if interface_name is None:
					print("Can't start an interface without an interface name!")
				else:
					settings = load_settings(command.get('SETTINGS'))

					settings['TARGETS'] = targets # Temporarily hardcode targets
					parent_pipe, child_pipe = multiprocessing.Pipe()
					interface_kwargs = {
						'interface': interface_name,
						'settings': settings,
						'hunter_pipe': hunter_queue,
						'msg_pipe': child_pipe
					}

					if interfaces.get(interface_name):
						settings = interfaces[interface_name]['settings']
					else:
						interfaces[interface_name] = {
							'process': multiprocessing.Process(target=hunter.serve, kwargs=interface_kwargs),
							'parent_pipe': parent_pipe,
							'settings': settings
						}
						interfaces[interface_name]['process'].start()

					response['BODY'] = settings
			elif ACTION == 'STOP':

				if interfaces.get(interface_name):
					process = interfaces[interface_name]['process']
					process.terminate()
					process.join()

					response['BODY'] = interface_name
				else:
					response['BODY'] = f'{interface_name} NOT STARTED'
			elif ACTION == 'GET_DOT11_INTERFACES':
				iw_dev = subprocess.Popen(['iw', 'dev'], stdout=PIPE)
				awk = subprocess.check_output(['awk', '$1=="Interface"{print $2}'], stdin=iw_dev.stdout)
				ret = iw_dev.wait()
				if ret == 0:
					BODY = dict()
					for i in [b.decode('utf-8') for b in awk.split(b'\n') if b]:
						if i in interfaces:
							BODY[i] = {
								'STATE': 'RUNNING',
								'SETTINGS': interfaces[i]['settings']
							}
						else:
							BODY[i] = {
								'STATE': 'NOT_RUNNING',
								'SETTINGS': {}
							}
					response['BODY'] = BODY
				else:
					response['BODY'] = 'GET_DOT11_INTERFACES FAILED'
			else:
				if interfaces.get(interface_name):
					response['BODY'] = execute_command(command, interfaces[interface_name])
				else:
					response['BODY'] = {
						'ERROR': 'NOT_STARTED',
						'INTERFACE': interface_name
					}

		server_parent.send(response)
		seen_requests.add(request_id)
	time.sleep(0.6)


print("AFTER MAIN LOOP")
try:
	for name in interfaces:
		proc = interfaces[name]['process']
		print("Stopping interface {}".format(name))
		proc.terminate()
		print("Waiting for interface {} to stop".format(name))
		proc.join()
except TypeError:
	pass


server.terminate()
server.join()








