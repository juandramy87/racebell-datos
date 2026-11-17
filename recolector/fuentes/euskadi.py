"""Ayuda común para el País Vasco: sacar el municipio de un texto en euskera o castellano.

Los nombres de las carreras vascas llevan el pueblo en genitivo («Errenteriako San Silbestrea», «Azkoitiko Herri
Lasterketa», «Markina-Xemeingo Krosa»), y a veces se da el nombre castellano («Rentería», «Vergara») o los dos
(«Laudio/Llodio»). `nz.municipio_espana` solo encuentra el nombre exacto: aquí se prueban además los nombres sin
el sufijo -ko/-go (y con la -a que se pierde: «Azkoitiko» → «Azkoitia») y una tabla corta de nombres castellanos.

Sirve también para arreglar otras fuentes (p. ej. las fichas de RockTheSport sin región: «Errenteriako…»)."""
from __future__ import annotations

import re
from typing import Iterable, Optional

from nucleo import normalizar as nz

PROVINCIAS_VASCAS = ("Álava", "Bizkaia", "Gipuzkoa")

# Nombre castellano, abreviado o histórico (en nz.clave) → nombre del INE que entiende nz.municipio_espana.
_OTROS_NOMBRES = {
    "bilbo": "Bilbao", "gasteiz": "Vitoria-Gasteiz", "vitoria": "Vitoria-Gasteiz", "donosti": "Donostia",
    "zarauz": "Zarautz", "renteria": "Errenteria", "vergara": "Bergara", "azcoitia": "Azkoitia",
    "azpeitia": "Azpeitia", "fuenterrabia": "Hondarribia", "pasajes": "Pasaia", "mondragon": "Arrasate",
    "guernica": "Gernika-Lumo", "gernika": "Gernika-Lumo", "baracaldo": "Barakaldo", "santurce": "Santurtzi",
    "lequeitio": "Lekeitio", "motrico": "Mutriku", "zumaya": "Zumaia",
    "guetaria": "Getaria", "deva": "Deba", "plencia": "Plentzia",
    "sopelana": "Sopela", "musquiz": "Muskiz", "trapagaran": "Valle de Trápaga-Trapagaran",
    "urduna": "Orduña", "amorebieta": "Amorebieta-Etxano", "zornotza": "Amorebieta-Etxano",
    "llodio": "Laudio", "salvatierra": "Agurain", "oyarzun": "Oiartzun",
    "lasarte": "Lasarte-Oria", "villafranca de ordicia": "Ordizia", "legazpia": "Legazpi", "onate": "Oñati",
    "arechavaleta": "Aretxabaleta", "escoriatza": "Eskoriatza", "sodupe": "Güeñes",
    "las arenas": "Getxo", "algorta": "Getxo", "areeta": "Getxo", "romo": "Getxo", "gros": "Donostia",
    "amara": "Donostia", "egia": "Donostia", "intxaurrondo": "Donostia", "antiguo": "Donostia",
    "rekalde": "Bilbao", "deusto": "Bilbao", "arizgoiti": "Basauri", "mimetiz": "Zalla",
    "pobena": "Muskiz", "san julian de muskiz": "Muskiz", "itziar": "Deba", "zaramillo": "Güeñes",
    "lezama araba": "Amurrio",
}
_PALABRA = re.compile(r"[a-zñ]+(?:-[a-zñ]+)*")
# Palabras que no son pueblos aunque coincidan con alguno o con un nombre recortado.
_NO_PUEBLO = {"herri", "krosa", "kros", "cross", "lasterketa", "mendi", "trail", "san", "silbestre", "silvestre",
              "txiki", "gau", "igoera", "erronka", "carrera", "popular", "media", "maraton", "nocturna", "urbana"}


def _probar(nombre: str, provincias: Optional[Iterable[str]]) -> Optional[tuple[str, str]]:
    hallado = nz.municipio_espana(nombre)
    if hallado and (provincias is None or hallado[1] in provincias):
        return hallado
    return None


def _candidatos(palabra: str) -> list[str]:
    """«azkoitiko» → [«azkoitiko», «azkoiti», «azkoitia»]; «beasaingo» → [… «beasain»]."""
    salida = [palabra]
    for sufijo in ("ko", "go"):
        if palabra.endswith(sufijo) and len(palabra) > len(sufijo) + 3:
            base = palabra[: -len(sufijo)]
            salida += [base, base + "a"]
    return salida


def municipio(texto: Optional[str], provincias: Optional[Iterable[str]] = PROVINCIAS_VASCAS
              ) -> Optional[tuple[str, str]]:
    """(municipio, provincia) del texto, o None. `provincias` limita el resultado (por defecto, las tres vascas;
    None = toda España). Prueba: el texto entero, sus trozos separados por «/», la tabla de nombres castellanos y
    cada palabra con y sin el sufijo -ko/-go."""
    if not texto:
        return None
    provincias = tuple(provincias) if provincias is not None else None
    trozos = [texto] + [t for t in re.split(r"\s*/\s*", texto) if t.strip()]
    for t in trozos:
        if hallado := _probar(t, provincias):
            return hallado
        k = nz.clave(t)
        if k in _OTROS_NOMBRES and (hallado := _probar(_OTROS_NOMBRES[k], provincias)):
            return hallado
    palabras = _PALABRA.findall(nz.clave(texto))
    # Primero las parejas («las arenas», «lasarte oria»), luego cada palabra.
    grupos = [" ".join(palabras[i:i + 2]) for i in range(len(palabras) - 1)] + palabras
    for palabra in grupos:
        if palabra in _NO_PUEBLO or len(palabra) < 4:
            continue
        for cand in _candidatos(palabra):
            if cand in _NO_PUEBLO:
                continue
            if cand in _OTROS_NOMBRES and (hallado := _probar(_OTROS_NOMBRES[cand], provincias)):
                return hallado
            if hallado := _probar(cand, provincias):
                return hallado
    return None
