import re


def multi_replace(s, replacements, ignore_case=False):
	if ignore_case:
		replacements = dict((k.lower(), v) for (k, v) in replacements.items())
	rep = map(re.escape, sorted(replacements, key=len, reverse=True))
	pattern = re.compile('|'.join(rep), re.I if ignore_case else 0)
	return pattern.sub(lambda match: replacements[match.group(0)], s)
	

def alphanum(s, allow_underscore=False):
	return re.sub(r'[\W]+' if allow_underscore else r'[\W_]+', '', s)
	

def alpha(s):
	return re.sub(r'[^A-Za-z]+', '', s)


def print_conditional(s, verbosity_level, min_level=1):
	if verbosity_level >= min_level:
		print(s)

