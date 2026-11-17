"""Tests de los lectores añadidos el 16/11/2026 (copias guardadas ese día)."""
from datetime import date, datetime

from fuentes import (alcanzatumeta, avaibook, corredorespopulares, cronius, deportime, gesconchip, inscrik,
                     jsonld, runnink, todofondo)
from nucleo.modelo import DUDOSO
from tests.test_lectores import buscar, muestra


def test_gesconchip():
    carreras, descartes = gesconchip.leer(muestra("gesconchip.html"))
    assert len(carreras) == 23  # 21 andaluzas y 2 de Ceuta (el Duatlón de Herrera ya no cuenta: hay bici)
    assert not any("Duatl" in c.nombre for c in carreras)
    c = buscar(carreras, "Cross Pinar del Rey")
    assert (c.fecha, c.poblacion, c.provincia) == (date(2026, 11, 22), "San Roque", "Cádiz")
    assert c.inscripcion_hasta == datetime(2026, 11, 18, 12, 0)
    chiclana = buscar(carreras, "Urbana Ciudad de Chiclana")
    assert chiclana.inscripcion_hasta is None and "Cambio de precio el 20/11" in chiclana.previos[0]
    assert buscar(carreras, "Trail Benahavís")  # icono «Carrera Montaña/Trail»: sí es a pie
    assert any("Triatlón" in d for d in descartes)
    assert any(c.provincia == "Ceuta" for c in carreras)  # antes se descartaba


def test_corredores_populares():
    carreras, _ = corredorespopulares.leer(muestra("corredorespopulares.html"))
    c = buscar(carreras, "Santiponce")
    assert c.nombre == "XXIX Carrera Popular Santiponce"  # solo la primera línea del título
    assert (c.fecha, c.provincia, c.inscripcion_hasta) == (date(2026, 11, 22), "Sevilla", datetime(2026, 11, 18, 23, 59))
    assert buscar(carreras, "Puente Genil").provincia == "Córdoba"


def test_cronius_y_ficha_avaibook():
    assert len(cronius.enlaces(muestra("cronius.html"))) == 12
    c, motivo = avaibook.leer_ficha(muestra("cronius-ficha.html"), "https://x", cronius.ID)
    assert motivo is None
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 11, 21), "16:30", "Gibraleón", "Huelva")
    assert c.inscripcion_hasta == datetime(2026, 11, 17, 23, 59)
    assert {"nombre": "General Absoluta", "euros": 11.0} in c.precios


def test_inscrik_jsonld_marca_dias_distintos():
    c, _ = jsonld.leer_ficha(muestra("inscrik-ficha.html"), "https://x", inscrik.ID)
    assert (c.provincia, c.fecha) == ("Almería", date(2026, 11, 21))
    assert c.precios[0] == {"nombre": "Media Maratón", "euros": 25.0}
    assert c.calidad == DUDOSO  # empieza el 21 a las 16:30 y acaba el 22: hay que confirmar el día


def test_deportime():
    c, _ = deportime.leer_ficha(muestra("deportime-ficha.html"), "https://x")
    assert c.nombre == "XIII Carrera por la No Violencia de Género y por la Igualdad"
    assert (c.fecha, c.hora, c.provincia) == (date(2026, 11, 22), "11:30", "Jaén")
    assert "Inscripciones agotadas" in c.previos


def test_todofondo():
    carreras, descartes = todofondo.leer(muestra("todofondo.html"))
    c = buscar(carreras, "Duchenne")
    assert (c.fecha, c.poblacion, c.provincia, c.modalidad) == (date(2026, 11, 22), "Almería", "Almería", "trail")
    assert any("Senderismo" in d for d in descartes)


def test_runnink():
    carreras, descartes = runnink.leer(muestra("runnink.html"))
    c = buscar(carreras, "Puerto Menesteo")
    assert (c.fecha, c.hora, c.poblacion) == (date(2026, 11, 22), "10:00", "El Puerto de Santa María")
    assert any("Híbrida" in d for d in descartes)


def test_alcanza_tu_meta_almeria_y_murcia():
    carreras, _ = alcanzatumeta.leer(muestra("alcanzatumeta.html"))
    assert {c.provincia for c in carreras} >= {"Almería", "Murcia"}
    c = buscar(carreras, "Bajo Almanz")
    assert (c.fecha, c.hora, c.inscripcion_hasta) == (date(2026, 11, 22), "08:30", datetime(2026, 11, 21, 0, 0))


def test_montur_quita_senderismo_y_lee_hora_y_provincia():
    from fuentes import montur
    carreras, descartes = montur.leer(muestra("montur.html"))
    sabina = next(c for c in carreras if "Sabina" in c.nombre)
    assert (sabina.fecha.isoformat(), sabina.hora, sabina.poblacion, sabina.provincia) == ("2027-04-18", "09:00", "Chirivel", "Almería")
    assert not any("Senderismo" in c.nombre or "Marcha" in c.nombre for c in carreras)
    assert len(descartes) == 2


def test_cruzandolameta_municipio_sin_confundir_la_provincia():
    from fuentes import cruzandolameta
    carreras, _ = cruzandolameta.leer(muestra("cruzandolameta.html"))
    por_nombre = {c.nombre: c for c in carreras}
    atarfe = por_nombre["IV Carrera San Silvestre Atarfe 2026"]
    assert (atarfe.poblacion, atarfe.provincia) == ("Atarfe", "Granada")
    roquetas = por_nombre["IX Media Maratón Ciudad de Roquetas 2026"]
    assert roquetas.inscripcion_hasta.isoformat() == "2026-11-19T23:59:00"
    guajar = por_nombre["XVI San Silvestre Subida Al Castillejo"]
    assert (guajar.poblacion, guajar.provincia) == (None, "Granada")
    assert por_nombre["CxM Sierro 2027"].fecha.isoformat() == "2027-05-02"
