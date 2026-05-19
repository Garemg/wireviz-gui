"""Dialog for filling assembly manual parameters per connector end."""

import logging
import tkinter as tk
import tkinter.ttk as ttk
from tkinter.messagebox import showerror, showinfo
from typing import Callable, Optional

import yaml

from wireviz_gui._base import BaseFrame, HeadLabel, NormButton, NormLabel, ToplevelBase
from wireviz_gui.assembly_spec import (
    AssemblyManualSpec,
    ConnectorAssemblySpec,
    CrimpingSpec,
    CuttingSpec,
    EndSpec,
    FinishSpec,
    PackagingSpec,
    StrippingSpec,
    TestSpec,
    TraceabilitySpec,
)


class _LabeledEntry(tk.Frame):
    """A label + entry pair on a single row."""

    def __init__(self, parent, label_text, default="", width=20, **kwargs):
        super().__init__(parent, **kwargs)
        tk.Label(self, text=label_text, font=("Arial", 10), anchor="e", width=28).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        self._var = tk.StringVar(value=default)
        self._entry = tk.Entry(self, textvariable=self._var, width=width)
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def get(self) -> str:
        return self._var.get().strip()

    def set(self, value: str):
        self._var.set(value)


class _LabeledCheck(tk.Frame):
    """A label + checkbox pair."""

    def __init__(self, parent, label_text, default=False, **kwargs):
        super().__init__(parent, **kwargs)
        self._var = tk.BooleanVar(value=default)
        tk.Checkbutton(self, text=label_text, variable=self._var, font=("Arial", 10)).pack(
            side=tk.LEFT
        )

    def get(self) -> bool:
        return self._var.get()

    def set(self, value: bool):
        self._var.set(value)


class _SectionHeader(tk.Label):
    """Bold section header."""

    def __init__(self, parent, text, **kwargs):
        super().__init__(parent, text=text, font=("Arial", 11, "bold"), anchor="w", **kwargs)


