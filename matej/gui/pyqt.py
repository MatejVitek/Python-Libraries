from abc import ABCMeta, abstractmethod
from collections import defaultdict
from inspect import signature
import numpy as np
from pathlib import Path
import re

from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
try:
	from PyQt5.QtCore import pyqtWrapperType
except ImportError:
	from sip import wrappertype as pyqtWrapperType

from matej import Singleton
from matej.collections import lfilter
from matej.enum import LazyDirectEnum


def browse_file(parent=None, title=None, *, init=None, existing_only=False, multiple=False, ext_filters=None, init_filter=None, return_chosen_filter=False):
	"""
	Browse files on the filesystem.

	:param QWidget parent: Parent widget
	:param str title: Title of the opened dialog
	:param init: Initial directory to start in (if it doesn't exist or is a file, it will be resolved to the first existing parent directory)
	:type  init: str or pathlib.Path
	:param bool existing_only: Only search for existing files (don't allow new ones)
	:param bool multiple: Allow multiple files (only relevant in `existing_only=True` mode)
	:param ext_filters: List of extension filters. If multiple filters are passed as a single string, they must be separated using `;;`.
	                    For the specific syntax of the filters see the `QFileDialog` docs (e.g. https://doc.qt.io/qt-5/qfiledialog.html#getOpenFileName).
	:type  ext_filters: str or Iterable
	:param str init_filter: Initially selected filter
	:param bool return_chosen_filter: Whether to return a tuple of the selected file and filter, rather than just the selected file.

	:return: Selected file or None if dialog was cancelled. If `return_chosen_filter=True`, will also return selected extension filter.
	:rtype:  Path or tuple
	"""

	init = _get_first_existing_parent(init)
	if not isinstance(ext_filters, str):
		ext_filters = ';;'.join(ext_filters)

	if existing_only:
		browse = QFileDialog.getOpenFileNames if multiple else QFileDialog.getOpenFileName
	else:
		browse = QFileDialog.getSaveFileName

	f, chosen_filter = browse(parent, title, init, ext_filters, init_filter)
	if f:
		f = Path(f)

	if return_chosen_filter:
		return f, chosen_filter
	return f


def browse_dir(parent=None, title=None, *, init=None, show_files=False):
	"""
	Browse directories on the filesystem.

	:param QWidget parent: Parent widget
	:param str title: Title of the opened dialog
	:param init: Initial directory to start in (if it doesn't exist or is a file, it will be resolved to the first existing parent directory)
	:type  init: str or pathlib.Path
	:param bool show_files: Show files in the dialog as well

	:return: Selected directory or None if dialog was cancelled.
	:rtype:  Path
	"""

	init = _get_first_existing_parent(init)
	flags = QFileDialog.Options() if show_files else QFileDialog.ShowDirsOnly

	if (d := QFileDialog.getExistingDirectory(parent, title, init, flags)):
		d = Path(d)
	return d

def _get_first_existing_parent(f_or_dir):
	if not f_or_dir:
		return str(Path())
	d = Path(f_or_dir)
	while not d.is_dir():
		d = d.parent
	return str(d)


def set_label_number(label, x):
	label.setText(np.format_float_positional(x, precision=3, trim='-'))


def set_background_colour(widget, colour):
	p = widget.palette()
	p.setColor(widget.backgroundRole(), colour)
	widget.setPalette(p)
	widget.setAutoFillBackground(True)


def clear_layout(layout):
	if layout is None:
		return
	while layout.count():
		item = layout.takeAt(0)
		widget = item.widget()
		if widget is not None:
			widget.deleteLater()
		else:
			clear_layout(item.layout())


class AbstractWidgetMeta(pyqtWrapperType, ABCMeta):
	pass


