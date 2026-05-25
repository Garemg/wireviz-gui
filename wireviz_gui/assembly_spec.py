"""Data model for cable assembly manufacturing manuals (block-based)."""

from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Block type definitions: {type_name: [(field_key, field_label, widget_type)]}
# widget_type: "entry" | "check" | "textarea"
# ─────────────────────────────────────────────────────────────────────────────
BLOCK_TYPES: dict = OrderedDict([
    ("Corte", [
        ("pn_cable",           "PN Cable",               "entry"),
        ("longitud_mm",        "Longitud total (m)",      "entry"),
        ("programa_cortadora", "Programa cortadora",      "entry"),
        ("notas",              "Notas de corte",          "entry"),
    ]),
    ("Procesado", [
        ("extremo",            "Extremo (A / B / ...)",   "entry"),
        ("funda_mm",           "Desforre funda (mm)",     "entry"),
        ("camisa_mm",          "Desforre camisa (mm)",    "entry"),
        ("seccion_mm2",        "Sección mm²",             "entry"),
        ("awg",                "AWG",                     "entry"),
        ("programa_peladora",  "Programa peladora",       "entry"),
    ]),
    ("Crimpado", [
        ("extremo",                "Extremo (A / B / ...)",      "entry"),
        ("pn_pin",                 "PN Pin / Terminal",           "entry"),
        ("ref_crimpado",           "Molde / Referencia",          "entry"),
        ("parametros",             "Parámetros de crimpado",      "entry"),
        ("programa_crimpadora",    "Programa crimpadora",         "entry"),
        ("crimp_sobre_funda",      "Crimp sobre funda",           "check"),
        ("crimp_sobre_conductores","Crimp sobre conductores",     "check"),
    ]),
    ("Termorretráctil", [
        ("extremo",          "Extremo (A / B / ...)",  "entry"),
        ("texto_label",      "Texto del label",        "entry"),
        ("tamaño_label_mm",  "Tamaño label (mm)",      "entry"),
    ]),
    ("Montaje conector", [
        ("extremo",        "Extremo (A / B / ...)", "entry"),
        ("pn_conector",    "PN Conector",           "entry"),
        ("has_lock",       "Tiene Lock",            "check"),
        ("observaciones",  "Observaciones",         "textarea"),
    ]),
    ("Test", [
        ("tipo_test",         "Tipo de test",       "entry"),
        ("ubicacion_test",    "Ubicación del test", "entry"),
        ("equipo_test",       "Equipo / Adaptador", "entry"),
        ("criterio_aprobado", "Criterio aprobado",  "entry"),
    ]),
    ("Embalaje", [
        ("pn_bolsa",          "PN Bolsa",           "entry"),
        ("tipo_bolsa",        "Tipo de bolsa",      "entry"),
        ("unidades_por_bolsa","Unidades por bolsa", "entry"),
        ("observaciones",     "Observaciones",      "entry"),
    ]),
    ("Personalizado", [
        ("instrucciones", "Instrucciones / Notas", "textarea"),
    ]),
])

BOOL_DEFAULTS: dict = {
    "crimp_sobre_funda":       True,
    "crimp_sobre_conductores": True,
    "has_lock":                False,
}


def default_fields_for(block_type: str) -> dict:
    result: dict = {}
    for key, _label, wtype in BLOCK_TYPES.get(block_type, []):
        result[key] = BOOL_DEFAULTS.get(key, False) if wtype == "check" else ""
    return result


@dataclass
class ManualBlock:
    """One independent step/block in the assembly manual."""
    block_type: str
    title: str
    fields: dict = field(default_factory=dict)
    images: list = field(default_factory=list)   # [{"name": str, "data_uri": str}]


