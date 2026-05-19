import json
import logging
import sys
import tkinter as tk
from io import BytesIO
from pathlib import Path
from tkinter import ttk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from tkinter.messagebox import showerror, showinfo
from typing import Callable, Optional

import yaml
from graphviz import ExecutableNotFound
from PIL import Image, ImageTk
from tk_tools import ToolTip
from wireviz.DataClasses import Connector, Metadata, Options, Tweak
from wireviz.wireviz import Harness, parse
from yaml import YAMLError

from wireviz_gui import __version__
from wireviz_gui._base import BaseFrame, HeadButton, LinkLabel, NormLabel, ToplevelBase
from wireviz_gui.dialogs import (
    AboutFrame,
    AddCableFrame,
    AddConnectionFrame,
    AddConnectorFrame,
    MetadataDialog,
)
from wireviz_gui.examples import EXAMPLES
from wireviz_gui.images import (
    add_box_fill,
    add_circle_fill,
    folder_transfer_fill,
    links_fill,
    logo,
    map_pin_add_fill,
    refresh_fill,
    slightlynybbled_logo_small,
)
from wireviz_gui.assembly_dialog import AssemblyManualDialog
from wireviz_gui.assembly_export import export_manual_html, export_manual_pdf
from wireviz_gui.mating_dialog import AddMateDialog
from wireviz_gui.menus import Menu
from wireviz_gui.syntax_help import SyntaxReferencePanel, SyntaxReferenceWindow


def preprocess_yaml_data(data):
    """
    Preprocess the YAML data to handle compatibility issues and normalize connections.
    - Moves 'label' from cables to 'notes' (compatibility fix).
    - Resolves 'Connector.Pin' syntax in connections to {Connector: Pin} (syntax fix).
    - Flattens nested dictionary connections (star topology).
    """
    if not isinstance(data, dict):
        return data

    # Fix: Handle Cable labels by moving them to notes
    if "cables" in data and isinstance(data["cables"], dict):
        for cable_name, cable_data in data["cables"].items():
            if isinstance(cable_data, dict) and "label" in cable_data:
                label = cable_data.pop("label")
                if "notes" in cable_data:
                    cable_data["notes"] = str(cable_data["notes"]) + "\n" + str(label)
                else:
                    cable_data["notes"] = str(label)

    if "connections" not in data:
        return data

    connections = data["connections"]
    if not isinstance(connections, list):
        return data

    # Get known connectors (designators) to support Connector.Pin syntax
    known_connectors = set()
    if "connectors" in data and isinstance(data["connectors"], dict):
        known_connectors = set(data["connectors"].keys())

    new_connections = []

    # Helper to parse node string into wireviz compatible format
    def parse_node(node_str):
        # Fix: Handle Connector.Pin syntax
        if isinstance(node_str, str) and "." in node_str:
            parts = node_str.split(".")
            if len(parts) == 2:
                designator = parts[0]
                pin = parts[1]
                if designator in known_connectors:
                    # It is Connector.Pin, convert to {Designator: Pin}
                    return {designator: pin}
        return node_str

    for conn in connections:
        if isinstance(conn, dict):
            keys = list(conn.keys())
            if len(keys) == 0:
                continue

            start_node = keys[0]
            value = conn[start_node]

            if isinstance(value, list):
                for item in value:
                    p = [parse_node(start_node)]
                    if isinstance(item, dict):
                        if len(item) > 0:
                            k = list(item.keys())[0]
                            v = list(item.values())[0]
                            p.append(parse_node(v))
                            p.append(parse_node(k))
                    else:
                        p.append(parse_node(item))
                    new_connections.append(p)
            else:
                p = [parse_node(start_node), parse_node(value)]
                new_connections.append(p)
        else:
            # If it's a list, we should also check for Connector.Pin syntax in its items
            if isinstance(conn, list):
                new_conn = [parse_node(item) for item in conn]
                new_connections.append(new_conn)
            else:
                new_connections.append(conn)

    data["connections"] = new_connections
    return data


# Alias for backward compatibility if needed, though mostly internal
normalize_connections = preprocess_yaml_data




