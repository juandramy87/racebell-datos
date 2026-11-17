"""Lectores del norte (País Vasco, Navarra, Galicia, Asturias, Cantabria), con copias recortadas de las
webs del 17/11/2026."""
from datetime import date, datetime

from fuentes import cronelec, fcatle, fga, fnaf, go321, kirolprobak
from nucleo.modelo import ABIERTA, CERRADA, PENDIENTE_CARTEL
from tests.test_lectores import buscar, muestra


def _fichas_kirolprobak(url: str) -> bytes:
    if "basauriko" in url:
        return muestra("kirolprobak-ficha-basauri.html")
    if "pasai-antxoko" in url:
        return muestra("kirolprobak-ficha-pasaia.html")
    return b"<html></html>"  # el resto de fichas no se guarda: salen como «sin datos de evento»


def test_kirolprobak_portada():
    urls, descartes = kirolprobak.enlaces(muestra("kirolprobak.html"))
    assert len(urls) == 14  # cada prueba una vez aunque salga por cada distancia u hora
    assert "https://inscripcion.kirolprobak.com/inscripcion/basauriko-herrikrosa-2026-evento-solidario/" in urls
    assert not any("feddi" in u for u in urls)  # se inscribe fuera de Kirolprobak
    assert any("Mugaz Muga" in d for d in descartes)  # triatlón


def test_kirolprobak_fichas():
    pedidas = []
    carreras, descartes = kirolprobak.leer(muestra("kirolprobak.html"),
                                           descargar_ficha=lambda u: pedidas.append(u) or _fichas_kirolprobak(u))
    assert all(u.endswith("/?lang=es") for u in pedidas)  # en castellano, para leer el plazo
    assert len(carreras) == 2
    # El JSON-LD de Basauri trae saltos de línea sin escapar: aun así se lee.
    c = buscar(carreras, "Basauriko")
    assert c.fecha == date(2026, 11, 22) and c.hora == "10:30"
    assert (c.poblacion, c.provincia) == ("Arizgoiti", "Bizkaia")
    assert c.inscripcion_hasta == datetime(2026, 11, 19, 12, 0)
    assert c.modalidad == "asfalto"  # del tipo de la portada («ATLETISMO-RUTA»)
    p = buscar(carreras, "Pasai Antxoko")
    assert (p.provincia, p.inscripcion_hasta) == ("Gipuzkoa", datetime(2026, 12, 17, 22, 0))
    assert p.precios == [{"nombre": "General", "euros": 12.0}]


def test_fga_diciembre():
    carreras, descartes = fga.leer([muestra("fga.html")])
    assert len(carreras) == 16
    assert {c.provincia for c in carreras} == {"A Coruña", "Pontevedra", "Ourense"}
    media = buscar(carreras, "Medio Maratón")
    assert media.distancias_km == [21.097]  # «Medio Maratón» en gallego, no 42,195
    assert (media.poblacion, media.provincia) == ("Vilagarcía de Arousa", "Pontevedra")
    assert buscar(carreras, "Belarmino Alonso").modalidad == "cross"
    assert buscar(carreras, "San Silvestre do Pino").poblacion == "O Pino"
    assert all(c.calidad == PENDIENTE_CARTEL for c in carreras)
    assert not any("PGTA" in c.nombre or "Charlas" in c.nombre or "Xogade" in c.nombre for c in carreras)
    assert any("Pista Curta" in d for d in descartes)


def test_fga_poblacion_y_meses():
    assert fga._poblacion("Coruña, A") == "A Coruña"
    assert fga._poblacion("Pereiro de Aguiar, O") == "O Pereiro de Aguiar"
    assert fga._poblacion("Varias sedes") is None
    assert fga.urls(date(2026, 11, 17)) == [
        "https://atletismo.gal/competicions/?cp_date=01/11/2026",
        "https://atletismo.gal/competicions/?cp_date=01/12/2026",
        "https://atletismo.gal/competicions/?cp_date=01/01/2027",
    ]


def test_321go():
    carreras, descartes = go321.leer(muestra("321go.html"),
                                     descargar_ficha=lambda u: muestra("321go-ficha.html") if "callos" in u else b"")
    assert len(carreras) == 8
    c = buscar(carreras, "5 Km De Los Callos")
    assert (c.fecha, c.hora) == (date(2026, 12, 5), "10:30")
    assert (c.poblacion, c.provincia) == ("Noreña", "Asturias")
    assert c.inscripcion_hasta == datetime(2026, 12, 1, 23, 59)
    assert c.estado_fuente == ABIERTA
    assert buscar(carreras, "Xornada 5").estado_fuente == CERRADA
    assert buscar(carreras, "Xornada 5").provincia == "Pontevedra"
    assert buscar(carreras, "Trail 14k Moaña").modalidad == "trail"
    assert any("Andaina" in d for d in descartes) and any("Escolar" in d for d in descartes)
    assert any("Praviana" in d for d in descartes)  # «Pravia, España»: sin provincia


def test_321go_recorta_ficha():
    recortada = go321.recortar_ficha(
        b"<html><p>Inscritos: 500 de 500</p><p>Fecha de inicio: 05 diciembre, 2026 - 12:00</p>"
        b"<p>Cierre de inscripciones: En 14 dias (01 diciembre, 2026 - 23:59, o hasta agotar plazas)</p></html>")
    assert b"Inscritos" not in recortada and b"05 diciembre" in recortada and b"01 diciembre" in recortada


def test_fcatle():
    carreras, descartes = fcatle.leer(muestra("fcatle.ics"))
    assert len(carreras) == 7
    assert {c.provincia for c in carreras} == {"Cantabria"}
    c = buscar(carreras, "Carrera de Navidad de Piélagos")
    assert (c.fecha, c.hora, c.poblacion) == (date(2026, 12, 20), "15:15", "Renedo de Piélagos")
    assert buscar(carreras, "Cross de Loredo").poblacion == "Loredo"
    assert any("Logroño" in d for d in descartes)  # fuera de Cantabria
    assert any("Marcha" in d for d in descartes) and any("Martillo" in d for d in descartes)


def test_cronelec():
    carreras, descartes = cronelec.leer(muestra("cronelec.html"))
    assert len(carreras) == 4
    c = buscar(carreras, "10 km de Laviana")
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 12, 6), "11:00", "Pola de Laviana", "Asturias")
    assert c.coords == (43.247, -5.5638)
    assert c.distancias_km == [10.0]


def test_fnaf():
    carreras, descartes = fnaf.leer(muestra("fnaf.html"))
    assert [c.nombre for c in carreras][:2] == ["Cto. Navarra Cross Corto y Master 2026/2027",
                                               "XLVII Cross de Las Peñas de Tafalla"]
    t = buscar(carreras, "Tafalla")
    assert (t.fecha, t.poblacion, t.provincia, t.modalidad) == (date(2026, 12, 8), "Tafalla", "Navarra", "cross")
    assert t.url_inscripcion and "rockthesport" in t.url_inscripcion
    assert not any("JDN" in c.nombre for c in carreras)
    assert any("Pista" in d for d in descartes)
