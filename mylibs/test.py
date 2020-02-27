import numpy as np
import os
from PIL import Image


class RunningStatisticsVar:
    def __init__(self, ddof=0):
        self.mean = 0
        self.var = 0
        self.std = 0

        self._n = 0
        self._s = 0
        self._ddof = ddof

    def update(self, values):
        values = np.array(values, ndmin=1)
        n = len(values)

        self._n += n

        old_mean = self.mean
        delta = values - self.mean
        self.mean += (delta / self._n).sum()

        self._s += (delta * (values - self.mean)).sum()
        self.var = self._s / (self._n - self._ddof) if self._n > self._ddof else 0
        self.std = np.sqrt(self.var)

    def __str__(self):
        if self.std:
            return f"{self.name} (\u03BC \u00B1 \u03C3): {self.mean} \u00B1 {self.std}"
        else:
            return f"{self.name}: {self.mean}"


def calculate_mean_and_std(source_dir, pixelwise=True):
    source_fs = [os.path.join(source_dir, f) for f in os.listdir(source_dir)]

    if pixelwise:
        stats = {colour: RunningStatisticsVar() for colour in 'rgb'}
        for source in source_fs:
            _process_image_pixelwise(source, stats)
            print(f"\u03BC: {[stats[colour].mean for colour in 'rgb']}")
            print(f"\u03C3: {[stats[colour].std for colour in 'rgb']}")

    else:
        means, vars = zip(*(_process_image(source) for source in source_fs))
        means = np.array(means)
        vars = np.array(vars)
        print(f"\u03BC: {[[means[:i+1, c].mean() for c in range(3)] for i in range(len(means))]}")
        print(f"\u03C3: {[[np.sqrt(vars[:i+1, c].mean()) for c in range(3)] for i in range(len(vars))]}")


def _process_image(source_f):
    img = np.array(Image.open(source_f))
    return img.mean(axis=(0,1)), img.var(axis=(0,1))


def _process_image_pixelwise(source_f, stats):
    img = np.array(Image.open(source_f))
    for c, colour in enumerate('rgb'):
        stats[colour].update(img[:, :, c].flatten())


calculate_mean_and_std('/home/matej/Downloads/temp', True)
calculate_mean_and_std('/home/matej/Downloads/temp', False)
