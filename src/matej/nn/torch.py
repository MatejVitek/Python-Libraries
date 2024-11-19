import torch
from torch import nn
import torchvision.transforms as tf


# We subclass Sequential instead of Module to get some of the functionality (e.g. .cuda()) for free
class Parallel(nn.Sequential):
	""" The counterpart to :class:`~torch.nn.Sequential` that returns a tuple of the outputs of the modules. """

	def forward(self, x):
		return tuple(module(x) for module in self)


class NoneTransform:
	""" Dummy transform that does nothing. """
	def __call__(self, x):
		return x
