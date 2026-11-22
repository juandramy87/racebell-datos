"""Ronda 4: País Vasco y La Rioja (copias recortadas de las webs del 17/11/2026)."""
from datetime import date

from fuentes import buscametas, euskadi, kirolbide
from nucleo.modelo import NO_ABIERTA
from tests.test_lectores import buscar, muestra


def test_euskadi_municipio_en_euskera():
    assert euskadi.municipio("Errenteriako San Silbestrea 2026") == ("Errenteria", "Gipuzkoa")
    assert euskadi.municipio("Azkoitiko Herri Lasterketa") == ("Azkoitia", "Gipuzkoa")
    assert euskadi.municipio("Lasarte-Oriako Mendi Lasterketa") == ("Lasarte-Oria", "Gipuzkoa")
    assert euskadi.municipio("Markina-Xemeingo krosa") == ("Markina-Xemein", "Bizkaia")
    assert euskadi.municipio("Idiazabalgo Herri Krosa") == ("Idiazabal", "Gipuzkoa")
    assert euskadi.municipio("Laudio / Llodio") == ("Laudio", "Álava")
    assert euskadi.municipio("Vergara") == ("Bergara", "Gipuzkoa")
    assert euskadi.municipio("Gasteizko Maratoia") == ("Vitoria-Gasteiz", "Álava")
    assert euskadi.municipio("Herri Krosa") is None
    assert euskadi.municipio("Calahorra") is None  # fuera de las tres provincias vascas…
    assert euskadi.municipio("Calahorra", None) == ("Calahorra", "La Rioja")  # …salvo que se pida toda España


def test_kirolbide_ocurrencias_y_municipios():
    lista, total = kirolbide.ocurrencias(muestra("kirolbide-31dic.html"))
    assert (len(lista), total) == (15, 23)  # más de 15 ese día: hay que partir por municipios
    municipios = kirolbide.municipios_del_formulario(muestra("kirolbide-31dic.html"))
    assert len(municipios) == 114 and "-1" in municipios
    assert "fecha_busqueda=31%2F12%2F2026" in kirolbide.url_dia(date(2026, 12, 31))


def test_kirolbide_leer_parte_el_31_de_diciembre():
    municipios = kirolbide.municipios_del_formulario(muestra("kirolbide-31dic.html"))
    mitad = len(municipios) // 2
    paginas = {kirolbide.url_dia(date(2026, 12, 31)): muestra("kirolbide-31dic.html"),
               kirolbide.url_dia(date(2026, 12, 31), municipios[:mitad]): muestra("kirolbide-31dic-1.html"),
               kirolbide.url_dia(date(2026, 12, 31), municipios[mitad:]): muestra("kirolbide-31dic-2.html")}
    carreras, descartes = kirolbide.leer(paginas.__getitem__, date(2026, 12, 31), date(2026, 12, 31))
    assert len(carreras) == 23 and {c.fecha for c in carreras} == {date(2026, 12, 31)}
    assert {c.provincia for c in carreras} == {"Bizkaia"}
    baraka = buscar(carreras, "Barakaldesa")
    assert (baraka.poblacion, baraka.fuente.id) == ("Barakaldo", "kirolbide")
    assert baraka.fuente.url.startswith("https://www.bizkaia.eus/es/kirolbidepro/agenda/-/evento-detalle/")
    assert all("<" not in c.nombre and "​" not in c.nombre for c in carreras)


def test_kirolbide_ficha():
    datos = kirolbide.leer_ficha(muestra("kirolbide-ficha.html"))
    assert datos == {"hora": "17:45", "inscripcion": "https://www.buscametas.com/modulos/ticket/evento.php?codigo=1385"}


def test_kirolbide_descarta_lo_que_no_es_a_pie():
    c, motivo = kirolbide.carrera_de({"titulo": "Abadiñoko Ziklokrosa 2026", "fecha": "2026-11-28",
                                       "deporteList": ["Ciclismo"], "ubicacion": "Abadiño"})
    assert c is None and "no es a pie" in motivo
    c, _ = kirolbide.carrera_de({"titulo": "Bizkaia Kopa <span lang=\"en\">Trail</span> 2026: Larrabetzu",
                                 "fecha": "2026-11-21", "deporteList": ["Otros", "Carreras de montaña", "Marchas"],
                                 "ubicacion": "<a href=\"https://maps\">Larrabetzu</a>", "friendlyURL": "/x"})
    assert (c.nombre, c.poblacion, c.modalidad) == ("Bizkaia Kopa Trail 2026: Larrabetzu", "Larrabetzu", "trail")


def test_buscametas():
    carreras, descartes = buscametas.leer(muestra("buscametas.html"))
    assert len(carreras) == 10 and any("Mendi Martxa" in d for d in descartes)  # la marcha no cuenta
    muskiz = buscar(carreras, "Muskizko")
    assert (muskiz.fecha, muskiz.poblacion, muskiz.provincia) == (date(2026, 12, 19), "Muskiz", "Bizkaia")
    assert muskiz.url_inscripcion == "https://www.buscametas.com/modulos/ticket/evento.php?codigo=1385"
    media = buscar(carreras, "Media de Vitoria")
    assert (media.nombre, media.poblacion, media.provincia) == ("La Media de Vitoria-Gasteiz", "Vitoria-Gasteiz", "Álava")
    assert buscar(carreras, "Zalla").nombre == "Zalla-Balma-Zalla"
    izar = buscar(carreras, "Izarlokak")  # «Carrera Martxa»: carrera y marcha, sí cuenta
    assert (izar.nombre, izar.poblacion) == ("Carrera Martxa Izarlokak 25N", "Sodupe")
    sodupe = buscar(carreras, "San Silvestre Sodupe")
    assert sodupe.estado_fuente == NO_ABIERTA and sodupe.url_inscripcion is None
    assert buscar(carreras, "San Antontxuko").modalidad == "cross"


def test_kirolbide_captcha_da_error():
    # Desde el 20/11/2026 la agenda de Bizkaia pide un captcha a los robots: error claro, no «0 carreras».
    import pytest
    reto = b"<html><body>Please enable JavaScript to view the page content. This question is for testing whether you are a human visitor</body></html>"
    with pytest.raises(RuntimeError, match="captcha"):
        kirolbide.ocurrencias(reto)
