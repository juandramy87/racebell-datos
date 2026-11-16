"""Une la misma carrera cuando aparece en varias fuentes (mismo día, mismo pueblo y nombre
parecido) y completa los huecos de una con los datos de la otra."""
from __future__ import annotations

from nucleo import normalizar as nz
from nucleo.modelo import Carrera

# Cuanto antes en la lista, más fiable es la fuente como base de la ficha.
PRIORIDAD = ["dorsalchip", "tecnocrono", "globaltempo", "sesca", "faa"]

_VACIAS = {
    "carrera", "carreras", "popular", "populares", "de", "del", "la", "las", "el", "los", "y", "en", "a",
    "por", "contra", "edicion", "solidaria", "memorial", "circuito", "provincial", "km", "k", "the",
    # Palabras de tipo de prueba: comunes a muchas carreras distintas, no sirven para identificarlas.
    "san", "silvestre", "cross", "trail", "urbana", "media", "maraton", "cxm", "navidena", "navidad",
    "rural", "fondo", "nocturna", "infantil", "jornada", "senderos", "copa", "liga",
}


def _palabras(texto: str | None) -> set[str]:
    out = set()
    for p in nz.clave(texto).split():
        if p in _VACIAS or p.isdigit() or nz._ROMANO.match(p.upper()) or len(p) < 3:
            continue
        out.add(p)
    return out


def misma_carrera(a: Carrera, b: Carrera) -> bool:
    if a.fecha != b.fecha or a.fuente.id == b.fuente.id:
        return False  # una misma fuente nunca lista dos veces la misma prueba
    pa, pb = _palabras(a.nombre), _palabras(b.nombre)
    if not pa or not pb:
        return False
    comunes = pa & pb
    parecido = len(comunes) / len(pa | pb)
    mismo_pueblo = bool(a.poblacion and b.poblacion and nz.clave(a.poblacion) == nz.clave(b.poblacion))
    if mismo_pueblo and parecido >= 0.25:
        return True
    if parecido >= 0.5:
        return True
    # Nombres cortos (FAA: «Pinares de Cartaya», «Cruz de Velasco»): todas sus palabras están en la otra
    # (en el nombre o en el pueblo).
    corto, largo = (a, b) if len(pa) <= len(pb) else (b, a)
    pc = _palabras(corto.nombre)
    contexto = _palabras(largo.nombre) | _palabras(largo.poblacion)
    return len(pc) >= 1 and pc <= contexto and (len(pc) >= 2 or not corto.poblacion)


def _orden(c: Carrera) -> tuple:
    prioridad = PRIORIDAD.index(c.fuente.id) if c.fuente.id in PRIORIDAD else len(PRIORIDAD)
    # Las anunciadas (apuntadas a mano desde la web oficial) nunca mandan sobre una plataforma.
    return (c.fuente.id == "anunciadas", c.inscripcion_hasta is None, c.poblacion is None, prioridad)


def unir(grupo: list[Carrera]) -> Carrera:
    grupo = sorted(grupo, key=_orden)
    base = grupo[0]
    for otra in grupo[1:]:
        base.otras_fuentes.append(otra.fuente)
        for campo in ("hora", "poblacion", "provincia", "coords", "modalidad", "inscripcion_desde",
                      "inscripcion_hasta", "url_inscripcion", "cartel"):
            if getattr(base, campo) is None and getattr(otra, campo) is not None:
                setattr(base, campo, getattr(otra, campo))
        if not base.precios and otra.precios:
            base.precios = otra.precios
        if not base.distancias_km and otra.distancias_km:
            base.distancias_km = otra.distancias_km
        for p in otra.previos:
            if p not in base.previos:
                base.previos.append(p)
        for tipo, texto in otra.avisos_calidad:
            base.marcar(texto, tipo)
    # Quitar avisos que otra fuente ya ha resuelto.
    if base.inscripcion_hasta:
        base.quitar_avisos("cierre de inscripción")
        base.quitar_avisos("sin fecha de cierre")
    # Sesca no da provincia (se supone Cádiz): si otra fuente la da, manda la otra.
    con_provincia = [x for x in grupo if x.fuente.id != "sesca" and x.provincia]
    if con_provincia:
        base.provincia = con_provincia[0].provincia
        base.quitar_avisos("Provincia supuesta")
    if base.poblacion and base.inscripcion_hasta:
        base.quitar_avisos("Población, precio, cierre y previos solo en el cartel")
        if any(f.id == "faa" for f in [base.fuente, *base.otras_fuentes]) and not base.previos:
            base.marcar("Precio y previos solo en el cartel de la FAA", "pendiente_cartel")
    return base


def deduplicar(carreras: list[Carrera]) -> tuple[list[Carrera], list[str]]:
    """Devuelve las carreras únicas y un registro de lo que se ha unido (para revisarlo)."""
    grupos: list[list[Carrera]] = []
    for c in carreras:
        for g in grupos:
            if any(misma_carrera(c, x) for x in g):
                g.append(c)
                break
        else:
            grupos.append([c])
    unidas, registro = [], []
    for g in grupos:
        if len(g) > 1:
            registro.append(f"{g[0].fecha} · " + " = ".join(f"{x.nombre} [{x.fuente.id}]" for x in g))
        unidas.append(unir(g))
    unidas.sort(key=lambda c: (c.fecha, c.hora or "99:99", c.nombre))
    return unidas, registro