# TODO: Make this handle child init properly (so first all _inits are called, then all _init_uis, ...) -- this might be too hard/hacky.
# First determine if it's a top-level widget. Call all methods if it is. Otherwise only call __init__, _init and _init_ui and mark that _connect_signals and _init_ui_values haven't been called yet.
# Then make _connect_signals and _init_ui_values call _connect_signals and _init_ui_values of all children that are GUIWidget instances if marked uncalled, and mark them as called.
# This will require any subclass that overrides those two methods and has children to call super()._connect_signals or super()._init_ui_values at the beginning or the end (depending on when they want the childrens' methods to be called).
# It will also require that all non-top-level GUIWidgets be explicitly initialised with a parent (rather than implicitly adding a parent via layout managers or similar).
class GUIWidget(QWidget, metaclass=AbstractWidgetMeta):
	"""
	Template class for GUI Widget initialisation.

	This class canonicalises the initialisation of GUI Widgets into 5 steps:

	- a call to `__init__` of the superclass (the superclass is `QWidget` by default);
	- `_init`, where you initialise the necessary fields and values for further methods;
	- `_init_ui`, where you lay out and initialise the UI widgets. This method must be implemented in subclasses.
	  This method will usually also contain initialisation of child GUIWidgets;
	- `_connect_signals`, where you connect the signals and slots, particulary those in different children. It's usually a good idea
	  to connect any pair of signal and slot in `_connect_signals` of their Lowest Common Parent `GUIWidget` in the widget hierarchy;
	- `_init_ui_values`, where you set the initial values in the UI widgets, particularly the ones that will emit signals
	  (such as selecting the correct radio button or setting the correct spinbox value) and thereby set up the correct initial state.
	  The values should be initialised in the highest parent `GUIWidget` that relies on the signal they emit.

	When creating a new instance of this class a simple call to this class' constructor will try to match the arguments of the call
	to each of the 5 methods above (for `_init`, `_connect_signals` and `_init_ui_values` only if they are defined in the subclass).
	Below is a detailed description of how this argument matching works, but for the most part you shouldn't have to worry about this
	if you define your methods and call this class' constructor in a reasonable way. The best way to achieve intuitive, predictable,
	and reliable behaviour is to pass all arguments into the constructor as keywords. Passing them as keywords also allows you to pass
	the same argument to multiple initialisation methods, as long as its name matches in all of them.

	The argument matching procedure uses the following order of methods: `_init`, `_init_ui`, `_connect_signals`, `_init_ui_values`, `super().__init__`.
	Note that this order is different to the order in which the methods are actually called, which is described in the bullet list above
	(the difference is that for argument matching the superclass' `__init__` method is considered last, while in the calling order it appears first).
	The argument matching procedure works as follows:

	- Determine *how many* positional `*args` go to each method in 5 stages:
	  - First, enough `*args` must be reserved for positional-only parameters of all methods in order. If there aren't enough `*args` for this, raise Error.
	  - Second, reserve enough `*args` for positional-or-keyword arguments that don't appear in the passed `**kwargs` and don't have default values.
		Again, if there aren't enough remaining `*args` for this, raise an Error.
		If any of them are after the first positional-or-keyword argument that *does* appear in the passed `**kwargs`, also raise an Error.
	  - Third, if there are still `*args` left over, reserve enough for positional-or-keyword arguments with default values
		up to the first one that appears in the passed `**kwargs`.
	  - Finally, if `*args` are still not exhausted, as many as remain will be passed to the first method with `*args` in its signature.
		Note that only methods whose positional-or-keyword arguments don't appear in the passed `**kwargs` will be considered.
		If no such method is found, raise an Error.
	- Note that these stages are only used to determine the *number* of arguments passed, not *which* arguments are passed.
	  Since we now know how many positional arguments should be passed to each method, simply iterate over the methods in order
	  and pass that many `*args` to it, removing the passed arguments from `*args` in the process.
	- Finally, determine the keyword arguments that should be passed to each method. If the method has `**kwargs` in its signature, simply pass
	  all passed keyword arguments to it and let the method sort them out. Otherwise all the passed `**kwargs` that appear in the method's
	  signature will be passed to the method. This way multiple methods can be passed the same keyword argument.

	Example usage:
	>>> class ExampleGUIWidget(QPushButton, GUIWidget):
	... 	def _init(self, a, /, b, c=10, *args, d, e=20, **kw):
	... 		print("_init", a, b, c, d, e, args, kw)
	...
	... 	def _init_ui(self, omega, kappa=True, *args, **kw):
	... 		print("_init_ui", omega, kappa, args, kw)
	...
	... 	def _connect_signals(self):
	... 		print("_connect_signals")
	...
	... 	def _init_ui_values(self, *, val1=80, val2, c=20):
	... 		print("_init_ui_values", val1, val2, c)
	...
	>>> ExampleGUIWidget(1, 2, 3, 4, 5, 7, 8, 9, c=6, d=10, e=40, val2=15, parent=None)  # parent will be passed to QPushButton.__init__
	_init 1 2 6 10 40 () {'val2': 15, parent: None}
	_init_ui 8 9 (3, 4, 5, 6, 7) {'c': 6, 'd': 10, 'e': 40, 'val2': 15, parent: None}
	_connect_signals
	_init_ui_values 80, 15, 6
	>>> ExampleGUIWidget(1, 2, 3, d=10, val2=15)  # This is the minimal call possible - any fewer arguments would raise an error
	_init 1 2 10 10 20 () {'val2': 15}
	_init_ui 3 True () {'d': 10, 'val2': 15}
	_connect_signals
	_init_ui_values 80 15 20
	"""

	def __init__(self, *args, **kw):
		methods, signatures = self.__inspect()

		# Determine HOW MANY arguments can go to each method, following the *varargs procedure from the docs
		stages = self.__reserve_varargs(signatures, kw)
		stopping_point = self.__get_stopping_point(stages, args)

		# Determine WHICH arguments go to each method, following this distribution
		args_for = self.__distribute_args(stages, stopping_point, args)
		kw_for = self.__distribute_kw(signatures, kw)

		# Call super().__init__. Its signature cannot be determined by inspect, so we need to remove unknown arguments iteratively
		kw_for['super'] = kw_for['super'].copy()
		while True:
			try:
				super().__init__(*args_for['super'], **kw_for['super'])
				break
			except TypeError as e:
				argname = re.search(r"'[a-zA-Z1-9_]*'", str(e))
				if not argname:
					raise
				del kw_for['super'][argname[0].strip("'")]

		# Actually call the other initialisation methods
		for name, method in methods.items():
			if name != 'super':
				method(self, *args_for[name], **kw_for[name])

	@classmethod
	def __inspect(cls):
		init_names = '_init', '_init_ui', '_connect_signals', '_init_ui_values'
		methods = {name: getattr(cls, name) for name in init_names if hasattr(cls, name)} | {'super': super().__init__}
		signatures = {name: signature(method).parameters.values() for name, method in methods.items()}
		# Remove the 'self' and 'cls' arguments from the signatures
		signatures = {name: lfilter(lambda param: param.name not in {'self', 'cls'}, sig) for name, sig in signatures.items()}
		return methods, signatures

	@staticmethod
	def __reserve_varargs(signatures, kw):
		stages = []
		pos_only = {name: lfilter(lambda param: param.kind == param.POSITIONAL_ONLY, sig) for name, sig in signatures.items()}
		pos_or_kw = {name: lfilter(lambda param: param.kind == param.POSITIONAL_OR_KEYWORD, sig) for name, sig in signatures.items()}
		has_varargs = {name: any(param.kind == param.VAR_POSITIONAL for param in sig) for name, sig in signatures.items()}

		# Determine the index of the first pos-or-kw argument that appears in kw
		first_kw = {}
		for name, sig in pos_or_kw.items():
			for i, param in enumerate(sig):
				if param.name in kw:
					first_kw[name] = i
					break
		pos_or_kw = {name: sig[:first_kw[name]] if name in first_kw else sig for name, sig in pos_or_kw.items()}

		# First, positional-only parameters.
		stages.append({name: len(sig) for name, sig in pos_only.items()})

		# Second, positional-or-keyword arguments without default values until the first one that appears in **kw.
		stages.append({name: len(lfilter(lambda param: param.default == param.empty, sig)) for name, sig in pos_or_kw.items()})

		# Third, positional-or-keyword parameters with default values until the first one that appears in **kw.
		stages.append({name: len(lfilter(lambda param: param.default != param.empty, sig)) for name, sig in pos_or_kw.items()})

		# Finally, varargs of the first method that has them and wasn't passed any pos-or-kw values in **kw
		stages.append(next((name for name, varargs in has_varargs.items() if varargs and name not in first_kw), None))

		return stages

	@staticmethod
	def __get_stopping_point(stages, args):
		n_passed = len(args)

		# Check that we have enough args to cover the first two stages
		total = sum(n_args for s in range(2) for n_args in stages[s].values())
		if total > n_passed :
			raise ValueError("Not enough arguments passed to fill positional parameters with no default value")

		# Check the third stage for a stopping point
		for s in range(2, 3):
			for name, n_args in stages[s].items():
				if total + n_args > n_passed:
					return s, name, n_passed - total
				total += n_args

		# If we still have leftover arguments check that a method has varargs
		if n_passed > total and stages[3] is None:
			raise ValueError("Left-over positional arguments")

		# Return the stopping point at stage 4 and the name of the first method with varargs
		return 3, stages[3], 0

	@staticmethod
	def __distribute_args(stages, stopping_point, args):
		result = defaultdict(list)
		names = list(enumerate(stages[0]))
		stop_stage, stop_name, stop_idx = stopping_point
		stop_name_idx = next(i for i, name in names if name == stop_name)

		args_idx = 0
		for i, name in names:
			s_stop = min(3, stop_stage + 1 if i < stop_name_idx else stop_stage)
			for s in range(s_stop):
				if name in stages[s]:
					start = args_idx
					args_idx += stages[s][name]
					result[name].extend(args[start:args_idx])
			if i == stop_name_idx:
				start = args_idx
				args_idx += stop_idx
				result[name].extend(args[start:args_idx])
		if stop_stage == 3:
			result[stop_name].extend(args[args_idx:])

		return result

	@staticmethod
	def __distribute_kw(signatures, kw):
		kw_for = defaultdict(dict)
		for name, sig in signatures.items():
			# If a method has **kw in its signature, we can just pass all keyword arguments and let the method sort it out
			if any(param.kind == param.VAR_KEYWORD for param in sig):
				kw_for[name] = kw
			# Otherwise only pass an intersection of the passed kw and the method's keyword arguments
			else:
				kw_for[name] = {param.name: kw[param.name] for param in sig if param.kind in {param.POSITIONAL_OR_KEYWORD, param.KEYWORD_ONLY} and param.name in kw}
		return kw_for

	@abstractmethod
	def _init_ui(self, *args, **kw):
		pass


