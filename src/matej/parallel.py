import contextlib
try:
	import joblib
except ImportError as e:
	raise ImportError(
		"The parallel module requires the joblib library."
		"Please install it using `pip install joblib`."
	) from e


# https://stackoverflow.com/a/58936697/5769814 can get called on intermediate results,
# so it ends up occasionally going over 100%. So we use this solution instead.
@contextlib.contextmanager
def tqdm_joblib(tqdm_object):
	"""
	Context manager to patch joblib to report into tqdm progress bar given as argument.

	From: https://stackoverflow.com/a/61689175/5769814

	Examples
	--------
	.. code-block:: python

		with tqdm_joblib(tqdm(files)) as data:
			Parallel(n_jobs=-1)(
				delayed(process_file)(f)
				for f in data
			)
	"""

	def tqdm_print_progress(self):
		if self.n_completed_tasks > tqdm_object.n:
			n_completed = self.n_completed_tasks - tqdm_object.n
			tqdm_object.update(n=n_completed)

	original_print_progress = joblib.parallel.Parallel.print_progress
	joblib.parallel.Parallel.print_progress = tqdm_print_progress

	try:
		yield tqdm_object
	finally:
		joblib.parallel.Parallel.print_progress = original_print_progress
		tqdm_object.close()
