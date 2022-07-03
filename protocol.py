import json


wifi_channels = [1, 6, 11, 14, 2, 7, 3, 8, 4, 12, 9, 5, 10, 13, 36, 38, 40, 42, 44, 46, 52, 56, 58, 60, 100,
						 104, 108, 112, 116, 120, 124, 128, 132, 136, 140, 149, 153, 157, 161, 165]


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


def ack(pkt):
	response = {
		'type': 'ACK',
		'ack': pkt['seq']
	}
	response_bytes = json.dumps(response).encode('utf-8')

	return response_bytes

# {'COMMAND': 'START', 'ARGS':{'interface_name': 'wlan1'}}


def parse_command(pkt):
	if pkt['type'] == 'CONTROL':
		return {
			'command': pkt['payload']['COMMAND'],
			'args': pkt['payload'].get('ARGS'),
			'settings': load_settings(pkt['payload'].get('SETTINGS'))
		}
	else:
		return False

