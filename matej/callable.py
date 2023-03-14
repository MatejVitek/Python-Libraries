import functools as ft
import sys
import types


def compose(*functions):
	"""
	Compose arbitrary number of functions into one. I.e. `compose(f, g, h)(x, y) == f(g(h(x, y)))`.

	All functions, aside from the last one (`h` in the above example), must take exactly one argument.
	"""

	return ft.reduce(lambda f, g: lambda *args, **kwargs: f(g(*args, **kwargs)), functions)


# Call as make_module_callable(__name__, function_to_call) at the end of the module definition
def make_module_callable(module_name, f):
	class _CallableModule(types.ModuleType):
		def __call__(self, *args, **kw):
			return f(*args, **kw)
	sys.modules[module_name].__class__ = _CallableModule