@dataclass
class AssemblyManualSpec:
    """Complete assembly manual specification."""
    referencia: str = ""
    revision: str = "A"
    fecha: str = ""
    autor: str = ""
    blocks: list = field(default_factory=list)

    def numbered_blocks(self) -> list:
        total = len(self.blocks)
        result = []
        for i, block in enumerate(self.blocks):
            result.append({
                "step_number": i + 1,
                "total": total,
                "block_type": block.block_type,
                "title": block.title,
                "fields": block.fields,
                "images": block.images,
            })
        return result


def default_blocks_from_yaml(yaml_text: str) -> list:
    """Auto-generate a sensible default block list from a wireviz YAML string."""
    import yaml as _yaml
    blocks: list = []

    try:
        data = _yaml.safe_load(yaml_text) or {}
    except Exception:
        data = {}

    cables = list((data.get("cables") or {}).keys())
    connectors = list((data.get("connectors") or {}).keys())

    pn_cable = cables[0] if cables else ""
    blocks.append(ManualBlock(
        block_type="Corte",
        title="Corte del cable",
        fields={**default_fields_for("Corte"), "pn_cable": pn_cable},
    ))

    end_names = ["Extremo A", "Extremo B"]
    for i, end in enumerate(end_names):
        connector = connectors[i] if i < len(connectors) else ""
        blocks.append(ManualBlock(
            block_type="Procesado",
            title=f"Procesado {end}",
            fields={**default_fields_for("Procesado"), "extremo": end},
        ))
        blocks.append(ManualBlock(
            block_type="Termorretráctil",
            title=f"Termorretráctil {end}",
            fields={**default_fields_for("Termorretráctil"), "extremo": end},
        ))
        blocks.append(ManualBlock(
            block_type="Crimpado",
            title=f"Crimpado terminales {end}",
            fields={**default_fields_for("Crimpado"), "extremo": end},
        ))
        blocks.append(ManualBlock(
            block_type="Montaje conector",
            title=f"Montaje conector {end}",
            fields={**default_fields_for("Montaje conector"), "extremo": end, "pn_conector": connector},
        ))

    blocks.append(ManualBlock(block_type="Test", title="Test de funcionamiento", fields=default_fields_for("Test")))
    blocks.append(ManualBlock(block_type="Embalaje", title="Embalaje", fields=default_fields_for("Embalaje")))
    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# Serialization: save / load  (.wam – Wireviz Assembly Manual, JSON format)
# ─────────────────────────────────────────────────────────────────────────────

def spec_to_dict(spec: "AssemblyManualSpec") -> dict:
    return {
        "referencia": spec.referencia,
        "revision": spec.revision,
        "fecha": spec.fecha,
        "autor": spec.autor,
        "blocks": [
            {
                "block_type": b.block_type,
                "title": b.title,
                "fields": b.fields,
                "images": b.images,
            }
            for b in spec.blocks
        ],
    }


_BLOCK_TYPE_MIGRATIONS = {
    "Trazabilidad": "Termorretráctil",
}


def spec_from_dict(data: dict) -> "AssemblyManualSpec":
    blocks = []
    for b in data.get("blocks", []):
        btype = _BLOCK_TYPE_MIGRATIONS.get(b["block_type"], b["block_type"])
        blocks.append(ManualBlock(
            block_type=btype,
            title=b.get("title", btype),
            fields=b.get("fields", {}),
            images=b.get("images", []),
        ))
    return AssemblyManualSpec(
        referencia=data.get("referencia", ""),
        revision=data.get("revision", "A"),
        fecha=data.get("fecha", ""),
        autor=data.get("autor", ""),
        blocks=blocks,
    )


def save_spec(spec: "AssemblyManualSpec", path: str) -> None:
    """Save an AssemblyManualSpec to a .wam (JSON) file.
    Images are stored as data URIs so the file is fully self-contained."""
    import json
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(spec_to_dict(spec), fh, ensure_ascii=False, indent=2)


def load_spec(path: str) -> "AssemblyManualSpec":
    """Load an AssemblyManualSpec from a .wam (JSON) file."""
    import json
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return spec_from_dict(data)
