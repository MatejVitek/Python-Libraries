import ctypes
import sys


def query_yes_no(question, default=None):
	"""
	Ask a yes/no question and return the user's answer.

	Parameters
	----------
	question : str
		The question to ask the user. The suffix [y/n] is appended automatically.
	default : bool or None, default=None
		The default answer if the user just presses Enter.
		If `None`, the user must provide an explicit answer.
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


def run_as_admin(ask=False, default=True, query=None):
	"""
	Run the current script with administrator privileges.

	If the script is already running with administrator privileges, the function does nothing.

	Parameters
	----------
	ask : bool, default=False
		Whether to ask the user for confirmation before relaunching the script with administrator privileges.
		If `True`, the user can choose to continue execution normally, or to relaunch the script with administrator privileges.
	query : str, optional
		The question to ask the user if `ask=True`. By default, a generic question is asked.
	default : bool, default=True
		The default choice if the user is asked for confirmation (only if `ask=True`).
		See :func:`query_yes_no` for more information.
	"""
	if ctypes.windll.shell32.IsUserAnAdmin():
		return
	if ask and query is None:
		query = "You are running the script without administrator privileges. The script's functionality will be limited. Would you instead like to relaunch the script with administrator privileges?"
	if not ask or query_yes_no(query, default=default):
		ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
		sys.exit()
