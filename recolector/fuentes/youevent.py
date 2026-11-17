"""YouEvent: portal de inscripciones de Madrid (sierra norte, sureste), Guadalajara y Segovia.
El calendario (`Calendario.asp?paginacion=0`, todo en una página) trae fecha, nombre, localidad, provincia,
deporte y modalidad. La ficha de cada prueba trae el plazo de inscripción («Fecha Límite Inscripción: A partir
de … hasta el …») y el horario. De la ficha solo se guarda el bloque de datos de la prueba (ni correos ni
teléfonos del organizador). Sin robots.txt (404)."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Callable, Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "youevent"
URL = "https://www.youevent.es/sport/Calendario.asp?paginacion=0"
FICHA = "https://www.youevent.es/sport/Tabla_FichaEventoDeportivo.asp?id_competicion={}"

_MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
          "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
# Deporte (columna «Federación / Deporte») que puede ser una carrera a pie.
_DEPORTES_A_PIE = {"atletismo", "montana", "ae trail running"}
# Modalidades o nombres que no son una carrera aunque vayan como atletismo o montaña.
_NO_CARRERA = re.compile(r"escalada|aula de naturaleza|curso|cuota|zumba|dorsal 0|dorsal cero|"
                         r"tecnificacion|jornada de puertas|infantil|escolar")
_MODALIDAD_NO = re.compile(r"senderis|marcha")


def _texto(contenido: bytes | str) -> str:
    if isinstance(contenido, str):
        return contenido
    try:
        return contenido.decode("utf-8")
    except UnicodeDecodeError:
        return contenido.decode("cp1252", errors="replace")  # la web va en Windows-1252


def _fecha_larga(texto: str) -> Optional[date]:
    """«Viernes, 20 de Noviembre  de 2026» → date(2026, 11, 20)."""
    m = re.search(r"(\d{1,2}) de (\w+)\s+de (\d{4})", nz.sin_tildes(texto).lower())
    if not m or m.group(2) not in _MESES:
        return None
    return date(int(m.group(3)), _MESES[m.group(2)], int(m.group(1)))


def recortar_ficha(contenido: bytes) -> bytes:
    """Deja solo el texto de la ficha entre «FICHA DEL EVENTO» y los datos de contacto del organizador."""
    sopa = BeautifulSoup(_texto(contenido), "html.parser")
    for s in sopa(["script", "style"]):
        s.decompose()
    texto = re.sub(r"\n\s*\n+", "\n", sopa.get_text("\n"))
    inicio = texto.find("FICHA DEL EVENTO")
    fin = texto.find("Email Organizador")
    if inicio < 0:
        return b""
    return texto[inicio:fin if fin > inicio else inicio + 4000].encode("utf-8")


def _bloque(texto: str, etiqueta: str) -> str:
    """Texto que sigue a «Etiqueta:» hasta la siguiente etiqueta («Algo:» al final de una línea)."""
    m = re.search(re.escape(etiqueta) + r"\s*:?\s*\n(.*?)(?=\n[^\n]{2,40}:\s*\n|\Z)", texto, re.S)
    return m.group(1).strip() if m else ""


def leer_ficha(contenido: bytes | str, c: Carrera) -> None:
    """Completa la carrera con el plazo de inscripción, la hora y las distancias de la ficha (ya recortada)."""
    texto = _texto(contenido)
    plazo = _bloque(texto, "Fecha Límite Inscripción")
    if plazo:
        partes = re.split(r"\bhasta\b", plazo, maxsplit=1)
        if len(partes) == 2:
            desde, hasta = _fecha_larga(partes[0]), _fecha_larga(partes[1])
            if desde:
                c.inscripcion_desde = datetime(desde.year, desde.month, desde.day, 0, 0)
            if hasta:
                c.inscripcion_hasta = datetime(hasta.year, hasta.month, hasta.day, 23, 59)
        elif _fecha_larga(plazo):
            hasta = _fecha_larga(plazo)
            c.inscripcion_hasta = datetime(hasta.year, hasta.month, hasta.day, 23, 59)
    horario = _bloque(texto, "Horario/Actividades")
    m = re.search(r"\b(\d{1,2})[:.h](\d{2})\b", horario)
    if m and int(m.group(1)) < 24:
        c.hora = f"{int(m.group(1)):02d}:{m.group(2)}"
    kms = set(c.distancias_km)
    for linea in _bloque(texto, "Distancias/Duración").splitlines():
        if re.search(r"senderis|marcha|andarin|infantil|chupeta|benjam|alevin", nz.clave(linea)):
            continue
        for x in re.findall(r"(\d{1,3}(?:[.,]\d{1,3})?)\s?(?:km|kms|k)\b", linea, re.I):
            km = float(x.replace(",", "."))
            if 0.5 <= km <= 200:
                kms.add(km)
    c.distancias_km = sorted(kms)


def leer(contenido: bytes | str, descargar_ficha: Optional[Callable[[str], bytes]] = None,
         desde: Optional[date] = None, hasta: Optional[date] = None) -> tuple[list[Carrera], list[str]]:
    """Calendario completo → carreras. Con `descargar_ficha` abre la ficha de las que caen entre desde y hasta."""
    sopa = BeautifulSoup(_texto(contenido), "html.parser")
    carreras: list[Carrera] = []
    descartes: list[str] = []
    for fila in sopa.select("tr[class^=evento_]"):
        celdas = [td.get_text(" ", strip=True) for td in fila.find_all("td", recursive=False)]
        if len(celdas) < 6:
            continue
        m_fecha = re.search(r"(\d{2})/(\d{2})/(\d{4})", celdas[0])
        boton = fila.find("input", onclick=re.compile(r"mostrarEvento"))
        m_id = re.search(r"mostrarEvento\((\d+)", boton["onclick"]) if boton else None
        if not m_fecha:
            continue
        nombre = nz.nombre(celdas[1])
        deporte, modalidad_fuente = celdas[4], celdas[5]
        if (nz.clave(deporte) not in _DEPORTES_A_PIE or _NO_CARRERA.search(nz.clave(f"{nombre} {modalidad_fuente}"))
                or _MODALIDAD_NO.search(nz.clave(modalidad_fuente))):
            descartes.append(f"no es carrera a pie: {nombre} ({deporte} / {modalidad_fuente})")
            continue
        a_pie, modalidad = nz.clasificar(nombre, modalidad_fuente)
        if not a_pie and re.search(r"\bcarrera\b", nz.clave(nombre)) and "marcha" in nz.clave(nombre):
            # «Carrera popular y marcha senderista», «Marcha carrera solidaria»: hay carrera además de la marcha.
            a_pie, modalidad = nz.clasificar(re.sub(r"(?i)marcha( senderista)?", "", nombre), modalidad_fuente)
        if not a_pie:
            descartes.append(f"no es a pie: {nombre} ({modalidad_fuente})")
            continue
        provincia = nz.provincia(celdas[3])
        if not provincia:
            descartes.append(f"sin provincia: {nombre} ({celdas[3]})")
            continue
        url = FICHA.format(m_id.group(1)) if m_id else URL
        c = Carrera(
            nombre=nombre,
            fecha=date(int(m_fecha.group(3)), int(m_fecha.group(2)), int(m_fecha.group(1))),
            fuente=Fuente(ID, url),
            poblacion=nz.poblacion(celdas[2]),
            provincia=provincia,
            modalidad=modalidad or ("montaña" if "montana" in nz.clave(modalidad_fuente) else None),
            distancias_km=nz.distancias_del_nombre(nombre),
            url_inscripcion=url if m_id else None,
        )
        en_plazo = (not desde or c.fecha >= desde) and (not hasta or c.fecha <= hasta)
        if descargar_ficha and m_id and en_plazo:
            try:
                leer_ficha(descargar_ficha(url), c)
            except Exception as error:  # sin ficha la carrera vale igual
                descartes.append(f"ficha sin leer: {nombre} ({error})")
        if not c.inscripcion_hasta:
            c.marcar("Cierre de inscripción en la ficha de YouEvent", "pendiente_cartel")
        carreras.append(c)
    return carreras, descartes
