import logging
import tkinter as tk
from pathlib import Path
from typing import Callable, List, Optional

from wireviz_gui._base import BaseMenu


class Menu(BaseMenu):
    def __init__(
        self,
        parent,
        open_file: Callable,
        save: Callable,
        save_as: Callable,
        save_graph_image: Callable,
        export_all: Callable,
        refresh: Callable,
        reload_file: Callable,
        about: Callable,
        syntax_reference: Optional[Callable] = None,
        new_file: Optional[Callable] = None,
        load_example: Optional[Callable] = None,
        close_tab: Optional[Callable] = None,
        examples: Optional[dict] = None,
        recent_files: Optional[List[str]] = None,
        open_recent: Optional[Callable] = None,
        get_recent_files: Optional[Callable] = None,
        loglevel=logging.INFO,
        **kwargs,
    ):
        super().__init__(parent=parent, loglevel=loglevel, **kwargs)

        self._file_menu = FileMenu(
            self._parent,
            open_file=open_file,
            save=save,
            save_as=save_as,
            save_graph_image=save_graph_image,
            export_all=export_all,
            refresh=refresh,
            reload_file=reload_file,
            new_file=new_file,
            load_example=load_example,
            close_tab=close_tab,
            examples=examples,
            recent_files=recent_files,
            open_recent=open_recent,
            get_recent_files=get_recent_files,
        )
        self.add_cascade(label="File", menu=self._file_menu)
        self.add_cascade(label="Help", menu=HelpMenu(self._parent, about=about, syntax_reference=syntax_reference))


class FileMenu(BaseMenu):
    def __init__(
        self,
        parent,
        open_file: Callable,
        save: Callable,
        save_as: Callable,
        save_graph_image: Callable,
        export_all: Callable,
        refresh: Callable,
        reload_file: Callable,
        new_file: Optional[Callable] = None,
        load_example: Optional[Callable] = None,
        close_tab: Optional[Callable] = None,
        examples: Optional[dict] = None,
        recent_files: Optional[List[str]] = None,
        open_recent: Optional[Callable] = None,
        get_recent_files: Optional[Callable] = None,
        loglevel=logging.INFO,
        **kwargs,
    ):
        super().__init__(parent=parent, loglevel=loglevel, **kwargs)

        if new_file:
            self.add_command(label="New (CTRL+N)", command=lambda: new_file())

        self.add_command(label="Open (CTRL+O)", command=lambda: open_file())

        # Recent files submenu
        if open_recent:
            self._recent_menu = tk.Menu(self, tearoff=0)
            self.add_cascade(label="Abrir reciente", menu=self._recent_menu)
            self._open_recent = open_recent
            self._get_recent_files = get_recent_files
            self._populate_recent(recent_files or [])
            # Refresh when the File menu is opened
            self.bind("<Map>", self._on_file_menu_open)

        self.add_separator()
        self.add_command(label="Save (CTRL+S)", command=lambda: save())
        self.add_command(label="Save As...", command=lambda: save_as())
        self.add_separator()

        export_menu = tk.Menu(self, tearoff=0)
        export_menu.add_command(
            label="Graph Image (PNG)...", command=lambda: save_graph_image()
        )
        export_menu.add_command(
            label="All Formats (PNG, SVG, HTML)...", command=lambda: export_all()
        )
        self.add_cascade(label="Export", menu=export_menu)

        if examples and load_example:
            examples_menu = tk.Menu(self, tearoff=0)
            for name, content in examples.items():
                examples_menu.add_command(
                    label=name, command=lambda c=content, n=name: load_example(n, c)
                )
            self.add_cascade(label="Examples", menu=examples_menu)

        self.add_separator()
        self.add_command(label="Refresh Image (CTRL+L)", command=lambda: refresh())
        self.add_command(label="Reload File (CTRL+R)", command=lambda: reload_file())

        if close_tab:
            self.add_separator()
            self.add_command(label="Close Tab (CTRL+W)", command=lambda: close_tab())

    def _populate_recent(self, files: List[str]):
        self._recent_menu.delete(0, "end")
        if not files:
            self._recent_menu.add_command(label="(sin archivos recientes)", state="disabled")
        else:
            for i, filepath in enumerate(files):
                label = f"{i + 1}. {Path(filepath).name}  —  {Path(filepath).parent}"
                self._recent_menu.add_command(
                    label=label,
                    command=lambda p=filepath: self._open_recent(p),
                )

    def _on_file_menu_open(self, _event=None):
        if self._get_recent_files:
            self._populate_recent(self._get_recent_files())


class HelpMenu(BaseMenu):
    def __init__(self, parent, about: Callable, syntax_reference: Optional[Callable] = None, loglevel=logging.INFO, **kwargs):
        super().__init__(parent=parent, loglevel=loglevel, **kwargs)

        if syntax_reference:
            self.add_command(label="Referencia de Sintaxis (F1)", command=lambda: syntax_reference())
            self.add_separator()
        self.add_command(label="About", command=lambda: about())


if __name__ == "__main__":
    # This section is only used for testing the menu structure
    window = tk.Tk()

    menu = Menu(window)  # type: ignore
    window.config(menu=menu)

    window.mainloop()
