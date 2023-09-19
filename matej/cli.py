def query_yes_no(question, default=None):
	"""
	Ask a yes/no question and return the user's answer.
	"""

	valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
	if default not in (None, True, False):
		default = valid[default]

	if default is None:
		prompt = " [y/n] "
	elif default:
		prompt = " [Y/n] "
	else:
		prompt = " [y/N] "
	prompt = question + prompt

	while True:
		print(prompt, end="")
		choice = input().lower().strip()
		if default is not None and choice == "":
			return default
		elif choice in valid:
			return valid[choice]
		else:
			print("Please respond with 'yes' or 'no'.")