class _AbstractSingletonWidgetMeta(AbstractWidgetMeta, Singleton):
	pass


class SingletonGUIWidget(GUIWidget, metaclass=_AbstractSingletonWidgetMeta):
	@abstractmethod
	def _init_ui(self, *args, **kw):
		# Keep this method abstract
		pass


class ImageButton(QPushButton):
	def __init__(self, image=None, *args, **kw):
		super().__init__(*args, **kw)
		self.pixmap = None  # The original pixmap
		self.movie = None  # The movie resized to the current size (QMovie doesn't have a scaled method, so we can't keep the original version)
		self._pixmap = None  # The current pixmap adjusted to the current size
		self._size = super().sizeHint()
		if image:
			self.setImage(image)

		sp = QSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
		sp.setHeightForWidth(True)
		self.setSizePolicy(sp)

	def setImage(self, image):
		if isinstance(image, (str, Path)):
			animated = Path(image).suffix.lower() == '.gif'
			image = str(image)
		else:
			animated = isinstance(image, QMovie)

		if animated:
			self.pixmap = None
			self.movie = image if isinstance(image, QMovie) else QMovie(image, parent=self)
			self.movie.jumpToFrame(0)
			self._size = self.movie.currentImage().size()
			self.movie.frameChanged.connect(self._set_pixmap_from_movie)
			self.movie.start()
		else:
			if self.movie:
				self.movie.frameChanged.disconnect(self._set_pixmap_from_movie)
				self.movie.stop()
				self.movie = None
			self.pixmap = QPixmap(image)
			self._size = self.pixmap.size()
			self._pixmap = self.pixmap
			self.update()
		self._resize_img()

	def _set_pixmap_from_movie(self):
		self._pixmap = self.movie.currentPixmap()
		self.update()

	def resizeEvent(self, e):
		super().resizeEvent(e)
		self._resize_img(e.size())

	def _resize_img(self, size=None):
		if size is None:
			size = self.size()
		if self.pixmap:
			self._pixmap = self.pixmap.scaled(size, Qt.KeepAspectRatio)
		elif self.movie:
			width = size.height() * self._size.width() // self._size.height()
			if width <= size.width():
				size = QSize(width, size.height())
			else:
				height = size.width() * self._size.height() // self._size.width()
				size = QSize(size.width(), height)
			self.movie.setScaledSize(size)

	def paintEvent(self, e):
		super().paintEvent(e)
		if self._pixmap:
			w, h = self._pixmap.size().width(), self._pixmap.size().height()
			x = (self.size().width() - w) // 2
			y = (self.size().height() - h) // 2
			QPainter(self).drawPixmap(x, y, w, h, self._pixmap)

	def sizeHint(self):
		return self._size

	def heightForWidth(self, w):
		return self._size.height() * w // self._size.width()


