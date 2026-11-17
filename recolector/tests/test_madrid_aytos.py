"""Tests del lector de ayuntamientos de Madrid (copias recortadas del 17/11/2026)."""
from datetime import date

from fuentes import aytos_madrid as a
from tests.test_lectores import buscar, muestra

HOY = date(2026, 11, 17)


def test_tec_agenda_municipal():
    carreras, descartes, siguiente = a.leer_tec(muestra("aytos_madrid-tec.json"), "Manzanares el Real")
    assert siguiente is None
    assert len(carreras) == 1  # ni la charla de nutrición «deportista» ni el cuentacuentos
    c = carreras[0]
    assert (c.nombre, c.fecha, c.poblacion, c.provincia) == (
        "San Silvestre 2026", date(2026, 12, 31), "Manzanares el Real", "Madrid")
    assert c.fuente.id == "aytos_madrid" and c.fuente.url.endswith("/agenda-municipal/san-silvestre-2026/")
    assert not descartes  # la «Marcha Solidaria» ni se mira: no parece carrera


def test_tec_url():
    assert a.url_tec("https://manzanareselreal.es", HOY, date(2027, 1, 31)) == (
        "https://manzanareselreal.es/wp-json/tribe/events/v1/events?per_page=50&start_date=2026-11-17"
        "&end_date=2027-01-31")


def test_mec_busqueda_y_ficha():
    assert a.fichas_mec(muestra("aytos_madrid-mec.json")) == [
        ("Carrera solidaria", "https://www.ayto-villacanada.es/agenda-y-actividades/carrera-solidaria/")]
    assert a.fichas_mec(b'[{"title":{"rendered":"Charla: correr sin lesiones, carrera"},"link":"x"}]') == []
    assert len(a.urls_mec("https://coslada.es", HOY)) == len(a.MEC_BUSQUEDAS)
    c, motivo = a.leer_ficha_mec(muestra("aytos_madrid-mec-ficha.html"), "https://x/", "Carrera solidaria",
                                 "Villanueva de la Cañada")
    assert not motivo
    assert (c.fecha, c.hora, c.poblacion) == (date(2026, 12, 13), "11:00", "Villanueva de la Cañada")
    assert b'"organizer": {}' in a.recortar_mec(b'<script type="application/ld+json">{"@type":"Event",'
                                                b'"organizer": {"name": "Fulano"}}</script>')


def test_web_oficial_con_jsonld():
    c, motivo = a.leer_web(muestra("aytos_madrid-alcorcon.html"), "https://www.sansilvestrealcorcon.com/", "Alcorcón", HOY)
    assert not motivo
    assert (c.nombre, c.fecha, c.hora, c.poblacion, c.provincia) == (
        "San Silvestre de Alcorcón", date(2026, 12, 12), "18:30", "Alcorcón", "Madrid")
    assert "deporticket.blob" not in (c.url_inscripcion or "")
    # Pasada la carrera, la web todavía enseña esa edición: no sale.
    c, motivo = a.leer_web(muestra("aytos_madrid-alcorcon.html"), "u", "Alcorcón", date(2027, 1, 5))
    assert c is None and "edición pasada" in motivo


def test_web_oficial_por_texto():
    rozas, _ = a.leer_web(muestra("aytos_madrid-lasrozas.html"), "https://www.sansilvestredelasrozas.es/",
                          "Las Rozas de Madrid", HOY)
    assert (rozas.fecha, rozas.hora, rozas.poblacion) == (date(2026, 12, 31), "10:00", "Las Rozas de Madrid")
    assert "San Silvestre" in rozas.nombre
    getafe, _ = a.leer_web(muestra("aytos_madrid-getafe.html"), "https://www.mediadegetafe.com/", "Getafe", HOY)
    assert (getafe.fecha, getafe.hora, getafe.distancias_km) == (date(2027, 1, 31), "10:30", [21.097])
    assert getafe.url_inscripcion.startswith("https://inscripciones.runrunsports.com/eventos/")
    sanse, _ = a.leer_web(muestra("aytos_madrid-sanse.html"), "https://sanselvestre.es/",
                          "San Sebastián de los Reyes", HOY)
    assert (sanse.fecha, sanse.hora) == (date(2026, 12, 27), "10:00")
    assert sanse.nombre.startswith("Sanselvestre 2026")


def test_primera_fecha_ignora_las_pasadas():
    assert a._primera_fecha("abre el 1 de junio de 2026 y la carrera es el 31 de enero de 2027", HOY) == date(2027, 1, 31)
    assert a._primera_fecha("Domingo, 27 de diciembre de 2026", HOY) == date(2026, 12, 27)
    assert a._primera_fecha("sin año: 8 de noviembre", HOY) is None


def test_leer_junta_todo_y_aguanta_fallos():
    def bajar(url, recortar=None):
        if "tribe/events" in url:
            if "manzanares" in url:
                return muestra("aytos_madrid-tec.json")
            raise RuntimeError("caída")
        if "mec-events" in url:
            return muestra("aytos_madrid-mec.json") if "villacanada" in url else b"[]"
        if "carrera-solidaria" in url:
            return muestra("aytos_madrid-mec-ficha.html")
        nombres = {"alcorcon": "alcorcon", "rozas": "lasrozas", "getafe": "getafe", "sanselvestre": "sanse"}
        for clave, n in nombres.items():
            if clave in url:
                return muestra(f"aytos_madrid-{n}.html")
        raise RuntimeError("no responde")

    carreras, descartes = a.leer(bajar, HOY, date(2027, 1, 31), hoy=HOY, bajar_ficha=bajar)
    nombres = {c.nombre for c in carreras}
    assert {"San Silvestre 2026", "Carrera solidaria", "San Silvestre de Alcorcón"} <= nombres
    assert len(carreras) == 6
    assert any("Colmenar" not in d and "agenda no disponible" in d for d in descartes)
    assert any("web oficial no disponible" in d and "colmenarviejo" in d for d in descartes)