class EndFormFrame(tk.LabelFrame):
    """Form for one cable end (Extremo A, B, etc.)."""

    def __init__(self, parent, end_name="Extremo A", connector_names=None, **kwargs):
        super().__init__(parent, text=end_name, font=("Arial", 12, "bold"), **kwargs)
        self._end_name = end_name
        connector_names = connector_names or []

        row = 0

        # Connector selection
        _SectionHeader(self, text="Conector").grid(row=row, column=0, columnspan=2, sticky="w", pady=(4, 0))
        row += 1
        tk.Label(self, text="Conector asignado:", font=("Arial", 10)).grid(row=row, column=0, sticky="e")
        self._connector_cb = ttk.Combobox(self, values=connector_names, width=25)
        self._connector_cb.grid(row=row, column=1, sticky="w", padx=4, pady=2)
        if connector_names:
            self._connector_cb.set(connector_names[0])
        row += 1

        # Stripping section
        _SectionHeader(self, text="Pelado / Procesado").grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1
        self._desforre_funda = _LabeledEntry(self, "Desforre funda exterior (mm):")
        self._desforre_funda.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._desforre_camisa = _LabeledEntry(self, "Desforre camisa hilos (mm):")
        self._desforre_camisa.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._seccion_mm2 = _LabeledEntry(self, "Sección (mm²):")
        self._seccion_mm2.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._awg = _LabeledEntry(self, "AWG:")
        self._awg.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._prog_peladora = _LabeledEntry(self, "Programa peladora:")
        self._prog_peladora.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1

        # Crimping section
        _SectionHeader(self, text="Crimpado").grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1
        self._pn_pin = _LabeledEntry(self, "PN Pin / Terminal:")
        self._pn_pin.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._ref_crimpado = _LabeledEntry(self, "Referencia crimpado (molde):")
        self._ref_crimpado.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._params_crimpado = _LabeledEntry(self, "Parámetros crimpado:")
        self._params_crimpado.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._prog_crimpadora = _LabeledEntry(self, "Programa crimpadora:")
        self._prog_crimpadora.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._crimp_funda = _LabeledCheck(self, "Crimp sobre funda", default=True)
        self._crimp_funda.grid(row=row, column=0, sticky="w", padx=4)
        self._crimp_conductores = _LabeledCheck(self, "Crimp sobre conductores", default=True)
        self._crimp_conductores.grid(row=row, column=1, sticky="w", padx=4)
        row += 1

        # Finish section
        _SectionHeader(self, text="Acabado").grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1
        self._punteras = _LabeledCheck(self, "Punteras")
        self._punteras.grid(row=row, column=0, sticky="w", padx=4)
        row += 1
        self._pn_punteras = _LabeledEntry(self, "PN Punteras:")
        self._pn_punteras.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._termoretractil = _LabeledCheck(self, "Termorretráctil")
        self._termoretractil.grid(row=row, column=0, sticky="w", padx=4)
        row += 1
        self._pn_termoretractil = _LabeledEntry(self, "PN Termorretráctil:")
        self._pn_termoretractil.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._prestanado = _LabeledCheck(self, "Prestañado")
        self._prestanado.grid(row=row, column=0, sticky="w", padx=4)
        row += 1

        # Traceability section
        _SectionHeader(self, text="Trazabilidad").grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1
        self._trazabilidad = _LabeledCheck(self, "Tiene trazabilidad")
        self._trazabilidad.grid(row=row, column=0, sticky="w", padx=4)
        row += 1
        self._texto_trazabilidad = _LabeledEntry(self, "Texto trazabilidad:")
        self._texto_trazabilidad.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._label_size = _LabeledEntry(self, "Tamaño label (mm):", default="24")
        self._label_size.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1

        # Connector assembly
        _SectionHeader(self, text="Montaje conector").grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 0))
        row += 1
        self._pn_conector = _LabeledEntry(self, "PN Conector:")
        self._pn_conector.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)
        row += 1
        self._has_lock = _LabeledCheck(self, "Conector tiene Lock")
        self._has_lock.grid(row=row, column=0, sticky="w", padx=4)
        row += 1
        self._observaciones = _LabeledEntry(self, "Observaciones:")
        self._observaciones.grid(row=row, column=0, columnspan=2, sticky="ew", padx=4, pady=1)

    def get_end_spec(self) -> EndSpec:
        """Collect all form data into an EndSpec."""
        return EndSpec(
            nombre=self._end_name,
            stripping=StrippingSpec(
                longitud_desforre_funda_mm=_safe_float(self._desforre_funda.get()),
                longitud_desforre_camisa_mm=_safe_float(self._desforre_camisa.get()),
                seccion_mm2=_safe_float(self._seccion_mm2.get()),
                awg=self._awg.get(),
                programa_peladora=self._prog_peladora.get(),
            ),
            crimping=CrimpingSpec(
                pn_pin=self._pn_pin.get(),
                ref_crimpado=self._ref_crimpado.get(),
                parametros_crimpado=self._params_crimpado.get(),
                programa_crimpadora=self._prog_crimpadora.get(),
                crimp_sobre_funda=self._crimp_funda.get(),
                crimp_sobre_conductores=self._crimp_conductores.get(),
            ),
            finish=FinishSpec(
                punteras=self._punteras.get(),
                pn_punteras=self._pn_punteras.get(),
                termoretractil=self._termoretractil.get(),
                pn_termoretractil=self._pn_termoretractil.get(),
                prestanado=self._prestanado.get(),
                acabado_nada=not (self._punteras.get() or self._termoretractil.get() or self._prestanado.get()),
            ),
            traceability=TraceabilitySpec(
                enabled=self._trazabilidad.get(),
                texto=self._texto_trazabilidad.get(),
                tamaño_label_mm=_safe_float(self._label_size.get(), 24.0),
            ),
            connector=ConnectorAssemblySpec(
                pn_conector=self._pn_conector.get(),
                has_lock=self._has_lock.get(),
                observaciones=self._observaciones.get(),
            ),
        )


