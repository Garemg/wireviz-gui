"""
Syntax reference window for WireViz-GUI.
Shows a searchable, tabbed reference of the WireViz YAML syntax.
"""
import tkinter as tk
import tkinter.ttk as ttk

from wireviz_gui._base import BaseFrame, ToplevelBase

# ---------------------------------------------------------------------------
# Content definitions
# ---------------------------------------------------------------------------

_SECTIONS = {
    "Estructura": """\
# ESTRUCTURA PRINCIPAL DEL ARCHIVO YAML
# ─────────────────────────────────────

connectors:          # Diccionario de conectores
  <nombre>:
    ...              # Atributos del conector

cables:              # Diccionario de cables / hilos
  <nombre>:
    ...              # Atributos del cable

connections:         # Lista de conexiones entre componentes
  -
    - <conector>: <pin>
    - <cable>:    <hilo>
    - <conector>: <pin>

additional_bom_items:  # Elementos adicionales en el BOM
  - description: <str>
    qty: <int/float>
    pn: <str>

metadata:            # Información descriptiva del arnés
  title: <str>
  description: <str>
  notes: <str>

options:             # Opciones globales del diagrama
  bgcolor: WH
  fontname: arial
  color_mode: SHORT

tweak:               # Ajuste experimental del .gv generado
  override:
    <str>: { <attr>: <valor> }
  append: <str>
""",

    "Conectores": """\
# ATRIBUTOS DE CONECTOR
# ─────────────────────

<nombre>:
  # ── Información general (todo opcional) ──────────
  type: <str>              # Tipo de conector (p.ej. "Molex KK 254")
  subtype: <str>           # Subtipo (p.ej. "female")
  color: <color>           # Color de fondo (ver sección Colores)
  image:
    src: <ruta>            # Ruta a imagen PNG/JPG
    caption: <str>         # Texto debajo de la imagen
    width: <int>           # Ancho en puntos (1-65535)
    height: <int>          # Alto en puntos  (1-65535)
  notes: <str>             # Notas (admite multilínea con |)

  # ── Información de producto (todo opcional) ──────
  ignore_in_bom: false     # true → no añadir al BOM
  pn: <str>                # Número de pieza interno
  manufacturer: <str>      # Fabricante
  mpn: <str>               # Número de pieza del fabricante
  supplier: <str>          # Proveedor
  spn: <str>               # Número de pieza del proveedor
  additional_components:
    - type: <str>
      subtype: <str>
      qty: 1
      qty_multiplier: pincount  # pincount | populated | unpopulated
      pn: <str>

  # ── Información de pines ──────────────────────────
  # Al menos uno de los siguientes es obligatorio:
  pincount: <int>          # Número de pines (auto si se especifica lista)
  pins: [1, 2, 3, ...]    # IDs de pines (por defecto 1,2,...,N)
  pinlabels: [GND, 5V, SIG]  # Etiquetas de pines
  pincolors: [BK, RD, GN]    # Colores por pin (ver sección Colores)

  # ── Cortocircuitos internos (loops) ──────────────
  loops:
    - [1, 2]               # Pines a cortocircuitar (lista de pares)

  # ── Visualización (todo opcional) ────────────────
  bgcolor: <color>
  bgcolor_title: <color>
  style: simple            # "simple" → conector de un solo pin sin recuadro
  show_name: true          # false por defecto en conectores "simple"
  show_pincount: true      # false por defecto en conectores "simple"
  hide_disconnected_pins: false


# ── EJEMPLO ───────────────────────────────────────
connectors:
  X1:
    type: D-Sub
    subtype: female
    pinlabels: [DCD, RX, TX, DTR, GND, DSR, RTS, CTS, RI]
    image:
      src: dsub9.png
      caption: DB-9 Female
""",

    "Cables": """\
# ATRIBUTOS DE CABLE / HILO
# ─────────────────────────

<nombre>:
  # ── Información general (todo opcional) ──────────
  category: bundle         # "bundle" → ítem BOM por hilo; borde discontinuo
  type: <str>
  gauge: 0.25 mm2          # Formatos: "0.25 mm2" | "22 AWG" | 0.25 (=mm2)
  show_equiv: false        # true → muestra conversión mm2 ↔ AWG
  length: 0.5              # En metros por defecto; admite "2.5 ft"
  shield: false            # true | <color> → muestra pantalla; acceder con "s"
  color: <color>
  image:
    src: <ruta>
    caption: <str>
  notes: <str>

  # ── Información de producto (todo opcional) ──────
  ignore_in_bom: false
  pn: <str>
  manufacturer: <str>
  mpn: <str>
  supplier: <str>
  spn: <str>
  additional_components:
    - type: <str>
      qty: 1
      qty_multiplier: wirecount  # wirecount | terminations | length | total_length

  # ── Conductores (una de las siguientes combinaciones)
  # ┌─────────────────────────────────────────────────┐
  # │ wirecount solo    → sin info de color            │
  # │ colors solo       → wirecount inferido de lista  │
  # │ wirecount+color_code → colores auto por código   │
  # │ wirecount+colors  → lista recortada/repetida     │
  # └─────────────────────────────────────────────────┘
  wirecount: <int>
  colors: [BK, RD, GN, YE]   # Lista de colores (ver sección Colores)
  color_code: DIN             # DIN | IEC | T568A | T568B | TEL | TELALT | BW
  wirelabels: [GND, 5V, SIG, +12V]  # Etiqueta por hilo (opcional)

  # ── Visualización (todo opcional) ────────────────
  bgcolor: <color>
  bgcolor_title: <color>
  show_name: true
  show_wirecount: true
  show_wirenumbers: true      # false por defecto en bundles


# ── EJEMPLO ───────────────────────────────────────
cables:
  W1:
    gauge: 0.25 mm2
    length: 0.2
    color_code: DIN
    wirecount: 3
    shield: true
""",

    "Conexiones": """\
# CONEXIONES — SINTAXIS COMPLETA
# ────────────────────────────────

# Una "connection set" es una lista de componentes alternando
# conectores y cables. Se añade como elemento de la lista "connections:".

# ── CONEXIÓN SIMPLE ───────────────────────────────
connections:
  -
    - X1: 1           # Conector X1, pin 1
    - W1: 1           # Cable W1, hilo 1
    - X2: 1           # Conector X2, pin 1

  -
    - X1: GND         # Pin referenciado por etiqueta (si es única)
    - W1: s           # Hilo especial: pantalla (shield)
    - X2              # Conector simple → pin 1 implícito


# ── CONEXIONES PARALELAS ──────────────────────────
connections:
  -
    - X1: [1, 2, 3]          # Múltiples pines
    - W1: [1, 2, 3]          # Múltiples hilos
    - X2: [1, 2, 3]

  -
    - X1: [1-4]              # Rango → expande a 1,2,3,4
    - W1: [1-4]
    - X2: [4-1]              # Rango inverso: 4,3,2,1

  -
    - X1: [1, GND, 3-5]     # Mezcla: número, etiqueta, rango


# ── FLECHAS ENTRE PINES (mating pin-to-pin) ──────
connections:
  -
    - X1: [1, 2, 3]
    - [--, -->, <--]         # Flecha individual por conexión
    - X2: [1, 2, 3]


# ── FLECHAS ENTRE CONECTORES (mating completo) ───
connections:
  -
    - X1              # Conector completo
    - ==>             # Una sola flecha doble
    - X2
  # Tipos de flecha doble: == | <== | <==> | ==>
  # Tipos de flecha simple: -- | <-- | <--> | -->


# ── AUTOGENERACIÓN DE INSTANCIAS ─────────────────
# Usando "." (o template_separator definido en options)
connections:
  -
    - Y.Y1: [1, 2]   # Template Y → instancia con nombre Y1
    - W.W1: [1, 2]
  -
    - Y.Y2: [1, 2]   # Otra instancia del mismo template
    - W.W2: [1, 2]
  -
    - Z.             # Instancia sin nombre (solo útil para terminales simples)
    - W.


# ── COMPONENTE NO CONECTADO (para que aparezca en el diagrama)
connections:
  -
    - X1             # Mínima connection set para incluir componente
""",

    "Colores": """\
# COLORES — CÓDIGOS DE DOS LETRAS (IEC 60757)
# ─────────────────────────────────────────────

BK  negro     (black)      #000000
WH  blanco    (white)      #ffffff
GY  gris      (grey)       #999999
PK  rosa      (pink)       #ff66cc
RD  rojo      (red)        #ff0000
OG  naranja   (orange)     #ff8000
YE  amarillo  (yellow)     #ffff00
OL  verde oliva            #708000
GN  verde     (green)      #00ff00
TQ  turquesa  (turquoise)  #00ffff
LB  azul claro (light blue) #a0dfff
BU  azul      (blue)       #0066ff
VT  violeta   (violet)     #8000ff
BN  marrón    (brown)      #895956
BG  beige                  #ceb673
IV  marfil    (ivory)      #f5f0d0
SL  pizarra   (slate)      #708090
CU  cobre     (copper)     #d6775e
SN  estaño    (tin)        #aaaaaa
SR  plata     (silver)     #84878c
GD  oro       (gold)       #ffcf80

# COLORES COMBINADOS (bicolor / rayas)
# Concatenar sin espacio: GNYE = verde-amarillo
# Ejemplos: BKWH, RDWH, BKRD, GNYE, BUWH

# HEXADECIMAL (también aceptado)
# color: "#FF0000"          (rojo en hex)
# color: "#FF0000:#00FF00"  (bicolor hex)
# NOTA: Los strings con '#' deben ir entre comillas en YAML.


# CÓDIGOS DE COLOR PARA CABLES (color_code)
# ──────────────────────────────────────────
DIN      → DIN 47100   (WH, BN, GN, YE, GY, PK, BU, RD, BK, VT, ...)
IEC      → IEC 60757   (BN, RD, OG, YE, GN, BU, VT, GY, WH, BK, ...)
T568A    → TIA/EIA 568A (Ethernet CAT5/6)
T568B    → TIA/EIA 568B (Ethernet CAT5/6 - más común)
TEL      → 25-pair color code
TELALT   → 25-pair color code alternativo
BW       → Blanco y negro alternos
""",

    "Options / Meta": """\
# METADATA — Información del documento
# ─────────────────────────────────────
metadata:
  title: "Mi Arnés"
  description: "Descripción completa"
  notes: |
    Línea 1 de notas
    Línea 2 de notas


# OPTIONS — Configuración global del diagrama
# ────────────────────────────────────────────
options:
  # Colores de fondo
  bgcolor: WH              # Fondo del diagrama y HTML  (defecto: WH)
  bgcolor_node: WH         # Fondo de nodos             (defecto: WH)
  bgcolor_connector: WH    # Fondo de conectores        (defecto: bgcolor_node)
  bgcolor_cable: WH        # Fondo de cables            (defecto: bgcolor_node)
  bgcolor_bundle: WH       # Fondo de bundles           (defecto: bgcolor_cable)

  # Visualización de colores en el diagrama
  # Valores: full | FULL | hex | HEX | short | SHORT | ger | GER
  color_mode: SHORT        # (defecto)

  # Fuente del diagrama
  fontname: arial          # (defecto)

  # Modo de BOM compacto
  mini_bom_mode: true      # true → muestra referencia en nodo; false → todo
                           # (defecto: true)

  # Separador para autogeneración de instancias
  template_separator: "."  # (defecto: ".")


# TWEAK — Ajuste experimental del .gv
# ─────────────────────────────────────
tweak:
  override:
    "X1" :                 # Identificador del nodo en el .gv
      color: "#FF0000"     # Nuevo valor del atributo
      fillcolor: null      # null → eliminar atributo
  append: |
    // Contenido extra que se añade al final del .gv
""",

    "Multilínea / Tips": """\
# CADENAS MULTILÍNEA
# ───────────────────

# Método 1 — Pipe (|): cada línea indentada es una línea nueva
notes: |
  Línea 1.
  Línea 2.

# Método 2 — Comillas dobles con \\n
notes: "Línea 1.\\nLínea 2."

# Las comillas simples NO convierten \\n.
# Más info: https://yaml-multiline.info/


# HERENCIA (YAML anchors)
# ────────────────────────
# Define una vez, reutiliza varias veces
connectors:
  &plantilla_dt    # Definir ancla
  DT_TEMPLATE:
    type: Deutsch DT
    subtype: female
    pincount: 4

  X1:
    <<: *plantilla_dt   # Fusionar plantilla
    notes: Conector A

  X2:
    <<: *plantilla_dt   # Misma plantilla
    notes: Conector B


# CONSEJOS DE USO
# ────────────────
# • Los componentes deben estar en connections: para aparecer en el diagrama.
#   Si están en connectors:/cables: pero no en connections:, aparece un warning.
# • Para componente no conectado, añadir connection set mínima:
#     connections:
#       - [X_standalone]
# • El escudo de un cable se accede como wire "s":
#     - W1: s
# • Los pines se pueden referenciar por número (1,2,3...) o por etiqueta
#   (si pinlabels está definido y la etiqueta es única).
# • Ctrl+L refresca el diagrama manualmente.
# • Ctrl+Z deshace cambios en el editor YAML.
""",
}


