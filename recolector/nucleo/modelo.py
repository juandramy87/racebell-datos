"""Formato común de una carrera, igual para todas las fuentes.

Solo se guardan datos de hecho (nombre, fecha, lugar, distancias, precio, plazos y
enlace oficial). Nunca listas de inscritos ni clasificaciones con nombres.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Optional

from nucleo import normalizar as nz

# Estados de la inscripción que ve la app.
NO_ABIERTA = "no_abierta"
ABIERTA = "abierta"
CERRADA = "cerrada"
SIN_INSCRIPCION = "sin_inscripcion"
DESCONOCIDO = "desconocido"

# Calidad del dato.
DE_FUENTE = "fuente"  # lo da la fuente tal cual
DUDOSO = "dudoso"  # algo no cuadra: revisar antes de publicar
PENDIENTE_CARTEL = "pendiente_cartel"  # faltan datos que solo están en el cartel o la normativa


@dataclass
class Fuente:
    id: str  # «dorsalchip», «tecnocrono»…
    url: str  # ficha de la carrera en esa fuente


@dataclass
class Carrera:
    nombre: str
    fecha: date
    fuente: Fuente
    hora: Optional[str] = None  # «HH:MM» o None si no se sabe
    poblacion: Optional[str] = None
    provincia: Optional[str] = None
    comunidad: Optional[str] = None  # se rellena con la de la provincia al publicar
    coords: Optional[tuple[float, float]] = None  # (latitud, longitud) aproximadas
    modalidad: Optional[str] = None  # asfalto, cross, trail, montaña, pista, obstáculos
    distancias_km: list[float] = field(default_factory=list)
    inscripcion_desde: Optional[datetime] = None
    inscripcion_hasta: Optional[datetime] = None
    estado_fuente: Optional[str] = None  # el estado tal como lo da la fuente, ya traducido
    url_inscripcion: Optional[str] = None
    cartel: Optional[str] = None  # enlace a la imagen del cartel en la fuente (no se copia)
    precios: list[dict] = field(default_factory=list)  # [{"nombre": "General", "euros": 11.0}]
    previos: list[str] = field(default_factory=list)
    # Cada aviso es (tipo, texto) con tipo DUDOSO o PENDIENTE_CARTEL. La calidad sale de ellos.
    avisos_calidad: list[tuple[str, str]] = field(default_factory=list)
    otras_fuentes: list[Fuente] = field(default_factory=list)

    def marcar(self, aviso: str, tipo: str = DUDOSO) -> None:
        if (tipo, aviso) not in self.avisos_calidad:
            self.avisos_calidad.append((tipo, aviso))

    def quitar_avisos(self, contiene: str) -> None:
        self.avisos_calidad = [a for a in self.avisos_calidad if contiene.lower() not in a[1].lower()]

    @property
    def calidad(self) -> str:
        tipos = {t for t, _ in self.avisos_calidad}
        return DUDOSO if DUDOSO in tipos else PENDIENTE_CARTEL if tipos else DE_FUENTE

    def estado(self, ahora: datetime) -> str:
        """Estado de la inscripción calculado con la hora actual (no con la del día anterior)."""
        if self.inscripcion_hasta and ahora > self.inscripcion_hasta:
            return CERRADA
        if self.inscripcion_desde and ahora < self.inscripcion_desde:
            return NO_ABIERTA
        if self.inscripcion_hasta:
            return ABIERTA
        return self.estado_fuente or DESCONOCIDO

    def a_dict(self, ahora: datetime) -> dict:
        d = asdict(self)
        d["comunidad"] = nz.comunidad(self.provincia) or self.comunidad
        d["fecha"] = self.fecha.isoformat()
        for clave in ("inscripcion_desde", "inscripcion_hasta"):
            d[clave] = d[clave].isoformat(timespec="minutes") if d[clave] else None
        d["coords"] = list(self.coords) if self.coords else None
        d["estado"] = self.estado(ahora)
        d["calidad"] = self.calidad
        d["avisos_calidad"] = [{"tipo": t, "texto": x} for t, x in self.avisos_calidad]
        d["fuentes"] = [d.pop("fuente")] + d.pop("otras_fuentes")
        return d
