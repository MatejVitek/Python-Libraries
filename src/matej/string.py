import re
import string


ALPHABET_LOWER = 'abcčćdđefghijklmnopqrsštuvwxyzž'
ALPHABET_UPPER = ALPHABET_LOWER.upper()
SLOVENE_LOWER = 'abcčdefghijklmnoprsštuvzž'
SLOVENE_UPPER = SLOVENE_LOWER.upper()


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


def alphasort(l, alphabet=string.ascii_lowercase, *args, whitespace=-2, digits=-1, punctuation=1, **kw):
	"""
	Sort a list of strings alphabetically using a custom alphabet.

	Parameters
	----------
	l : Sequence[str]
		Strings to sort.
	alphabet : str, default=string.ascii_lowercase
		Alphabet to use for sorting.
	whitespace, digits, punctuation : int, default=-2, -1, 1
		Relative position of whitespace, digits, and punctuation in the alphabet.
		Negative values will be prepended to the alphabet, positive values appended.
		If 0, the corresponding entry will not be included in the alphabet.
	*args, **kw : Any
		Other parameters to pass to :func:`sorted`.

	Returns
	-------
	List[str]
		Sorted list of strings.
	"""
	prefixes = sorted((i, extra) for i, extra in ((digits, string.digits), (punctuation, string.punctuation), (whitespace, string.whitespace)) if i < 0)
	suffixes = sorted((i, extra) for i, extra in ((digits, string.digits), (punctuation, string.punctuation), (whitespace, string.whitespace)) if i > 0)
	alphabet = ''.join(extra for _, extra in prefixes) + alphabet + ''.join(extra for _, extra in suffixes)
	alphabet = {c: i for i, c in enumerate(alphabet)}
	return sorted(l, *args, key=lambda s: tuple(alphabet[c] if c in alphabet else len(alphabet) + ord(c) for c in s.lower()), **kw)


def print_conditional(s, verbosity_level, min_level=1):
	if verbosity_level >= min_level:
		print(s)


if __name__ == '__main__':
	print(alphasort(['človek', 'cekin', '12 dežnikov', 'človeka', 'človek-pajek', 'človek beseda', 'žaba'], SLOVENE_LOWER))