# ---------------------------------------------------------------------------
# Reusable panel (embeddable in any container)
# ---------------------------------------------------------------------------

class SyntaxReferencePanel(BaseFrame):
    """Embeddable panel with the full WireViz syntax reference.

    Can be parented to a Toplevel, a ttk.PanedWindow, or any Frame.
    """

    def __init__(self, parent, compact=False):
        """
        Args:
            parent: tkinter parent widget.
            compact: if True, use a smaller font and less padding (for side panel).
        """
        import logging
        super().__init__(parent, loglevel=logging.INFO)
        self.configure(bg="#f0f0f0")
        self._compact = compact

        # ── Search bar ────────────────────────────────────────────────────
        search_frame = tk.Frame(self, bg="#f0f0f0", pady=3)
        search_frame.pack(fill="x", padx=6, pady=(6, 0))

        tk.Label(search_frame, text="🔍", bg="#f0f0f0",
                 font=("Arial", 9)).pack(side="left", padx=(0, 2))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", self._on_search_change)
        search_entry = tk.Entry(search_frame, textvariable=self._search_var,
                                font=("Arial", 9), width=16)
        search_entry.pack(side="left")
        search_entry.bind("<Return>", lambda _: self._navigate(+1))
        search_entry.bind("<Shift-Return>", lambda _: self._navigate(-1))

        btn_kw = dict(font=("Arial", 9), relief="flat", bg="#f0f0f0",
                      cursor="hand2", padx=2)
        tk.Button(search_frame, text="▲", command=lambda: self._navigate(-1),
                  **btn_kw).pack(side="left", padx=(4, 0))
        tk.Button(search_frame, text="▼", command=lambda: self._navigate(+1),
                  **btn_kw).pack(side="left")

        self._match_label = tk.Label(search_frame, text="", bg="#f0f0f0",
                                     font=("Arial", 8), fg="#666")
        self._match_label.pack(side="left", padx=4)

        tk.Button(search_frame, text="✕", font=("Arial", 8),
                  command=self._clear_search, relief="flat",
                  cursor="hand2").pack(side="left")

        # Internal match index tracking
        self._all_matches: list = []   # [(tab_title, start_index), ...]
        self._match_cursor: int = -1

        # ── Notebook with sections ────────────────────────────────────────
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=4, pady=4)
        self._notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        self._text_widgets = {}
        font_size = 9 if compact else 10

        for title, content in _SECTIONS.items():
            frame = tk.Frame(self._notebook)
            self._notebook.add(frame, text=title)

            scroll_y = tk.Scrollbar(frame, orient="vertical")
            scroll_y.pack(side="right", fill="y")
            scroll_x = tk.Scrollbar(frame, orient="horizontal")
            scroll_x.pack(side="bottom", fill="x")

            text = tk.Text(
                frame,
                font=("Consolas", font_size),
                wrap="none",
                bg="#1e1e1e",
                fg="#d4d4d4",
                insertbackground="white",
                selectbackground="#264f78",
                padx=8, pady=6,
                yscrollcommand=scroll_y.set,
                xscrollcommand=scroll_x.set,
                state="normal",
            )
            text.pack(fill="both", expand=True)
            scroll_y.config(command=text.yview)
            scroll_x.config(command=text.xview)

            # Configure syntax highlight tags
            text.tag_config("comment",           foreground="#6a9955")
            text.tag_config("key",               foreground="#9cdcfe")
            text.tag_config("value",             foreground="#ce9178")
            text.tag_config("section",           foreground="#569cd6",
                            font=("Consolas", font_size, "bold"))
            text.tag_config("highlight",         background="#4d4d00", foreground="#ffd700")
            text.tag_config("highlight_current", background="#ffd700", foreground="#000000")
            text.tag_config("color_code",        foreground="#c586c0")

            self._insert_highlighted(text, content)
            text.config(state="disabled")
            self._text_widgets[title] = text

    # ── Syntax highlighting ────────────────────────────────────────────────

    def _insert_highlighted(self, widget, content):
        """Insert content with basic syntax highlighting."""
        for line in content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                widget.insert("end", line + "\n", "comment")
            elif ":" in stripped and not stripped.startswith("-"):
                colon_pos = line.index(":")
                key_part = line[:colon_pos + 1]
                rest = line[colon_pos + 1:]
                widget.insert("end", key_part, "key")
                widget.insert("end", rest + "\n", "value")
            elif stripped.startswith("- ") or stripped == "-":
                if len(stripped) >= 2 and stripped[2:4].isupper() and stripped[:2].isupper():
                    widget.insert("end", line + "\n", "color_code")
                else:
                    widget.insert("end", line + "\n")
            else:
                widget.insert("end", line + "\n")

    # ── Search ─────────────────────────────────────────────────────────────

    def _on_search_change(self, *_):
        query = self._search_var.get().strip()
        self._all_matches = []
        self._match_cursor = -1

        for title, text_widget in self._text_widgets.items():
            text_widget.config(state="normal")
            text_widget.tag_remove("highlight", "1.0", "end")
            text_widget.tag_remove("highlight_current", "1.0", "end")

            if query:
                start = "1.0"
                while True:
                    pos = text_widget.search(query, start, stopindex="end", nocase=True)
                    if not pos:
                        break
                    end = f"{pos}+{len(query)}c"
                    text_widget.tag_add("highlight", pos, end)
                    self._all_matches.append((title, pos))
                    start = end

            text_widget.config(state="disabled")

        total = len(self._all_matches)
        if total:
            self._match_cursor = 0
            self._jump_to_match(0)
            self._update_match_label()
        else:
            self._match_label.config(text="Sin resultados" if query else "")

    def _navigate(self, direction: int):
        if not self._all_matches:
            return
        self._match_cursor = (self._match_cursor + direction) % len(self._all_matches)
        self._jump_to_match(self._match_cursor)
        self._update_match_label()

    def _jump_to_match(self, idx: int):
        if not self._all_matches:
            return
        query = self._search_var.get().strip()
        title, pos = self._all_matches[idx]

        for i, t in enumerate(_SECTIONS.keys()):
            if t == title:
                self._notebook.select(i)
                break

        widget = self._text_widgets[title]
        widget.config(state="normal")
        widget.tag_remove("highlight_current", "1.0", "end")
        end = f"{pos}+{len(query)}c"
        widget.tag_add("highlight_current", pos, end)
        widget.see(pos)
        widget.config(state="disabled")

    def _update_match_label(self):
        total = len(self._all_matches)
        current = self._match_cursor + 1 if total else 0
        self._match_label.config(text=f"{current}/{total}")

    def _clear_search(self):
        self._search_var.set("")
        self._match_label.config(text="")

    def _on_tab_change(self, _event):
        pass


# ---------------------------------------------------------------------------
# Standalone window (wraps the panel in a Toplevel)
# ---------------------------------------------------------------------------

class SyntaxReferenceWindow(ToplevelBase):
    """Floating window with the full WireViz syntax reference."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Referencia de Sintaxis WireViz")
        self.geometry("800x600")
        self.minsize(600, 400)

        panel = SyntaxReferencePanel(self)
        panel.pack(fill="both", expand=True)