class ImageRadioButton(ImageButton):
	def __init__(self, *args, **kw):
		super().__init__(*args, **kw)
		self.setCheckable(True)
		self.setAutoExclusive(True)


class ColourPicker(GUIWidget):
	def _init_ui(self, *args, **kw):
		hbox = QHBoxLayout(self)
		self.setSizePolicy(QSizePolicy())

		self.button = ColourPickerButton(*args, **kw)
		hbox.addWidget(self.button)

		self.label = QWidget()
		self.label.setFixedSize(self.button.sizeHint())
		self._set_label_colour(self.button.colour)
		hbox.addWidget(self.label)

	def _connect_signals(self):
		self.button.colour_changed.connect(self._set_label_colour)

	@pyqtSlot(QColor)
	def _set_label_colour(self, colour):
		set_background_colour(self.label, colour)

	def sizeHint(self):
		button_size = self.button.sizeHint()
		return QSize(2 * button_size.width(), button_size.height())


class ColourPickerButton(ImageButton):
	colour_changed = pyqtSignal(QColor)

	def __init__(self, init_colour=None, dialog_title="Pick Colour", force_alpha=False):
		super().__init__()
		if init_colour is None:
			init_colour = Qt.White
		self._title = dialog_title
		self._alpha = force_alpha

		if isinstance(init_colour, QColor):
			self._colour = init_colour
			self._alpha |= init_colour.alpha() != 255
		else:
			self._colour = QColor(*init_colour)
			self._alpha |= len(init_colour) == 4

		self.clicked.connect(self._dialog)

		self.setSizePolicy(QSizePolicy())

	@property
	def colour(self):
		return self._colour

	@colour.setter
	def colour(self, new_colour):
		if not isinstance(new_colour, QColor):
			new_colour = QColor(*new_colour)

		if new_colour != self._colour:
			self._colour = new_colour
			self.colour_changed.emit(self._colour)

	def _dialog(self):
		flags = QColorDialog.ShowAlphaChannel if self._alpha else QColorDialog.ColorDialogOptions()
		colour = QColorDialog.getColor(self.colour, self, self._title, flags)
		if colour.isValid():
			self.colour = colour


