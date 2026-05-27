import logging
from tkinter import Button, Frame, Label, Menu, PhotoImage, Toplevel

from wireviz_gui.images import slightlynybbled_logo_small

_norm_font    = ("Segoe UI", 10)
_heading_font = ("Segoe UI", 13, "bold")

_link_fg  = "#1a66cc"
_alert_fg = "#cc2222"


class BaseFrame(Frame):
    _normal  = {"font": ("Segoe UI", 10)}
    _link    = {"font": ("Segoe UI", 10), "fg": "#1a66cc"}
    _red     = {"font": ("Segoe UI", 10), "fg": "#cc2222"}
    _heading = {"font": ("Segoe UI", 13, "bold")}

    def __init__(self, parent, loglevel, **kwargs):
        self._parent = parent
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(loglevel)

        super().__init__(self._parent, **kwargs)


class BaseMenu(Menu):
    def __init__(self, parent, loglevel=logging.INFO, **kwargs):
        self._parent = parent
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(loglevel)
        super().__init__(self._parent, tearoff=False, **kwargs)


class ToplevelBase(Toplevel):
    def __init__(self, parent, loglevel=logging.INFO, **kwargs):
        self._parent = parent
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(loglevel)
        super().__init__(self._parent, **kwargs)

        self._icon = PhotoImage(data=slightlynybbled_logo_small)
        self.tk.call("wm", "iconphoto", self._w, self._icon)


class NormButton(Button):
    def __init__(self, *args, **kwargs):
        super().__init__(font=_norm_font, *args, **kwargs)


class HeadButton(Button):
    def __init__(self, *args, **kwargs):
        super().__init__(font=_heading_font, *args, **kwargs)


class NormLabel(Label):
    def __init__(self, *args, **kwargs):
        super().__init__(font=_norm_font, *args, **kwargs)


class AlertLabel(NormLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(fg=_alert_fg, *args, **kwargs)


class LinkLabel(NormLabel):
    def __init__(self, *args, **kwargs):
        super().__init__(fg=_link_fg, *args, **kwargs)


class HeadLabel(Label):
    def __init__(self, *args, **kwargs):
        super().__init__(font=_heading_font, *args, **kwargs)