class _CloseableNotebook(ttk.Notebook):
    """ttk.Notebook that shows a ✕ close button inside each tab label.

    Clicking the ✕ part of a tab label calls on_close(index).
    """

    _SUFFIX = "  ✕"

    def __init__(self, parent, on_close=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._on_close = on_close
        self.bind("<Button-1>", self._check_close_click, add=True)

    # Override add() to append ✕ suffix
    def add(self, child, **kwargs):
        if "text" in kwargs and not kwargs["text"].endswith(self._SUFFIX):
            kwargs["text"] = kwargs["text"] + self._SUFFIX
        super().add(child, **kwargs)

    # Override tab() to keep ✕ suffix on text updates
    def tab(self, tab_id, option=None, **kwargs):
        if "text" in kwargs and not kwargs["text"].endswith(self._SUFFIX):
            kwargs["text"] = kwargs["text"] + self._SUFFIX
        return super().tab(tab_id, option, **kwargs)

    def _check_close_click(self, event):
        """Detect clicks on the ✕ area (rightmost ~20px of a tab label)."""
        if self.identify(event.x, event.y) != "label":
            return
        try:
            idx = self.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return
        # Scan right to find the right edge of this tab (within 24px)
        x = event.x + 1
        limit = event.x + 24
        while x <= limit:
            try:
                if self.index(f"@{x},{event.y}") != idx:
                    # Right edge found; click must be within 18px of it
                    if x - event.x <= 18 and self._on_close:
                        self._on_close(idx)
                    return
            except tk.TclError:
                # Past all tabs → right edge of last tab
                if x - event.x <= 18 and self._on_close:
                    self._on_close(idx)
                return
            x += 1


class _RecentFiles:
    """Manages a persistent list of recently opened/saved files."""
    _MAX = 10
    _CONFIG_DIR = Path.home() / ".wireviz-gui"
    _FILE = _CONFIG_DIR / "recent_files.json"

    def load(self) -> list:
        try:
            if self._FILE.exists():
                data = json.loads(self._FILE.read_text(encoding="utf-8"))
                return [p for p in data if Path(p).exists()][:self._MAX]
        except Exception:
            pass
        return []

    def add(self, filepath: str):
        files = self.load()
        path = str(Path(filepath).resolve())
        if path in files:
            files.remove(path)
        files.insert(0, path)
        files = files[:self._MAX]
        try:
            self._CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            self._FILE.write_text(json.dumps(files, indent=2), encoding="utf-8")
        except Exception:
            pass


class Application(tk.Tk):
    def __init__(self, loglevel=logging.INFO, **kwargs):
        self._logger = logging.getLogger(self.__class__.__name__)
        self._logger.setLevel(loglevel)

        super().__init__(**kwargs)

        self.title(f"wireviz-gui {__version__}")
        self._recent_files_mgr = _RecentFiles()

        self._icon = tk.PhotoImage(data=slightlynybbled_logo_small)
        self.tk.call("wm", "iconphoto", self._w, self._icon)

        r = 0
        self._title_frame = TitleFrame(self)
        self._title_frame.grid(row=r, column=0, sticky="ew")

        r += 1
        # Main content: horizontal paned window (tabs | syntax reference)
        self._main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        self._main_paned.grid(row=r, column=0, sticky="news")

        self._notebook = _CloseableNotebook(
            self._main_paned, on_close=self._close_tab_by_index
        )
        self._main_paned.add(self._notebook, weight=3)

        self._syntax_panel = SyntaxReferencePanel(self._main_paned, compact=True)
        self._main_paned.add(self._syntax_panel, weight=1)
        self._syntax_visible = True

        # Configure grid expansion
        self.grid_rowconfigure(r, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.add_tab()

        self._menu = Menu(
            self,
            open_file=lambda: self.get_active_frame().open_file()
            if self.get_active_frame()
            else None,
            save=lambda: self.get_active_frame().save_file()
            if self.get_active_frame()
            else None,
            save_as=lambda: self.get_active_frame().save_as_file()
            if self.get_active_frame()
            else None,
            save_graph_image=lambda: self.get_active_frame().save_graph_image()
            if self.get_active_frame()
            else None,
            export_all=lambda: self.get_active_frame().export_all()
            if self.get_active_frame()
            else None,
            refresh=lambda: self.get_active_frame().parse_text()
            if self.get_active_frame()
            else None,
            reload_file=lambda: self.get_active_frame().reload_file()
            if self.get_active_frame()
            else None,
            about=self._about,
            syntax_reference=self._open_syntax_reference,
            new_file=lambda: self.add_tab(),
            load_example=self.add_tab,
            close_tab=self.close_current_tab,
            examples=EXAMPLES,
            recent_files=self._recent_files_mgr.load(),
            open_recent=self._open_recent_file,
            get_recent_files=self._recent_files_mgr.load,
        )
        self.config(menu=self._menu)

        self.bind_all("<F1>", lambda _: self._open_syntax_reference())
        self.bind_all(
            "<Control-n>",
            lambda _: self.add_tab(),
        )
        self.bind_all(
            "<Control-o>",
            lambda _: self.get_active_frame().open_file()
            if self.get_active_frame()
            else None,
        )
        self.bind_all(
            "<Control-s>",
            lambda _: self.get_active_frame().save_file()
            if self.get_active_frame()
            else None,
        )
        self.bind_all(
            "<Control-r>",
            lambda _: self.get_active_frame().reload_file()
            if self.get_active_frame()
            else None,
        )
        self.bind_all("<Control-w>", lambda _: self.close_current_tab())

        self.mainloop()

    def _about(self):
        top = ToplevelBase(self)
        top.title("About")
        AboutFrame(top).grid()

    def _open_syntax_reference(self):
        """Toggle the embedded syntax reference panel."""
        try:
            if self._syntax_visible:
                self._main_paned.remove(self._syntax_panel)
                self._syntax_visible = False
            else:
                self._main_paned.add(self._syntax_panel, weight=1)
                self._syntax_visible = True
        except Exception:
            pass

    def _open_recent_file(self, filepath: str):
        """Open a file from the recent files list in a new tab."""
        path = Path(filepath)
        if not path.exists():
            showerror("File Not Found", f"The file no longer exists:\n{filepath}")
            return
        frame = self.add_tab(title=path.name, filepath=filepath)
        if frame:
            frame._text_entry_frame.load(path.read_text(encoding="utf-8"))
            frame.parse_text()

    def get_active_frame(self):
        try:
            tab_id = self._notebook.select()
            if not tab_id:
                return None
            return self._notebook.nametowidget(tab_id)
        except tk.TclError:
            return None

    def add_tab(self, title="Untitled", content=None, filepath=None):
        def on_title_change(new_title):
            try:
                self._notebook.tab(frame, text=new_title)
            except tk.TclError:
                pass

        frame = InputOutputFrame(
            self._notebook,
            on_title_change=on_title_change,
            on_syntax_help=self._open_syntax_reference,
            on_file_opened=self._recent_files_mgr.add,
        )

        if content:
            frame._text_entry_frame.load(content)
            frame.parse_text()

        if filepath:
            frame._current_file_path = filepath

        self._notebook.add(frame, text=title)
        self._notebook.select(frame)
        return frame

    def close_current_tab(self):
        active_tab = self.get_active_frame()
        if active_tab:
            active_tab.destroy()
        if not self._notebook.tabs():
            self.add_tab()

    def _close_tab_by_index(self, index: int):
        """Close a specific tab by its notebook index (called from tab ✕ button)."""
        try:
            tabs = self._notebook.tabs()
            if 0 <= index < len(tabs):
                widget = self._notebook.nametowidget(tabs[index])
                widget.destroy()
        except Exception:
            pass
        if not self._notebook.tabs():
            self.add_tab()


class TitleFrame(BaseFrame):
    def __init__(self, parent, loglevel=logging.INFO):
        super().__init__(parent, loglevel=loglevel)

        self._logo_img = tk.PhotoImage(data=logo)

        r = 0
        tk.Label(self, image=self._logo_img).grid(row=r, column=0, sticky="news")


class InputOutputFrame(BaseFrame):
    def __init__(self, parent, on_title_change=None, on_syntax_help=None,
                 on_edit_metadata=None, on_file_opened=None,
                 loglevel=logging.INFO):
        super().__init__(parent, loglevel=loglevel)

        self._current_file_path = None
        self._custom_image_paths = []
        self._on_title_change = on_title_change
        self._on_syntax_help = on_syntax_help
        self._on_file_opened = on_file_opened
        self._harness = Harness(Metadata(), Options(), Tweak())

        r = 0
        self._button_frame = ButtonFrame(
            self,
            on_click_add_connector=self.add_connector,
            on_click_add_cable=self.add_cable,
            on_click_add_connection=self.add_connection,
            on_click_add_mate=self.add_mate,
            on_click_save_image=self.save_graph_image,
            on_click_export=self.export_all,
            on_click_refresh=self.parse_text,
            on_click_set_image_path=self.set_image_path,
            on_click_syntax_help=self._on_syntax_help,
            on_click_edit_metadata=on_edit_metadata if on_edit_metadata else self._edit_metadata,
            on_click_generate_manual=self.generate_assembly_manual,
        )
        self._button_frame.grid(row=r, column=0, sticky="ew")

        r += 1
        self._structure_view_frame = StructureViewFrame(
            self, on_update_callback=self.refresh_view, harness=self._harness
        )
        self._structure_view_frame.grid(row=r, column=0, sticky="ew")

        r += 1
        self._paned_window = ttk.PanedWindow(self, orient=tk.VERTICAL)
        self._paned_window.grid(row=r, column=0, sticky="news")

        # Configure expansion for the paned window row
        self.grid_rowconfigure(r, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._text_entry_frame = TextEntryFrame(
            self._paned_window, on_update_callback=self.parse_text
        )
        self._harness_view_frame = HarnessViewFrame(self._paned_window)

        self._paned_window.add(self._text_entry_frame, weight=1)
        self._paned_window.add(self._harness_view_frame, weight=3)

        r += 1
        self._status_bar = _StatusBar(self)
        self._status_bar.grid(row=r, column=0, sticky="ew")

    def _update_yaml_section(self, section, new_data):
        current_text = self._text_entry_frame.get()
        try:
            data = yaml.safe_load(current_text) or {}

            if section not in data:
                # If section doesn't exist, create appropriate container
                if isinstance(new_data, list):
                    data[section] = []
                elif isinstance(new_data, dict):
                    data[section] = {}
                else:
                    data[section] = None  # Should not happen based on current use

            if isinstance(new_data, list):
                # For lists (connections), append
                if not isinstance(data[section], list):
                    if data[section] is None:
                        data[section] = []
                    else:
                        if not isinstance(data[section], list):
                            pass

                data[section].append(new_data)

            elif isinstance(new_data, dict):
                # For dicts (connectors, cables), update/merge
                if not isinstance(data[section], dict):
                    if data[section] is None:
                        data[section] = {}

                data[section].update(new_data)

            # Replace as one undo-able operation (Ctrl+Z can revert an "Add" action)
            self._text_entry_frame.replace(
                yaml.dump(data, default_flow_style=False, sort_keys=False)
            )
            self.parse_text(silent=True)

        except yaml.YAMLError as e:
            showerror("YAML Error", f"Error processing existing YAML: {e}")
            return

    def add_connector(self):
        top = ToplevelBase(self)
        top.title("Add Connector")

        def on_save(connector_data):
            top.destroy()
            self._update_yaml_section("connectors", connector_data)

        AddConnectorFrame(top, harness=self._harness, on_save_callback=on_save).grid()

    def add_cable(self):
        top = ToplevelBase(self)
        top.title("Add Cable")

        def on_save(cable_data):
            top.destroy()
            self._update_yaml_section("cables", cable_data)

        AddCableFrame(top, harness=self._harness, on_save_callback=on_save).grid()

    def add_connection(self):
        top = ToplevelBase(self)
        top.title("Add Connection")

        def on_save(connection_data):
            top.destroy()
            self._update_yaml_section("connections", connection_data)

        dialog = AddConnectionFrame(
            top, harness=self._harness,
            on_save_callback=on_save,
            get_yaml_text=self._text_entry_frame.get,
        )
        dialog.grid()
        # Refresh dropdowns whenever the dialog regains focus (harness may have been updated)
        top.bind("<FocusIn>", lambda _: dialog.refresh_dropdowns())

    def add_mate(self):
        top = ToplevelBase(self)
        top.title("Mate Connectors")

        def on_save(mate_data):
            top.destroy()
            self._update_yaml_section("connections", mate_data)

        dialog = AddMateDialog(top, harness=self._harness, on_save_callback=on_save, get_yaml_text=self._text_entry_frame.get)
        dialog.grid()
        top.bind("<FocusIn>", lambda _: dialog.refresh_dropdowns())

    def open_file(self):
        file_name = askopenfilename(
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")]
        )
        if not file_name:
            return

        try:
            with open(file_name, "r", encoding="utf-8") as f:
                content = f.read()
            self._text_entry_frame.load(content)
            self._current_file_path = file_name
            if self._on_title_change:
                self._on_title_change(Path(file_name).name)
            self._status_bar.set_file(file_name)
            self.parse_text()
            if self._on_file_opened:
                self._on_file_opened(file_name)
        except Exception as e:
            showerror("Open Error", f"Could not open file:\n{e}")

    def reload_file(self):
        if self._current_file_path:
            try:
                with open(self._current_file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                self._text_entry_frame.load(content)
                self.parse_text()
            except Exception as e:
                showerror("Reload Error", f"Could not reload file:\n{e}")
        else:
            showinfo("Reload Info", "No file to reload.")

    def _image_paths(self):
        """Return image search paths: open file dir + user-configured dirs."""
        paths = []
        if self._current_file_path:
            paths.append(Path(self._current_file_path).parent.resolve())
        for p in self._custom_image_paths:
            rp = Path(p).resolve()
            if rp not in paths:
                paths.append(rp)
        return paths

    def set_image_path(self):
        from tkinter.filedialog import askdirectory
        folder = askdirectory(title="Select image search folder")
        if folder:
            path = Path(folder).resolve()
            if path not in [Path(p).resolve() for p in self._custom_image_paths]:
                self._custom_image_paths.append(path)
            self._status_bar.set_image_path(str(path))
            self.parse_text(silent=True)

    def _edit_metadata(self):
        """Open metadata editor dialog and update the YAML on save."""
        current_text = self._text_entry_frame.get()
        try:
            data = yaml.safe_load(current_text) or {}
        except Exception:
            data = {}
        current_meta = data.get("metadata", {}) or {}

        def on_save(new_meta):
            self._update_yaml_section("metadata", new_meta)

        MetadataDialog(self, current_metadata=current_meta, on_save_callback=on_save)

    def save_file(self):
        if self._current_file_path:
            yaml_input = self._text_entry_frame.get()
            if yaml_input.strip() == "":
                return

            # Validate YAML before saving
            try:
                data = yaml.safe_load(yaml_input)
                data = normalize_connections(data)
                parse(inp=data, return_types=("harness",), image_paths=self._image_paths())
            except YAMLError as e:
                showerror("Save Error", f"Invalid YAML content:\n{e}")
                return
            except Exception as e:
                showerror("Save Error", f"Invalid Wireviz YAML:\n{e}")
                return

            try:
                with open(self._current_file_path, "w", encoding="utf-8") as f:
                    f.write(yaml_input)
            except Exception as e:
                showerror("Save Error", f"Could not save file:\n{e}")
        else:
            self.save_as_file()

    def save_as_file(self):
        yaml_input = self._text_entry_frame.get()
        if yaml_input.strip() == "":
            return

        # Validate YAML before saving
        try:
            data = yaml.safe_load(yaml_input)
            data = normalize_connections(data)
            parse(inp=data, return_types=("harness",), image_paths=self._image_paths())
        except YAMLError as e:
            showerror("Save Error", f"Invalid YAML content:\n{e}")
            return
        except Exception as e:
            showerror("Save Error", f"Invalid Wireviz YAML:\n{e}")
            return

        file_name = asksaveasfilename(
            defaultextension=".yaml",
            filetypes=[("YAML files", "*.yaml"), ("All files", "*.*")],
        )
        if file_name is None or file_name.strip() == "":
            return

        try:
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(yaml_input)
            self._current_file_path = file_name
            if self._on_title_change:
                self._on_title_change(Path(file_name).name)
            self._status_bar.set_file(file_name)
            if self._on_file_opened:
                self._on_file_opened(file_name)
        except Exception as e:
            showerror("Save Error", f"Could not save file:\n{e}")

    def save_yaml(self):
        """Deprecated: use save_file or save_as_file"""
        self.save_file()

    def save_graph_image(self):
        if not self._harness_view_frame.has_image():
            showinfo("Save Image", "No image to save.")
            return

        file_name = asksaveasfilename(
            title="Export Graph Image",
            defaultextension=".png",
            filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
        )
        if not file_name:
            return

        self._harness_view_frame.save_image(file_name)

    def generate_assembly_manual(self):
        """Open the assembly manual dialog and generate PDF/HTML."""
        yaml_text = self._text_entry_frame.get()
        if not yaml_text.strip():
            showinfo("Manual", "No hay YAML para generar el manual.")
            return

        def on_generate(spec):
            file_name = asksaveasfilename(
                title="Guardar Manual de Ensamblaje",
                defaultextension=".html",
                filetypes=[
                    ("HTML files", "*.html"),
                    ("PDF files", "*.pdf"),
                    ("All files", "*.*"),
                ],
            )
            if not file_name:
                return

            try:
                if file_name.lower().endswith(".pdf"):
                    result = export_manual_pdf(spec, file_name)
                else:
                    result = export_manual_html(spec, file_name)
                showinfo("Manual generado", f"Manual guardado en:\n{result}")
            except Exception as e:
                showerror("Error", f"Error generando manual:\n{e}")

        AssemblyManualDialog(
            self,
            yaml_text=yaml_text,
            on_generate_callback=on_generate,
        )

    def export_all(self):
        file_name = asksaveasfilename(title="Export All Formats")
        if file_name is None or file_name.strip() == "":
            return

        path = Path(file_name)
        yaml_input = self._text_entry_frame.get()

        if yaml_input.strip() != "":
            try:
                data = yaml.safe_load(yaml_input)
                data = normalize_connections(data)
                parse(
                    inp=data,
                    output_dir=path.parent,
                    output_name=path.stem,
                    output_formats=(
                        "png",
                        "svg",
                        "html",
                        "tsv",
                    ),
                    image_paths=self._image_paths(),
                )
            except (ExecutableNotFound, FileNotFoundError):
                showerror(
                    "Error",
                    "Graphviz executable not found; Make sure that the "
                    "executable is installed and in your system PATH",
                )
                return
            except Exception as e:
                showerror("Error", f"An unexpected error occurred:\n{e}")
                return

    def parse_text(self, silent=False):
        """
        This is where the data is read from the text entry and parsed into an image.
        silent=True suppresses error popups (used during auto-refresh while typing).
        """
        yaml_input = self._text_entry_frame.get()
        if yaml_input.strip() != "":
            try:
                data = yaml.safe_load(yaml_input)
                data = normalize_connections(data)
                png_data, new_harness = parse(inp=data, return_types=("png", "harness"), image_paths=self._image_paths())
                self._harness.connectors = new_harness.connectors
                self._harness.cables = new_harness.cables
                self._harness.mates = new_harness.mates
                self._harness.additional_bom_items = new_harness.additional_bom_items

                self.refresh_view(png_data)
                self._status_bar.set_status(ok=True)
            except YAMLError as e:
                lines = str(e).lower()
                for line in lines.split("\n"):
                    if "line" in line:
                        # determine the line number that has a problem
                        parts = [line_part.strip() for line_part in line.split(",")]
                        part = [
                            line_part for line_part in parts if "line" in line_part
                        ][0]
                        error_line = part.split(" ")[1]
                        self._text_entry_frame.highlight_line(error_line)
                        break
                self._status_bar.set_status(ok=False, message=f"YAML: {str(e)[:80]}")
                if not silent:
                    showerror("Parse Error", f"Input is invalid: {e}")
                return
            except (ExecutableNotFound, FileNotFoundError):
                self._status_bar.set_status(ok=False, message="Graphviz not found in PATH")
                if not silent:
                    showerror(
                        "Error",
                        "Graphviz executable not found; Make sure that the "
                        "executable is installed and in your system PATH",
                    )
                return
            except Exception as e:
                msg = str(e)
                # Provide a specific hint when an image file can't be found
                if "not found in any of the following locations" in msg and not self._current_file_path:
                    self._status_bar.set_status(ok=False, message="Image not found – use File > Open or the 📍 button")
                    if not silent:
                        showerror(
                            "Image not found",
                            f"{msg}\n\nTo resolve this, either:\n"
                            "• Use File > Open to open the .yaml file from its folder\n"
                            "• Or click the 📍 button in the toolbar to set the image search folder"
                        )
                else:
                    self._status_bar.set_status(ok=False, message=msg[:100])
                    if not silent:
                        showerror("Error", f"An unexpected error occurred:\n{e}")
                return

        self._text_entry_frame.highlight_line(None)

    def refresh_view(self, png_data=None):
        if png_data:
            self._harness_view_frame.update_image(png_data)

        self._structure_view_frame.refresh()


class StructureViewFrame(BaseFrame):
    def __init__(
        self,
        parent,
        harness: Harness,
        on_update_callback: Optional[Callable] = None,
        loglevel=logging.INFO,
    ):
        super().__init__(parent=parent, loglevel=loglevel)

        self._harness = harness
        self._on_update_callback = on_update_callback

        self.refresh(False)

    def _load_connector_dialog(self, connector: Connector):
        top = ToplevelBase(self)
        top.title("Add Connector")

        def on_save(connector_data):
            top.destroy()
            # self.refresh(True)
            # The structure view refresh should happen when the main app parses text again.
            # But here we need to callback to the main app to update YAML.
            # This is tricky because StructureViewFrame doesn't have reference to Application methods directly.
            # However, the user flow is: Click structure item -> Edit.
            # But the current Dialogs are "AddConnectorFrame". They don't support Editing well yet
            # because they don't load data back fully if we just pass a string.
            # And our refactor changed `_save` to return a dict, not modify harness.
            # If we reuse AddConnectorFrame for editing, we need to handle the save callback differently.

            # The prompt asked for "Add gui-based harness building". Editing existing ones is a bonus/next step.
            # For now, I will disable the "Edit" click or leave it but it won't save correctly unless I fix it.
            # The current StructureViewFrame implementation passes `on_save_callback` which calls `self.refresh(True)`.
            # `AddConnectorFrame` now expects `on_save_callback` to take an argument `connector_data`.
            # `self.refresh` does not take that.
            # So the click listener in StructureViewFrame will break if I don't update it.
            pass

        # We need to update StructureViewFrame to handle the new callback signature if we want to support clicking existing items.
        # However, editing is complicated because we need to find the item in the YAML and replace it.
        # For now, I'll update the callback to accept the arg but do nothing, effectively making it read-only for now,
        # or just print it.
        def dummy_save(data):
            print("Edit saved (not implemented yet):", data)
            top.destroy()

        AddConnectorFrame(
            top,
            harness=self._harness,
            connector_name=str(connector),
            on_save_callback=dummy_save,
        ).grid()

    def refresh(self, execute_callback: bool = False):
        for child in self.winfo_children():
            child.destroy()

        NormLabel(self, text="Harness Elements:").grid(row=0, column=0, sticky="ew")

        if self._harness.connectors == {} and self._harness.cables == {}:
            # a nag screen; todo: replace when wireviz is updated so
            # that parse will return an instance of `Harness`
            self._logger.debug(
                "There appears to be no data in the "
                "`Harness` instance; Perhaps the "
                "instance is blank?"
            )
            NormLabel(self, text="(none)").grid(row=0, column=1, sticky="ew")

        c = 1
        for connector in self._harness.connectors:
            conn_label = LinkLabel(self, text=f"{connector}")
            conn_label.grid(row=0, column=c, sticky="ew")
            conn_label.bind(
                "<Button-1>", lambda _, cl=connector: self._load_connector_dialog(cl)
            )
            c += 1

        for cable in self._harness.cables:
            cable_label = LinkLabel(
                self,
                text=f"{cable}",
            )
            cable_label.grid(row=0, column=c, sticky="ew")
            cable_label.bind("<Button-1>", lambda _, cb=cable: print(cb))
            c += 1

        if execute_callback and self._on_update_callback is not None:
            self._on_update_callback()


class _StatusBar(BaseFrame):
    """Thin bar at the bottom of each tab showing file path and parse status."""

    def __init__(self, parent, loglevel=logging.INFO):
        super().__init__(parent, loglevel=loglevel)
        self.configure(bg="#f0f0f0", relief="sunken", bd=1)

        self._file_label = tk.Label(
            self, text="No file open", anchor="w",
            bg="#f0f0f0", font=("Arial", 9), fg="#666666"
        )
        self._file_label.grid(row=0, column=0, sticky="ew", padx=6, pady=2)

        self._status_label = tk.Label(
            self, text="", anchor="e",
            bg="#f0f0f0", font=("Arial", 9, "bold")
        )
        self._status_label.grid(row=0, column=1, sticky="e", padx=6, pady=2)

        self.grid_columnconfigure(0, weight=1)

    def set_file(self, filepath: str):
        self._img_hint = ""
        self._filepath = str(filepath)
        self._update_file_label()

    def set_image_path(self, path: str):
        self._img_hint = f"  |  img: {path}"
        self._update_file_label()

    def _update_file_label(self):
        base = getattr(self, "_filepath", "No file open")
        hint = getattr(self, "_img_hint", "")
        self._file_label.configure(text=f"{base}{hint}", fg="#333333")

    def set_status(self, ok: bool, message: str = ""):
        if ok:
            self._status_label.configure(text="\u2714 OK", fg="#007700")
        else:
            short = message[:70] if message else "Error"
            self._status_label.configure(text=f"\u2718 {short}", fg="#cc0000")


class ButtonFrame(BaseFrame):
    def __init__(
        self,
        parent,
        on_click_add_connector: Callable,
        on_click_add_cable: Callable,
        on_click_add_connection: Callable,
        on_click_add_mate: Callable,
        on_click_save_image: Callable,
        on_click_export: Callable,
        on_click_refresh: Callable,
        on_click_set_image_path: Optional[Callable] = None,
        on_click_syntax_help: Optional[Callable] = None,
        on_click_edit_metadata: Optional[Callable] = None,
        on_click_generate_manual: Optional[Callable] = None,
        loglevel=logging.INFO,
    ):
        super().__init__(parent, loglevel=loglevel)

        c = 0
        self._add_conn_img = tk.PhotoImage(data=add_box_fill)
        add_conn_btn = tk.Button(
            self, image=self._add_conn_img, command=on_click_add_connector
        )
        add_conn_btn.grid(row=0, column=c, sticky="ew")
        ToolTip(add_conn_btn, "Add Connector")

        c += 1
        self._add_cable_img = tk.PhotoImage(data=add_circle_fill)
        add_cable_btn = tk.Button(
            self, image=self._add_cable_img, command=on_click_add_cable
        )
        add_cable_btn.grid(row=0, column=c, sticky="ew")
        ToolTip(add_cable_btn, "Add Cable")

        c += 1
        self._add_connect_img = tk.PhotoImage(data=links_fill)
        add_connection_btn = tk.Button(
            self, image=self._add_connect_img, command=on_click_add_connection
        )
        add_connection_btn.grid(row=0, column=c, sticky="ew")
        ToolTip(add_connection_btn, "Add Connection")

        c += 1
        self._add_mate_img = tk.PhotoImage(data=add_box_fill)
        add_mate_btn = tk.Button(
            self, image=self._add_mate_img, command=on_click_add_mate
        )
        add_mate_btn.grid(row=0, column=c, sticky="ew")
        ToolTip(add_mate_btn, "Mate Connectors")

        c += 1
        self._export_img = tk.PhotoImage(data=folder_transfer_fill)
        save_img_btn = tk.Button(
            self, image=self._export_img, command=on_click_save_image
        )
        save_img_btn.grid(row=0, column=c, sticky="ew")
        ToolTip(save_img_btn, "Save Graph Image (PNG)")

        c += 1
        self._export_all_img = tk.PhotoImage(data=folder_transfer_fill)
        export_img_btn = tk.Button(
            self, image=self._export_all_img, command=on_click_export
        )
        export_img_btn.grid(row=0, column=c, sticky="ew")
        ToolTip(export_img_btn, "Export All (PNG, SVG, HTML, TSV)")

        c += 1
        self._refresh_img = tk.PhotoImage(data=refresh_fill)
        refresh_img_btn = HeadButton(
            self, image=self._refresh_img, command=on_click_refresh
        )
        refresh_img_btn.grid(row=0, column=c, sticky="ew")
        ToolTip(refresh_img_btn, "Refresh (Ctrl+L)")

        if on_click_set_image_path:
            c += 1
            self._imgpath_img = tk.PhotoImage(data=map_pin_add_fill)
            imgpath_btn = tk.Button(
                self, image=self._imgpath_img, command=on_click_set_image_path
            )
            imgpath_btn.grid(row=0, column=c, sticky="ew")
            ToolTip(imgpath_btn, "Set image search folder")

        if on_click_edit_metadata:
            c += 1
            meta_btn = tk.Button(
                self, text="≡", font=("Arial", 11, "bold"),
                command=on_click_edit_metadata,
                width=2, cursor="hand2",
                relief="flat", bg="#f0ede0", activebackground="#ddd8c0"
            )
            meta_btn.grid(row=0, column=c, sticky="ew", padx=(4, 0))
            ToolTip(meta_btn, "Editar Metadatos del documento")

        if on_click_syntax_help:
            c += 1
            help_btn = tk.Button(
                self, text="?", font=("Arial", 11, "bold"),
                command=on_click_syntax_help,
                width=2, cursor="hand2",
                relief="flat", bg="#e8f0fe", activebackground="#c5d8fd"
            )
            help_btn.grid(row=0, column=c, sticky="ew", padx=(4, 0))
            ToolTip(help_btn, "Mostrar/Ocultar Referencia de Sintaxis (F1)")

        if on_click_generate_manual:
            c += 1
            manual_btn = tk.Button(
                self, text="📋", font=("Arial", 11),
                command=on_click_generate_manual,
                width=2, cursor="hand2",
                relief="flat", bg="#e8fee8", activebackground="#c5fdc5"
            )
            manual_btn.grid(row=0, column=c, sticky="ew", padx=(4, 0))
            ToolTip(manual_btn, "Generar Manual de Ensamblaje")


class TextEntryFrame(BaseFrame):
    def __init__(
        self,
        parent,
        on_update_callback: Optional[Callable] = None,
        loglevel=logging.INFO,
    ):
        super().__init__(parent, loglevel=loglevel)

        self._on_update_callback = on_update_callback
        self._after_id = None

        # ── Line numbers canvas (column 0) ────────────────────────────────
        self._line_canvas = tk.Canvas(
            self, width=38, bg="#f5f5f5", bd=0, highlightthickness=0, cursor="arrow"
        )
        self._line_canvas.grid(row=0, column=0, sticky="ns")
        # Thin separator line on the right edge of the gutter
        self._line_canvas.bind("<Configure>", lambda _: self._update_line_numbers())

        # ── Vertical scrollbar (column 2) ─────────────────────────────────
        self._v_scroll = tk.Scrollbar(self, orient="vertical")
        self._v_scroll.grid(row=0, column=2, sticky="ns")

        # ── Horizontal scrollbar (row 1, column 1) ────────────────────────
        self._h_scroll = tk.Scrollbar(self, orient="horizontal")
        self._h_scroll.grid(row=1, column=1, sticky="ew")

        # ── Text widget (column 1) ────────────────────────────────────────
        self._text = tk.Text(
            self,
            undo=True,
            autoseparators=True,
            maxundo=-1,
            wrap="none",
            yscrollcommand=self._on_text_vscroll,
            xscrollcommand=self._h_scroll.set,
        )
        self._text.grid(row=0, column=1, sticky="news")
        self._v_scroll.configure(command=self._on_vscroll_cmd)
        self._h_scroll.configure(command=self._text.xview)

        self._text.bind("<Control-l>", self._on_ctrl_l)
        self._text.bind("<KeyRelease>", self._on_key_release)
        # Redo: Ctrl+Y and Ctrl+Shift+Z (Ctrl+Z undo is native with undo=True)
        self._text.bind("<Control-y>", lambda e: self._redo())
        self._text.bind("<Control-Shift-Z>", lambda e: self._redo())
        self._text.tag_config("highlight", background="#FFEB3B")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)  # text column expands

    def _on_text_vscroll(self, *args):
        """Called when text widget scrolls; update scrollbar and line numbers."""
        self._v_scroll.set(*args)
        self._update_line_numbers()

    def _on_vscroll_cmd(self, *args):
        """Called when scrollbar moves; update text and line numbers."""
        self._text.yview(*args)
        self._update_line_numbers()

    def _update_line_numbers(self):
        """Redraw line numbers to match the current visible area."""
        self._line_canvas.delete("all")
        # Draw right-edge separator
        w = self._line_canvas.winfo_width()
        self._line_canvas.create_line(w - 1, 0, w - 1, self._line_canvas.winfo_height(),
                                       fill="#cccccc")
        try:
            i = self._text.index("@0,0")
            while True:
                dline = self._text.dlineinfo(i)
                if dline is None:
                    break
                y = dline[1]
                ln = i.split(".")[0]
                self._line_canvas.create_text(
                    w - 4, y + dline[3] // 2,
                    anchor="e", text=ln,
                    fill="#888888", font=("Consolas", 9),
                )
                i = self._text.index(f"{i}+1line")
                if self._text.compare(i, ">=", "end"):
                    break
        except Exception:
            pass

    def _on_key_release(self, _event):
        self._trigger_update(immediate=False)
        self._update_line_numbers()

    def _on_ctrl_l(self, _event):
        self._trigger_update(immediate=True)
        return "break"

    def _redo(self):
        try:
            self._text.edit_redo()
        except tk.TclError:
            pass

    def associate_callback(self, on_update_callback: Callable):
        self._on_update_callback = on_update_callback

    def _trigger_update(self, immediate=False):
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        if immediate:
            self._fire_callback(silent=False)
        else:
            self._after_id = self.after(700, lambda: self._fire_callback(silent=True))

    def _fire_callback(self, silent=False):
        self._after_id = None
        if self._on_update_callback is not None:
            try:
                self._on_update_callback(silent=silent)
            except TypeError:
                self._on_update_callback()

    def _updated(self):
        self._fire_callback(silent=False)

    def get(self):
        return self._text.get("1.0", "end")

    def load(self, text: str):
        """Load fresh content (e.g. from file). Clears the undo history."""
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._text.delete("1.0", "end")
        self._text.insert("1.0", text)
        self._text.edit_reset()
        self.after(10, self._update_line_numbers)

    def replace(self, text: str):
        """Replace all content as a single undo-able operation (for programmatic updates)."""
        if self._after_id is not None:
            self.after_cancel(self._after_id)
            self._after_id = None
        self._text.config(autoseparators=False)
        self._text.edit_separator()
        self._text.delete("1.0", "end")
        self._text.insert("1.0", text)
        self._text.edit_separator()
        self._text.config(autoseparators=True)
        self.after(10, self._update_line_numbers)

    def append(self, text: str):
        self._text.insert("end", text)

    def clear(self):
        self._text.delete("1.0", "end")

    def highlight_line(self, line_number: str):
        self._text.tag_remove("highlight", "0.0", "end")

        if line_number is not None:
            self._text.tag_add("highlight", f"{line_number}.0", f"{line_number}.40")


class HarnessViewFrame(BaseFrame):
    def __init__(self, parent, loglevel=logging.INFO):
        super().__init__(parent, loglevel=loglevel)

        # Configure grid for canvas and scrollbars
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._canvas = tk.Canvas(self, bg="white")
        self._canvas.grid(row=0, column=0, sticky="news")

        self._v_scroll = tk.Scrollbar(
            self, orient="vertical", command=self._canvas.yview
        )
        self._v_scroll.grid(row=0, column=1, sticky="ns")

        self._h_scroll = tk.Scrollbar(
            self, orient="horizontal", command=self._canvas.xview
        )
        self._h_scroll.grid(row=1, column=0, sticky="ew")

        self._canvas.configure(
            yscrollcommand=self._v_scroll.set, xscrollcommand=self._h_scroll.set
        )

        self._image = None
        self._tk_image = None
        self._scale = 1.0

        # Bindings for Pan and Zoom
        self._canvas.bind("<ButtonPress-1>", self._on_move_press)
        self._canvas.bind("<B1-Motion>", self._on_move_drag)
        self._canvas.bind("<MouseWheel>", self._on_zoom)
        self._canvas.bind("<Button-4>", self._on_zoom)
        self._canvas.bind("<Button-5>", self._on_zoom)

    def _on_move_press(self, event):
        self._canvas.scan_mark(event.x, event.y)

    def _on_move_drag(self, event):
        self._canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_zoom(self, event):
        if not self._image:
            return

        if event.num == 4 or event.delta > 0:
            self._scale *= 1.1
        elif event.num == 5 or event.delta < 0:
            self._scale /= 1.1

        self._redraw()

    def has_image(self):
        return self._image is not None

    def save_image(self, filepath):
        if self._image:
            try:
                self._image.save(filepath)
            except Exception as e:
                self._logger.error(f"Error saving image: {e}")
                showerror("Save Error", f"Could not save image:\n{e}")

    def update_image(self, png_data):
        if not png_data:
            return

        try:
            self._image = Image.open(BytesIO(png_data))
            self._scale = 1.0
            self._redraw()
        except Exception as e:
            self._logger.error(f"Error loading image: {e}")
            from tkinter.messagebox import showerror

            showerror(
                "Graph Creation Error",
                f"There was an error parsing the last request: {e}",
            )

    def _redraw(self):
        if not self._image:
            return

        w, h = self._image.size
        new_w = int(w * self._scale)
        new_h = int(h * self._scale)

        if new_w <= 0 or new_h <= 0:
            return

        try:
            resample = Image.Resampling.LANCZOS
        except AttributeError:
            resample = Image.ANTIALIAS

        resized = self._image.resize((new_w, new_h), resample)
        self._tk_image = ImageTk.PhotoImage(resized)

        self._canvas.delete("all")
        self._canvas.create_image(0, 0, image=self._tk_image, anchor="nw")
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    Application()