class MultiplierSlider(QSlider):
	valueChanged = pyqtSignal(float)

	def __init__(self, *args, step=1, **kw):
		super().__init__(*args, **kw)
		super().valueChanged.connect(lambda: self.valueChanged.emit(self.value()))
		self.mult = step
		self.setMinimum(0)
		self.setMaximum(100 * step)
		self.setSingleStep(step)
		self.setPageStep(10 * step)

	def value(self):
		return self._get(super().value())

	def setValue(self, value):
		return super().setValue(self._set(value))

	def minimum(self):
		return self._get(super().minimum())

	def setMinimum(self, value):
		return super().setMinimum(self._set(value))

	def maximum(self):
		return self._get(super().maximum())

	def setMaximum(self, value):
		return super().setMaximum(self._set(value))

	def singleStep(self):
		return self._get(super().singleStep())

	def setSingleStep(self, value):
		return super().setSingleStep(self._set(value))

	def pageStep(self):
		return self._get(super().pageStep())

	def setPageStep(self, value):
		return super().setPageStep(self._set(value))

	def tickInterval(self):
		return self._get(super().tickInterval())

	def setTickInterval(self, value):
		return super().setTickInterval(self._set(value))

	def _get(self, value):
		return value * self.mult

	def _set(self, value):
		return int(value / self.mult)