class AssemblyManualDialog(ToplevelBase):
    """Main dialog for creating an assembly manual from wireviz data."""

    def __init__(
        self,
        parent,
        yaml_text: str = "",
        on_generate_callback: Optional[Callable] = None,
        loglevel=logging.INFO,
    ):
        super().__init__(parent, loglevel=loglevel)
        self.title("Generar Manual de Ensamblaje")
        self.geometry("750x800")

        self._yaml_text = yaml_text
        self._on_generate = on_generate_callback
        self._connector_names = self._extract_connectors()
        self._cable_names = self._extract_cables()

        # Scrollable canvas
        self._canvas = tk.Canvas(self)
        self._scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self._scroll_frame = tk.Frame(self._canvas)

        self._scroll_frame.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.create_window((0, 0), window=self._scroll_frame, anchor="nw")
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mousewheel
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self._build_form()

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def _extract_connectors(self) -> list:
        try:
            data = yaml.safe_load(self._yaml_text) or {}
            connectors = data.get("connectors", {})
            return list(connectors.keys()) if isinstance(connectors, dict) else []
        except Exception:
            return []

    def _extract_cables(self) -> list:
        try:
            data = yaml.safe_load(self._yaml_text) or {}
            cables = data.get("cables", {})
            return list(cables.keys()) if isinstance(cables, dict) else []
        except Exception:
            return []

    def _build_form(self):
        f = self._scroll_frame
        row = 0

        # --- Header section ---
        _SectionHeader(f, text="Datos Generales").grid(row=row, column=0, columnspan=2, sticky="w", pady=(8, 4), padx=8)
        row += 1
        self._referencia = _LabeledEntry(f, "Referencia cable (PN):")
        self._referencia.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1
        self._revision = _LabeledEntry(f, "Revisión:", default="A")
        self._revision.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1
        self._autor = _LabeledEntry(f, "Autor:")
        self._autor.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1

        # --- Cutting section ---
        _SectionHeader(f, text="Corte de Cable").grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 4), padx=8)
        row += 1
        self._pn_cable = _LabeledEntry(f, "PN del cable:")
        self._pn_cable.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1
        self._longitud_total = _LabeledEntry(f, "Longitud total (mm):")
        self._longitud_total.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1
        self._prog_cortadora = _LabeledEntry(f, "Programa cortadora:")
        self._prog_cortadora.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1
        self._notas_corte = _LabeledEntry(f, "Notas de corte:")
        self._notas_corte.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1

        # --- End forms ---
        self._end_frames = []
        end_names = ["Extremo A", "Extremo B"]

        for i, name in enumerate(end_names):
            end_frame = EndFormFrame(f, end_name=name, connector_names=self._connector_names)
            end_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=8)
            self._end_frames.append(end_frame)
            row += 1

        # --- Test section ---
        _SectionHeader(f, text="Test de Funcionamiento").grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 4), padx=8)
        row += 1
        self._tipo_test = _LabeledEntry(f, "Tipo de test:")
        self._tipo_test.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1
        self._ubicacion_test = _LabeledEntry(f, "Ubicación del test:")
        self._ubicacion_test.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1
        self._equipo_test = _LabeledEntry(f, "Equipo de test:")
        self._equipo_test.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1
        self._criterio_test = _LabeledEntry(f, "Criterio aprobado:")
        self._criterio_test.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1

        # --- Packaging section ---
        _SectionHeader(f, text="Embalaje").grid(row=row, column=0, columnspan=2, sticky="w", pady=(12, 4), padx=8)
        row += 1
        self._pn_bolsa = _LabeledEntry(f, "PN Bolsa:")
        self._pn_bolsa.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1
        self._tipo_bolsa = _LabeledEntry(f, "Tipo de bolsa:")
        self._tipo_bolsa.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1
        self._unidades_bolsa = _LabeledEntry(f, "Unidades por bolsa:", default="1")
        self._unidades_bolsa.grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=1)
        row += 1

        # --- Generate button ---
        tk.Frame(f, height=16).grid(row=row, column=0)
        row += 1
        NormButton(
            f,
            text="Generar Manual PDF",
            command=self._generate,
        ).grid(row=row, column=0, columnspan=2, sticky="ew", padx=8, pady=8)

    def _generate(self):
        """Collect all data and call the generate callback."""
        from datetime import date

        spec = AssemblyManualSpec(
            referencia=self._referencia.get(),
            revision=self._revision.get(),
            fecha=date.today().isoformat(),
            autor=self._autor.get(),
            cutting=CuttingSpec(
                pn_cable=self._pn_cable.get(),
                longitud_total_mm=_safe_float(self._longitud_total.get()),
                programa_cortadora=self._prog_cortadora.get(),
                notas_corte=self._notas_corte.get(),
            ),
            ends=[ef.get_end_spec() for ef in self._end_frames],
            test=TestSpec(
                tipo_test=self._tipo_test.get(),
                ubicacion_test=self._ubicacion_test.get(),
                equipo_test=self._equipo_test.get(),
                criterio_aprobado=self._criterio_test.get(),
            ),
            packaging=PackagingSpec(
                pn_bolsa=self._pn_bolsa.get(),
                tipo_bolsa=self._tipo_bolsa.get(),
                unidades_por_bolsa=int(_safe_float(self._unidades_bolsa.get(), 1)),
            ),
        )

        # Validate required fields
        errors = []
        if not spec.referencia:
            errors.append("Referencia cable (PN) es obligatorio")
        if not spec.cutting.pn_cable:
            errors.append("PN del cable es obligatorio")
        if spec.cutting.longitud_total_mm <= 0:
            errors.append("Longitud total debe ser > 0")
        if not spec.cutting.programa_cortadora:
            errors.append("Programa cortadora es obligatorio")

        if errors:
            showerror("Campos obligatorios", "\n".join(errors))
            return

        if self._on_generate:
            self._on_generate(spec)
        self.destroy()


def _safe_float(value: str, default: float = 0.0) -> float:
    """Parse a float from string, returning default on failure."""
    try:
        return float(value.replace(",", "."))
    except (ValueError, AttributeError):
        return default
