import logging
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.messagebox import showerror
from typing import Callable, Optional

from wireviz.wireviz import Harness

from wireviz_gui._base import BaseFrame, HeadLabel, NormButton, NormLabel


class AddMateDialog(BaseFrame):
    def __init__(
        self,
        parent,
        harness: Harness,
        on_save_callback: Optional[Callable] = None,
        get_yaml_text: Optional[Callable] = None,
        loglevel=logging.INFO,
    ):
        super().__init__(parent, loglevel=loglevel)

        self._harness = harness
        self._on_save_callback = on_save_callback
        self._get_yaml_text = get_yaml_text

        r = 0
        HeadLabel(
            self,
            text="Conectar pines",
        ).grid(row=r, column=0, columnspan=2, sticky="ew")

        r += 1
        NormLabel(
            self,
            text="Desde:",
        ).grid(row=r, column=0, sticky="e")
        connectors = self._read_connectors()
        self._from_connector_cb = ttk.Combobox(self, values=connectors)
        self._from_connector_cb.grid(row=r, column=1, sticky="ew")
        if connectors:
            self._from_connector_cb.set(connectors[0])

        r += 1
        NormLabel(
            self,
            text="Hasta:",
        ).grid(row=r, column=0, sticky="e")
        self._to_connector_cb = ttk.Combobox(self, values=connectors)
        self._to_connector_cb.grid(row=r, column=1, sticky="ew")
        if connectors:
            self._to_connector_cb.set(connectors[-1] if len(connectors) > 1 else connectors[0])

        r += 1
        self._arrow_type_var = tk.StringVar(value="double")
        tk.Radiobutton(
            self,
            text="Conector completo (==>)",
            variable=self._arrow_type_var,
            value="double",
            command=self._update_arrow_directions,
        ).grid(row=r, column=0, sticky="w")
        tk.Radiobutton(
            self,
            text="Pin a pin (-->)",
            variable=self._arrow_type_var,
            value="single",
            command=self._update_arrow_directions,
        ).grid(row=r, column=1, sticky="w")

        r += 1
        self._arrow_direction_var = tk.StringVar(value="==>")
        self._arrow_direction_frame = tk.Frame(self)
        self._arrow_direction_frame.grid(row=r, column=0, columnspan=2, sticky="ew")
        self._update_arrow_directions()

        r += 1
        NormButton(
            self,
            text="Guardar conexión",
            command=self._save,
        ).grid(row=r, column=0, columnspan=2, sticky="ew")

    def _update_arrow_directions(self):
        for child in self._arrow_direction_frame.winfo_children():
            child.destroy()

        if self._arrow_type_var.get() == "double":
            directions = ["==>", "<==", "<==>", "=="]
        else:
            directions = ["-->", "<--", "<-->", "--"]

        self._arrow_direction_var.set(directions[0])

        for direction in directions:
            tk.Radiobutton(
                self._arrow_direction_frame,
                text=direction,
                variable=self._arrow_direction_var,
                value=direction,
            ).pack(side="left", expand=True)

    def _read_connectors(self):
        """Read connector names from YAML text (source of truth)."""
        if self._get_yaml_text:
            try:
                import yaml
                data = yaml.safe_load(self._get_yaml_text()) or {}
                if isinstance(data.get("connectors"), dict):
                    return list(data["connectors"].keys())
            except Exception:
                pass
        return list(self._harness.connectors.keys())

    def refresh_dropdowns(self):
        """Re-read connectors from the YAML. Called when the dialog regains focus."""
        connectors = self._read_connectors()
        current_from = self._from_connector_cb.get()
        current_to = self._to_connector_cb.get()
        self._from_connector_cb["values"] = connectors
        self._to_connector_cb["values"] = connectors
        if current_from not in connectors and connectors:
            self._from_connector_cb.set(connectors[0])
        if current_to not in connectors and connectors:
            self._to_connector_cb.set(connectors[-1] if len(connectors) > 1 else connectors[0])

    def _save(self):
        from_connector = self._from_connector_cb.get()
        to_connector = self._to_connector_cb.get()
        arrow = self._arrow_direction_var.get()

        if not from_connector or not to_connector:
            showerror("Error", "Selecciona los conectores de origen y destino.")
            return

        # Return a python list representing the connection: [from, arrow, to]
        # This will be appended to the 'connections' list in the harness data.
        mate_data = [from_connector, arrow, to_connector]

        if self._on_save_callback is not None:
            self._on_save_callback(mate_data)
