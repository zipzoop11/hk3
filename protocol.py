import json


wifi_channels = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 7, 8, 9, 11, 12, 16, 32, 34, 36, 38, 40, 42, 44, 46,
				 48, 50, 52, 54, 56, 58, 60, 62, 64, 68, 96, 100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120, 122,
				 124, 126, 128, 132, 134, 136, 138, 140, 142, 144, 149, 151, 153, 155, 157, 159, 161, 163, 165, 167,
				 169, 171, 173, 175, 177, 182, 183, 184, 187, 188, 189, 192, 196]


def load_settings(settings):
	print("[load_settings]Loading settings {}".format(settings))
	default_hunter_settings = {
		'TARGETS': [],
		'CHANNELS': wifi_channels,
		'SUBTYPES': [4, 8]

	}

	if settings is None:
		return default_hunter_settings

	loaded_settings = default_hunter_settings
	for key in settings:
		if key in default_hunter_settings:
			loaded_settings[key] = settings[key]

	print("[load_settings]Loaded settings {}".format(loaded_settings))
	return loaded_settings


def execute_command(request, interface):
	request_action = request.get('ACTION')
	request_args = request.get('ARGS')
	request_settings = request.get('SETTINGS')
	response = ''

	print(f'[execute_command]Got interface: {interface}')
	print(f'[execute_command]Got ACTION: {request_action}')

	comms_pipe = interface['parent_pipe']

	query = {
		'REQUEST': request_action,
		'ARGS': request_args,
		'SETTINGS': request_settings
	}

	comms_pipe.send(query)

	if comms_pipe.poll(1):
		response = comms_pipe.recv()

	return response



