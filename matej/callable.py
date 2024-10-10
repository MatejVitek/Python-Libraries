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


def varargs(f):
	""" Decorator that lets a function with varargs also accept a single iterable argument. """
	from inspect import signature
	from matej.collections import is_iterable
	args = signature(f).parameters

	@ft.wraps(f)
	def wrapper(*args, **kwargs):
		if len(args) == 1 and is_iterable(args[0]):
			return f(*args[0], **kwargs)
		return f(*args, **kwargs)
	return wrapper


if __name__ == '__main__':
	@varargs
	def test(*arglist, kwarg=None):
		print(arglist, kwarg)

	test([1, 2, 3])
	test(1, 2, 3)

	@varargs
	def test2(arg, *arglist, kwarg=None):
		print(arg, arglist, kwarg)

	test2([1, 2, 3], [4, 5, 6])
	test2(1, 2, 3, 4, 5, 6)
	test2([1, 2, 3])
