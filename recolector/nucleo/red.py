"""Descargas educadas: User-Agent propio, una petición cada pocos segundos por web,
reintento corto y caché del día para no repetir peticiones."""
from __future__ import annotations

import gzip
import hashlib
import http.client
import ssl
import subprocess
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse

USER_AGENT = "RacebellBot/0.1 (calendario gratuito de carreras populares; lee despacio y enlaza a la inscripcion oficial)"
PAUSA_SEGUNDOS = 3.0
# Webs que piden más pausa en su robots.txt (Crawl-delay).
PAUSA_POR_WEB = {"runnink.com": 10.0, "www.runnink.com": 10.0, "nominatim.openstreetmap.org": 1.5}
CACHE = Path(__file__).resolve().parents[1] / "datos" / "cache"

_ultima_peticion: dict[str, float] = {}


def descargar(url: str, *, usar_cache: bool = True, intentos: int = 3,
              recortar: Optional[Callable[[bytes], bytes]] = None) -> bytes:
    """Descarga una URL respetando la pausa por web. Guarda una copia del día en datos/cache/.
    `recortar` quita lo que no se debe guardar (p. ej. listas de inscritos) ANTES de la caché."""
    ruta = CACHE / date.today().isoformat() / (hashlib.sha1(url.encode()).hexdigest()[:16] + ".bin")
    if usar_cache and ruta.exists():
        return ruta.read_bytes()

    web = urlparse(url).netloc
    espera = PAUSA_POR_WEB.get(web, PAUSA_SEGUNDOS) - (time.monotonic() - _ultima_peticion.get(web, -1e9))
    if espera > 0:
        time.sleep(espera)

    ultimo_error: Exception | None = None
    for intento in range(intentos):
        try:
            datos = _bajar(url)
            if recortar:
                datos = recortar(datos)
            _ultima_peticion[web] = time.monotonic()
            ruta.parent.mkdir(parents=True, exist_ok=True)
            ruta.write_bytes(datos)
            return datos
        except (urllib.error.URLError, TimeoutError, http.client.HTTPException, ConnectionError) as error:
            ultimo_error = error
            _ultima_peticion[web] = time.monotonic()
            time.sleep(PAUSA_SEGUNDOS * (intento + 1))
    raise RuntimeError(f"No se pudo descargar {url}: {ultimo_error}")


def _contexto_intermedios() -> ssl.SSLContext:
    import certifi
    contexto = ssl.create_default_context(cafile=certifi.where())
    contexto.load_verify_locations(cafile=str(Path(__file__).with_name("intermedios.pem")))
    return contexto


def _bajar(url: str) -> bytes:
    peticion = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(peticion, timeout=30) as respuesta:
            datos = respuesta.read()
            # Algunas webs (Sportmaniacs) mandan gzip aunque no se pida: se descomprime siempre.
            return gzip.decompress(datos) if datos[:2] == b"\x1f\x8b" else datos
    except urllib.error.URLError as error:
        if not isinstance(error.reason, ssl.SSLCertVerificationError):
            raise
    # Algunas webs (Corredores Populares) no envían el certificado intermedio. Se reintenta con los
    # intermedios públicos guardados en intermedios.pem (además de certifi); se sigue validando todo.
    try:
        with urllib.request.urlopen(peticion, timeout=30, context=_contexto_intermedios()) as respuesta:
            datos = respuesta.read()
            return gzip.decompress(datos) if datos[:2] == b"\x1f\x8b" else datos
    except urllib.error.URLError as error:
        if not isinstance(error.reason, ssl.SSLCertVerificationError):
            raise
    # Último recurso: curl con los certificados del sistema (en el Mac encuentra el intermedio).
    resultado = subprocess.run(["curl", "-sSfL", "--compressed", "--max-time", "30", "-A", USER_AGENT, url],
                               capture_output=True, check=False)
    if resultado.returncode != 0:
        raise urllib.error.URLError(resultado.stderr.decode(errors="replace").strip())
    return resultado.stdout