class FlowLayout(QLayout):
	def __init__(self, parent=None, orientation=Qt.Horizontal, margin=0, spacing=-1):
		super().__init__(parent)
		self.orientation = orientation

		if parent is not None:
			self.setContentsMargins(margin, margin, margin, margin)

		self.setSpacing(spacing)

		self.itemList = []

	def __del__(self):
		item = self.takeAt(0)
		while item:
			item = self.takeAt(0)

	def addItem(self, item):
		self.itemList.append(item)

	def count(self):
		return len(self.itemList)

	def itemAt(self, index):
		if index >= 0 and index < len(self.itemList):
			return self.itemList[index]

		return None

	def takeAt(self, index):
		if index >= 0 and index < len(self.itemList):
			return self.itemList.pop(index)

		return None

	def expandingDirections(self):
		return Qt.Orientations(Qt.Orientation(0))

	def hasHeightForWidth(self):
		return True

	def heightForWidth(self, width):
		return self.doLayout(QRect(0, 0, width, 0), True)

	def setGeometry(self, rect):
		super().setGeometry(rect)
		self.doLayout(rect, False)

	def sizeHint(self):
		return self.minimumSize()

	def minimumSize(self):
		size = QSize()

		for item in self.itemList:
			size = size.expandedTo(item.minimumSize())

		margin, _, _, _ = self.getContentsMargins()

		size += QSize(2 * margin, 2 * margin)
		return size

	def doLayout(self, rect, testOnly):
		x = rect.x()
		y = rect.y()
		lineHeight = columnWidth = heightForWidth = 0
		horizontal = self.orientation == Qt.Horizontal

		for item in self.itemList:
			wid = item.widget()
			spaceX = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Horizontal)
			spaceY = self.spacing() + wid.style().layoutSpacing(QSizePolicy.PushButton, QSizePolicy.PushButton, Qt.Vertical)

			if horizontal:
				nextX = x + item.sizeHint().width() + spaceX
				if nextX - spaceX > rect.right() and lineHeight > 0:
					x = rect.x()
					y = y + lineHeight + spaceY
					nextX = x + item.sizeHint().width() + spaceX
					lineHeight = 0

				if not testOnly:
					item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

				x = nextX
				lineHeight = max(lineHeight, item.sizeHint().height())

			else:
				nextY = y + item.sizeHint().height() + spaceY
				if nextY - spaceY > rect.bottom() and columnWidth > 0:
					x = x + columnWidth + spaceX
					y = rect.y()
					nextY = y + item.sizeHint().height() + spaceY
					columnWidth = 0

				heightForWidth += item.sizeHint().height() + spaceY
				if not testOnly:
					item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

				y = nextY
				columnWidth = max(columnWidth, item.sizeHint().width())

		return y + lineHeight - rect.y() if horizontal else heightForWidth - rect.y()


class Icons(LazyDirectEnum):
	X = 'x'
	PLUS = 'plus'
	MINUS = 'minus'

	@classmethod
	def _lazy_init(cls, symbol):
		# QPixmaps require a QGuiApplication, so we create one if it doesn't exist already
		if QApplication.instance() is None:
			app = QApplication([])
		assert isinstance(QApplication.instance(), QGuiApplication), f"Using icons from {cls.__qualname__} requires the running QCoreApplication to be a QGuiApplication"

		img = QImage(256, 256, QImage.Format_ARGB32)
		painter = QPainter(img)
		h, w = img.height(), img.width()

		if symbol.lower() == 'x':
			painter.setPen(QPen(Qt.red, 10, Qt.SolidLine, Qt.RoundCap))
			painter.drawLine(w//8, h//8, 7*w//8, 7*h//8)
			painter.drawLine(w//8, 7*h//8, 7*w//8, h//8)

		elif symbol.lower() == 'plus':
			painter.setPen(QPen(Qt.blue, 10, Qt.SolidLine, Qt.RoundCap))
			painter.drawLine(w//2, h//8, w//2, 7*h//8)
			painter.drawLine(w//8, h//2, 7*w//8, h//2)

		elif symbol.lower() == 'minus':
			painter.setPen(QPen(Qt.blue, 10, Qt.SolidLine, Qt.RoundCap))
			painter.drawLine(w//8, h//2, 7*w//8, h//2)

		painter.end()
		return QPixmap.fromImage(img)
