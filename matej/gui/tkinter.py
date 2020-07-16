import numpy as np
from tkinter import *


class ToolTip(Toplevel):
	def __init__(self, widget, text="", pos=None, *, bg='yellow', borderwidth=1, font=('times', 10, 'normal'), **kw):
		super().__init__(widget)
		self.widget = widget
		self.pos = pos

		self.label = Label(self, text=text, justify='left', relief='solid', background=bg, borderwidth=borderwidth, font=font, **kw)
		self.label.pack(ipadx=1)

		self.binds = widget.bind('<Enter>', self.show), widget.bind('<Leave>', self.hide)
		self.wm_overrideredirect(True)

		self.hide()

	def show(self, event=None):
		if event is None or self.pos is not None:
			x, y = np.array(self.widget.bbox('insert')[:2]) + self.pos
		else:
			x, y = event.x_root, event.y_root
		self.wm_geometry(f'+{x}+{y}')
		self.deiconify()

	def hide(self, event=None):
		self.withdraw()
