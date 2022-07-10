def load_targets(targets):
	if not isinstance(targets, list):
		raise TypeError("Targets has to be list!")

	target_set = set()
	for t in targets:
		mac_address = t[0]
		addr = b''
		for b in mac_address.split(':'):
			addr += bytes.fromhex(b)

		target_set.add(addr)
	return target_set, targets
