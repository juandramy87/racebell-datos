"""Ayudas comunes a los lectores de Levante (Comunitat Valenciana y Región de Murcia).

- Nombres en valenciano: «Volta a peu», «Cursa», «Mitja Marató», «Marató», «Camp a través».
  `nz.clasificar` y `nz.distancias_del_nombre` solo conocen las formas en castellano.
- Las webs murcianas dan la población sin provincia; casi todas son de Murcia, pero algunas son de la
  Vega Baja (Alicante) o de Albacete. Sin provincia, `municipios.completar` solo busca en Andalucía.
(Si se pasa a `nucleo/normalizar.py`, este módulo sobra.)"""
from __future__ import annotations

import re
from typing import Optional

from nucleo import normalizar as nz

_ASFALTO_VALENCIANO = re.compile(r"\b(volta a peu|cursa|marato|mitja|10 ?k|5 ?k|sant silvestre|milla)\b")
_CROSS_VALENCIANO = re.compile(r"\b(camp a traves|cros)\b")
_MUNTANYA = re.compile(r"\b(muntanya|vertical|km vertical)\b")


def clasificar(*textos: Optional[str]) -> tuple[bool, Optional[str]]:
    """`nz.clasificar` y, si no sabe la modalidad, prueba con las palabras en valenciano."""
    a_pie, modalidad = nz.clasificar(*textos)
    t = nz.clave(" ".join(x for x in textos if x))
    if not a_pie and re.search(r"\b(carrera|cursa)\b", t) and re.search(r"\bmarcha\b", t):
        # «7ª Carrera Cuatro Santos y Marcha Solidaria»: hay carrera además de la marcha.
        a_pie, modalidad = nz.clasificar(re.sub(r"\bmarcha\b", "", t))
    if not a_pie or modalidad:
        return a_pie, modalidad
    if _MUNTANYA.search(t):
        return True, "montaña"
    if _CROSS_VALENCIANO.search(t):
        return True, "cross"
    if _ASFALTO_VALENCIANO.search(t):
        return True, "asfalto"
    return True, None


def distancias(nombre: str) -> list[float]:
    # «11.3K»: `nz.clave` quita el punto y saldría 3 km; los decimales se leen antes.
    decimales = re.findall(r"\b(\d{1,3})[.,](\d)\s?km?\b", nombre, re.I)
    resto = re.sub(r"\b\d{1,3}[.,]\d\s?km?\b", " ", nombre, flags=re.I)
    kms = set(nz.distancias_del_nombre(resto)) | {float(f"{a}.{b}") for a, b in decimales}
    t = nz.clave(nombre)
    if re.search(r"\bmitja marato\b", t):
        kms.add(21.097)
    elif re.search(r"\bmarato\b", t):
        kms.add(42.195)
    return sorted(kms)


# Poblaciones (y pedanías) de fuera de Murcia que salen en las webs murcianas.
_FUERA_DE_MURCIA = {
    "Alicante": ["orihuela", "orihuela costa", "campoamor", "dehesa de campoamor", "la zenia", "torrevieja", "la mata",
                 "pilar de la horadada", "torre de la horadada", "san miguel de salinas", "guardamar del segura",
                 "rojales", "almoradi", "callosa de segura", "redovan", "cox", "bigastro", "benejuzar", "dolores",
                 "catral", "albatera", "rafal", "algorfa", "jacarilla", "torremendo", "los montesinos",
                 "benijofar", "formentera del segura", "granja de rocamora", "daya nueva", "daya vieja",
                 "san fulgencio", "san isidro", "crevillent", "crevillente", "elche", "elx", "santa pola",
                 "alicante", "novelda", "aspe", "monforte del cid", "pinoso", "el pinos", "villena", "elda",
                 "petrer", "sax", "monovar"],
    "Albacete": ["hellin", "caudete", "almansa", "tobarra", "yeste", "elche de la sierra", "nerpio"],
    "Almería": ["huercal overa", "pulpi", "velez rubio", "velez blanco", "cuevas del almanzora", "san juan de los terreros"],
}
_PROVINCIA_DE = {pob: prov for prov, pobs in _FUERA_DE_MURCIA.items() for pob in pobs}


def provincia_murciana(poblacion: Optional[str]) -> str:
    """Provincia de una población que sale en una web murciana: Murcia salvo las conocidas de fuera."""
    return _PROVINCIA_DE.get(nz.clave(poblacion), "Murcia")
