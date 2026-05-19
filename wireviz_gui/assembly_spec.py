"""Data model for cable assembly manufacturing manuals."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class StrippingSpec:
    """Stripping parameters for one end."""
    longitud_desforre_funda_mm: float = 0.0
    longitud_desforre_camisa_mm: float = 0.0
    seccion_mm2: float = 0.0
    awg: str = ""
    programa_peladora: str = ""


@dataclass
class CrimpingSpec:
    """Crimping parameters for one end."""
    pn_pin: str = ""
    ref_crimpado: str = ""  # Molde / referencia de crimpadora
    parametros_crimpado: str = ""
    programa_crimpadora: str = ""
    crimp_sobre_funda: bool = True
    crimp_sobre_conductores: bool = True


@dataclass
class FinishSpec:
    """Finish/acabado for one end."""
    punteras: bool = False
    pn_punteras: str = ""
    termoretractil: bool = False
    pn_termoretractil: str = ""
    prestanado: bool = False
    acabado_nada: bool = True


@dataclass
class TraceabilitySpec:
    """Traceability label for one end."""
    enabled: bool = False
    texto: str = ""
    tamaño_label_mm: float = 24.0


@dataclass
class ConnectorAssemblySpec:
    """Connector insertion parameters for one end."""
    pn_conector: str = ""
    imagen_conector: str = ""  # path to connector image
    pin_assignments: dict = field(default_factory=dict)  # {pin_number: color}
    has_lock: bool = False
    observaciones: str = ""


@dataclass
class EndSpec:
    """Full specification for one cable end."""
    nombre: str = "Extremo A"
    stripping: StrippingSpec = field(default_factory=StrippingSpec)
    crimping: CrimpingSpec = field(default_factory=CrimpingSpec)
    finish: FinishSpec = field(default_factory=FinishSpec)
    traceability: TraceabilitySpec = field(default_factory=TraceabilitySpec)
    connector: ConnectorAssemblySpec = field(default_factory=ConnectorAssemblySpec)


@dataclass
class CuttingSpec:
    """Cable cutting parameters."""
    pn_cable: str = ""
    longitud_total_mm: float = 0.0
    programa_cortadora: str = ""
    notas_corte: str = ""  # e.g. "Cerrar con cinta de poliéster"


@dataclass
class TestSpec:
    """Functional test parameters."""
    tipo_test: str = ""  # e.g. "Continuidad", "Aislamiento"
    ubicacion_test: str = ""
    equipo_test: str = ""
    adaptador: str = ""
    criterio_aprobado: str = ""


@dataclass
class PackagingSpec:
    """Packaging parameters."""
    pn_bolsa: str = ""
    tipo_bolsa: str = ""  # e.g. "Bolsa opaca con fuelle"
    unidades_por_bolsa: int = 1
    observaciones: str = ""


@dataclass
class AssemblyManualSpec:
    """Complete specification for a cable assembly manual."""
    # Header
    referencia: str = ""  # e.g. "CABLERET-A_ISA_011"
    revision: str = "A"
    fecha: str = ""
    autor: str = ""

    # Cable
    cutting: CuttingSpec = field(default_factory=CuttingSpec)

    # Ends (at least 2: A and B)
    ends: list = field(default_factory=lambda: [
        EndSpec(nombre="Extremo A"),
        EndSpec(nombre="Extremo B"),
    ])

    # Test
    test: TestSpec = field(default_factory=TestSpec)

    # Packaging
    packaging: PackagingSpec = field(default_factory=PackagingSpec)

    def generate_steps(self) -> list:
        """Generate the ordered list of manufacturing steps."""
        steps = []
        step_num = 1

        # Step: Cable cutting
        steps.append({
            "numero": step_num,
            "tipo": "corte",
            "titulo": f"Corte del cable",
            "data": self.cutting,
        })
        step_num += 1

        # Steps per end
        for end in self.ends:
            # Procesado (stripping)
            steps.append({
                "numero": step_num,
                "tipo": "procesado",
                "titulo": f"Procesado {end.nombre}",
                "data": end,
            })
            step_num += 1

            # Crimpado
            steps.append({
                "numero": step_num,
                "tipo": "crimpado",
                "titulo": f"Crimpado terminales {end.nombre}",
                "data": end,
            })
            step_num += 1

            # Trazabilidad (only if enabled)
            if end.traceability.enabled:
                steps.append({
                    "numero": step_num,
                    "tipo": "trazabilidad",
                    "titulo": f"Trazabilidad {end.nombre}",
                    "data": end,
                })
                step_num += 1

            # Montaje conector
            steps.append({
                "numero": step_num,
                "tipo": "montaje_conector",
                "titulo": f"Montaje conector {end.nombre}",
                "data": end,
            })
            step_num += 1

        # Test
        if self.test.tipo_test:
            steps.append({
                "numero": step_num,
                "tipo": "test",
                "titulo": "Test de funcionamiento",
                "data": self.test,
            })
            step_num += 1

        # Packaging
        if self.packaging.pn_bolsa:
            steps.append({
                "numero": step_num,
                "tipo": "packaging",
                "titulo": "Embalaje",
                "data": self.packaging,
            })
            step_num += 1

        # Set total
        total = len(steps)
        for s in steps:
            s["total"] = total

        return steps
