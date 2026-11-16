"""Tests de los lectores añadidos para el finde 28–29/11 (copias guardadas el 16/11/2026).
Las fichas se guardan recortadas (solo JSON-LD): nunca listas de inscritos ni clasificaciones."""
from datetime import date, datetime

from fuentes import cronofinisher, jsonld, olarivers, ruta091, sportmaniacs, time2run, tucarrera
from nucleo import normalizar as nz
from tests.test_lectores import buscar, muestra


def test_sportmaniacs_listado_y_recuerdo_de_provincias():
    tarjetas = sportmaniacs.tarjetas(muestra("sportmaniacs-3.html"))
    alcaudete = next(t for t in tarjetas if t["lugar"] == "Alcaudete")
    assert alcaudete["fecha"] == date(2026, 11, 28)

    abiertas = []

    def ficha(url):
        abiertas.append(url)
        return muestra("sportmaniacs-ficha.html")  # todas reciben la de Huelva: basta para probar el flujo

    recuerdo = {"bkt-larrabetzu-2026": sportmaniacs.FUERA}
    carreras, _ = sportmaniacs.leer([muestra("sportmaniacs-1.html")], descargar_ficha=ficha,
                                    desde=date(2026, 11, 21), hasta=date(2026, 11, 21), recuerdo=recuerdo)
    assert not any("larrabetzu" in u for u in abiertas)  # ya se sabía que es de fuera: no se abre
    assert carreras and all(c.provincia == "Huelva" for c in carreras)


def test_sportmaniacs_ficha_recortada():
    html = muestra("sportmaniacs-ficha.html")
    assert b"<body" not in html  # solo quedan los bloques JSON-LD
    c, _ = jsonld.leer_ficha(html, "https://x", sportmaniacs.ID)
    assert (c.fecha, c.poblacion, c.provincia) == (date(2026, 11, 22), "Huelva", "Huelva")
    assert c.precios[0]["euros"] == 10.0


def test_cronofinisher_solo_andalucia():
    pagina = muestra("cronofinisher.html")
    assert cronofinisher.otras_paginas(pagina) == ["https://www.cronofinisher.com/calendario//pg=2/"]
    carreras, _ = cronofinisher.leer([pagina, muestra("cronofinisher-2.html")])
    assert carreras and all(nz.es_andaluza(c.provincia) for c in carreras)
    c = buscar(carreras, "Violencia Contra las Mujeres")
    assert (c.fecha, c.poblacion, c.provincia) == (date(2026, 11, 22), "Cádiz", "Cádiz")
    assert c.inscripcion_hasta == datetime(2026, 11, 20, 23, 59) and c.cartel is None


def test_ruta091():
    carreras, _ = ruta091.leer(muestra("ruta091.html"))
    assert {c.poblacion for c in carreras} == {"Córdoba", "Écija"}  # Elche, Pamplona y Melilla fuera
    ecija = buscar(carreras, "Écija")
    assert (ecija.fecha, ecija.hora, ecija.provincia) == (date(2026, 11, 22), "10:00", "Sevilla")
    assert buscar(carreras, "Córdoba").distancias_km == [6.3]


def test_olarivers():
    carreras, descartes = olarivers.leer(muestra("olarivers.html"))
    c = buscar(carreras, "Sierra Albarracín")
    assert (c.fecha, c.poblacion, c.provincia, c.modalidad) == (date(2026, 11, 29), "El Bosque", "Cádiz", "montaña")
    assert c.inscripcion_hasta == datetime(2026, 11, 1, 0, 0)
    assert len({c.fuente.url for c in carreras}) == len(carreras)  # las destacadas no salen dos veces
    assert any("Bokeron Bike" in d for d in descartes)


def test_tucarrera():
    carreras, descartes = tucarrera.leer(muestra("tucarrera.json"))
    c = buscar(carreras, "Ultra Maratón Costa de Almeria")
    assert (c.fecha, c.provincia, c.distancias_km) == (date(2026, 11, 28), "Almería", [])  # «ultra», no 42,195
    assert any("Calar Alto Ride" in d for d in descartes) and all(c.provincia for c in carreras)


def test_time2run_con_rockthesport():
    carreras, descartes = time2run.leer(
        muestra("time2run.html"),
        descargar_ficha=lambda u: muestra("time2run-ficha.html") if "caras-norte" in u else b"",
        descargar_rockthesport=lambda u: muestra("rockthesport-ficha.html"))
    c = buscar(carreras, "Caras Nortes")
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 11, 28), "07:30", "Güejar Sierra", None)
    assert c.inscripcion_hasta == datetime(2026, 11, 15, 23, 59) and "Inscripciones agotadas" in c.previos
    assert buscar(carreras, "Tiñosa").fecha == date(2026, 11, 21)
    assert any("Hybrid" in d for d in descartes)  # categoría «fitness»: híbridas, no cuentan


def test_hibridas_no_cuentan():
    assert nz.clasificar("Fungo Hybrid Race")[0] is False
    assert nz.clasificar("HYROX Sevilla")[0] is False
