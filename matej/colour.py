import numpy as np

from .collections import ensure_iterable


# Accepts RGB/greyscale colours only
def text_colour(background_colour):
	# We process the colour as 0-1 floats but return 0-255 ints if the colour was passed in as such
	colour_type = numeric_type(background_colour)
	multiplier = 255 if colour_type is np.uint8 else 1
	background_colour = np.array(ensure_iterable(background_colour)[:3], dtype=np.float32) / multiplier

	# Greyscale (L/LA)
	if len(background_colour) < 3:
		return multiplier * (1 if background_colour[0] < .5 else 0)

	# RGB
	return multiplier * np.array([1, 1, 1] if brightness(background_colour) < .5 else [0, 0, 0], dtype=colour_type)


def brightness(rgb):
	# https://www.nbdtech.com/Blog/archive/2008/04/27/Calculating-the-Perceived-Brightness-of-a-Color.aspx
	return np.sqrt(np.sum(np.array([.241, .691, .068]) * np.array(rgb[:3]) ** 2))


def numeric_type(colour):
	colour = ensure_iterable(colour)
	if all(0 <= c <= 1 for c in colour) and any(int(c) != c for c in colour):
		return np.float32
	return np.uint8