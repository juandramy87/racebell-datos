"""Tests de cada lector con copias guardadas de las webs (16/11/2026). Si una web cambia,
basta con guardar una copia nueva en tests/muestras/ y ajustar los valores esperados."""
from datetime import date, datetime
from pathlib import Path

import pytest

from fuentes import dorsalchip, faa, globaltempo, sesca, tecnocrono
from nucleo.modelo import ABIERTA, CERRADA, DE_FUENTE, NO_ABIERTA, PENDIENTE_CARTEL

MUESTRAS = Path(__file__).parent / "muestras"


def muestra(nombre: str) -> bytes:
    return (MUESTRAS / nombre).read_bytes()


def buscar(carreras, texto):
    encontradas = [c for c in carreras if texto.lower() in c.nombre.lower()]
    assert encontradas, f"No aparece «{texto}»"
    return encontradas[0]


def test_dorsalchip_lee_cierre_exacto():
    carreras, descartes = dorsalchip.leer(muestra("dorsalchip.json"))
    assert len(carreras) == 51  # sin las dos fichas de la «ME Hybrid Marbella» (las híbridas no cuentan)
    c = buscar(carreras, "Cerebro no es Gris")
    assert c.fecha == date(2026, 11, 22)
    assert (c.poblacion, c.provincia) == ("Córdoba", "Córdoba")
    assert c.inscripcion_hasta == datetime(2026, 11, 18, 23, 55)
    assert c.url_inscripcion.startswith("https://www.dorsalchip.es/carrera/")
    assert c.calidad == DE_FUENTE


def test_dorsalchip_descarta_lo_que_no_es_a_pie():
    carreras, descartes = dorsalchip.leer(muestra("dorsalchip.json"))
    nombres = " ".join(c.nombre for c in carreras).lower()
    assert "mountainbike" not in nombres and "marcha" not in nombres and "triatlon" not in nombres
    assert any("Bokeron Bike" in d for d in descartes)


def test_dorsalchip_distancias_del_nombre():
    carreras, _ = dorsalchip.leer(muestra("dorsalchip.json"))
    assert buscar(carreras, "5Km y 10Km").distancias_km == [5.0, 10.0]
    assert buscar(carreras, "Media Maratón").distancias_km == [21.097]


def test_tecnocrono_plazos_y_coordenadas():
    carreras, descartes = tecnocrono.leer(muestra("tecnocrono.html"))
    assert len(carreras) == 21
    c = buscar(carreras, "Cadeba CxM Toleta")
    assert c.nombre == "II Cadeba CxM Toleta Puerto Serrano"  # sin comillas y en formato título
    assert (c.fecha, c.hora) == (date(2026, 11, 21), "09:30")
    assert c.inscripcion_hasta == datetime(2026, 11, 15, 21, 0)
    assert c.modalidad == "montaña"
    lat, lon = c.coords
    assert 36 < lat < 38.8 and -7.6 < lon < -1.6  # la fuente las da al revés: se corrigen


def test_tecnocrono_descarta_circuitos_y_otros():
    _, descartes = tecnocrono.leer(muestra("tecnocrono.html"))
    assert any("COPA/LIGA SEVILLANA" in d.upper() for d in descartes)
    assert any("Otro" in d for d in descartes)


def test_sesca_poblacion_fecha_y_metros():
    carreras, descartes = sesca.leer(muestra("sesca.html"))
    assert len(carreras) == 12
    c = buscar(carreras, "Torrecera")
    assert (c.fecha, c.hora, c.distancias_km) == (date(2026, 11, 21), "10:00", [8.0])
    assert c.provincia == "Cádiz" and c.calidad == PENDIENTE_CARTEL
    assert any("Ciclista" in d for d in descartes)


def test_globaltempo_portada_y_ficha_sin_inscritos():
    pruebas = globaltempo.leer_portada(muestra("globaltempo.html"))
    assert len(pruebas) == 33
    ficha = globaltempo.leer_ficha(muestra("globaltempo-ficha.html"))
    assert ficha == {"fecha": "12-11-2026 11:15 horas", "provincia": "GRANADA", "localidad": "GRANADA",
                     "nombre": "XXII CARRERA UNIVERSITARIA SAN ALBERTO MAGNO"}


def test_globaltempo_filtra_fechas_por_defecto_y_no_a_pie():
    fichas = []

    def descargar_ficha(url):
        fichas.append(url)
        return muestra("globaltempo-ficha.html")  # todas dicen Granada; solo importa el filtrado

    carreras, descartes = globaltempo.leer(muestra("globaltempo.html"), descargar_ficha=descargar_ficha,
                                           desde=date(2026, 11, 16), hasta=date(2026, 12, 31),
                                           buscar_ocultas=False)
    nombres = [c.nombre for c in carreras]
    assert "X Carrera de Fondo - Peligros Suena" in nombres
    assert not any("BTT" in n or "Senderos" in n or "Marchadoras" in n or "Mushing" in n for n in nombres)
    assert any("01-01" in d for d in descartes)
    assert len(fichas) == len(carreras) + sum("fuera de Andalucía" in d for d in descartes)


def test_faa_fechas_nombres_y_carteles():
    carreras, _ = faa.leer(muestra("faa.html"))
    assert len(carreras) == 26
    c = buscar(carreras, "Pinares de Cartaya")
    assert c.fecha == date(2026, 11, 22)
    assert c.url_inscripcion == "https://web.faalive.com/inscriptions/308"
    assert c.cartel.endswith(".webp") and "-212x300" not in c.cartel  # el cartel grande
    assert c.calidad == PENDIENTE_CARTEL


@pytest.mark.parametrize("ahora, esperado", [
    (datetime(2026, 11, 1), ABIERTA),
    (datetime(2026, 11, 19), CERRADA),
    (datetime(2026, 6, 1), NO_ABIERTA),
])
def test_estado_se_calcula_con_la_hora(ahora, esperado):
    carreras, _ = dorsalchip.leer(muestra("dorsalchip.json"))
    assert buscar(carreras, "Cerebro no es Gris").estado(ahora) == esperado


def test_globaltempo_encuentra_fichas_ocultas():
    """Cañada Real Soriana (id 3317) no sale en la portada; solo se encuentra sondeando los id."""
    pedidas = []

    def descargar_ficha(url):
        pedidas.append(url)
        if url.endswith("id=3317"):
            return muestra("globaltempo-oculta.html")
        return muestra("globaltempo-vacia.html")

    carreras, _ = globaltempo.leer(muestra("globaltempo.html"), descargar_ficha=descargar_ficha,
                                   desde=date(2026, 11, 16), hasta=date(2026, 12, 31))
    c = buscar(carreras, "Cañada Real Soriana")
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 11, 22), "10:00", "Villarrubia", "Córdoba")
    assert globaltempo.leer_ficha(muestra("globaltempo-vacia.html")).get("nombre") is None


def test_globaltempo_nunca_guarda_inscritos():
    pagina = b"<p>Fecha: 22-11-2026 10:00 horas</p><h3>Inscritos en la Carrera</h3><td>PEPE</td><td>PEREZ</td>"
    recortada = globaltempo.recortar_ficha(pagina)
    assert b"PEPE" not in recortada and b"Fecha" in recortada
    for f in MUESTRAS.glob("globaltempo-*.html"):
        assert b"Inscritos en la Carrera" not in f.read_bytes(), f
