import subprocess
import multiprocessing
import time
import sys
from protocol import ack
from protocol import parse_command
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


print("Starting ....")
# hunter.start()
server.start()
i = 0
while i < 600 and run['state']:
	while not hunter_queue.empty():
		msg = hunter_queue.get()

		server_parent.send(msg)

	if server_parent.poll(0.2):
		msg = server_parent.recv()
		pkt = json.loads(msg.decode('utf-8'))
		command = parse_command(pkt)

		if command:
			if command['command'] == 'START':
				print("GOT COMMAND 'START")

				if command['args'].get('interface_name') is None:
					print("Can't start an interface without an interface name!")
				else:
					print(command)
					interface_name = command['args'].get('interface_name')
					command['settings']['targets'] = targets # Temporarily hardcode targets
					parent_pipe, child_pipe = multiprocessing.Pipe()
					interface_kwargs = {
						'interface': interface_name,
						'settings': command['settings'],
						'hunter_pipe': hunter_queue,
						'msg_pipe': child_pipe
					}

					interfaces[interface_name] = {
						'process': multiprocessing.Process(target=hunter.serve, kwargs=interface_kwargs),
						'parent_pipe': parent_pipe
					}
					interfaces[interface_name]['process'].start()
			elif command['command'] == 'STOP':
				print("GOT COMMAND 'STOP'")
				if command['args'].get('interface_name') is None:
					print("Can't stop an interface without an interface name!")
				else:
					interface_name = command['args'].get('interface_name')
					process = interfaces[interface_name]['process']
					process.terminate()
					process.join()
			elif command['command'] == 'GET_SETTINGS':
				print("GOT COMMAND 'GET_SETTINGS'")
				if command['args'].get('interface_name') is None:
					print("Can't get settings without an interface name!")
				else:
					interface_name = command['args'].get('interface_name')
					interface_pipe = interfaces[interface_name]['parent_pipe']

					query = {
						'type': 'REQUEST',
						'REQUEST': 'GET_SETTINGS',
						'BODY': ''
					}

					interface_pipe.send(query)

					if interface_pipe.poll(0.3):
						response = interface_pipe.recv()
						print("Interface {} has settings {}".format(interface_name, response))
						# TODO:
						# We should actually ship this to the phone at some point
					else:
						print("Interface {} failed to respond to GET_SETTINGS".format(interface_name))
			elif command['command'] == 'UPDATE_SETTINGS':
				print("GOT COMMAND 'UPDATE_SETTINGS'")
				if command['args'].get('interface_name') is None:
					print("Can't get settings without an interface name!")
				else:
					interface_name = command['args'].get('interface_name')
					interface_pipe = interfaces[interface_name]['parent_pipe']

					new_settings = command.get('settings')

					if new_settings:
						print("UPDATE_SETTINGS got settings {}".format(new_settings))
						query = {
							'type': 'REQUEST',
							'REQUEST': 'UPDATE_SETTINGS',
							'BODY': new_settings
						}
						interface_pipe.send(query)

						if interface_pipe.poll(0.3):
							response = interface_pipe.recv()
							print("Interface {} sent {} in response to 'UPDATE_SETTINGS'".format(interface_name, response))
							# TODO:
							# Send response somewhere
					else:
						pass
						# TODO:
						# Send message somewhere
			elif command['command'] == 'GET_DOT11_INTERFACES':
				print("Got command 'GET_DOT11_INTERFACES'")
				iw_dev = subprocess.Popen(['iw', 'dev'], stdout=PIPE)
				awk = subprocess.check_output(['awk', '$1=="Interface"{print $2}'], stdin=iw_dev.stdout)
				ret = iw_dev.wait()

				if ret == 0:
					dot11_interfaces = [b.decode('utf-8') for b in awk.split(b'\n') if b]

					print("We have  the following interfaces available {}".format(dot11_interfaces))
					# TODO:
					# Send this somewhere

		print("[server parent]ACK")
		server_parent.send(ack(pkt))
	time.sleep(0.6)
	i += 1

print("AFTER MAIN LOOP")
for name in interfaces:
	proc = interfaces[name]['process']
	print("Stopping interface {}".format(name))
	proc.terminate()
	print("Waiting for interface {} to stop".format(name))
	proc.join()


server.terminate()
server.join()








