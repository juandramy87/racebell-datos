"""Tests de los lectores de la zona centro (Madrid, Castilla-La Mancha, Castilla y León), copias del 17/11/2026."""
from datetime import date, datetime

from fuentes import dipualba, fam, orycronsport, timingsys, youevent
from tests.test_lectores import buscar, muestra


def test_youevent_calendario():
    carreras, descartes = youevent.leer(muestra("youevent.html"))
    assert len(carreras) == 42
    molar = buscar(carreras, "Iberika Trail - el Molar")
    assert (molar.fecha, molar.poblacion, molar.provincia, molar.modalidad) == (
        date(2026, 11, 21), "El Molar", "Madrid", "montaña")
    assert molar.fuente.url.endswith("id_competicion=8325")
    assert buscar(carreras, "Media Maraton Guadalajara").distancias_km == [11.0, 21.097]
    assert buscar(carreras, "Cantimpalos").provincia == "Segovia"
    assert buscar(carreras, "Estremera")  # «Carrera popular y marcha senderista»: hay carrera
    nombres = " ".join(c.nombre for c in carreras).lower()
    for fuera in ("duatl", "zumba", "dorsal 0", "curso", "infantil", "cicloturista", "escalada"):
        assert fuera not in nombres
    assert any("Marcha Popular Solidaria Cerro Marmota" in d for d in descartes)


def test_youevent_ficha():
    carreras, _ = youevent.leer(muestra("youevent.html"))
    c = buscar(carreras, "Iberika Trail - el Molar")
    youevent.leer_ficha(muestra("youevent-ficha.html"), c)
    assert c.inscripcion_desde == datetime(2026, 11, 3, 0, 0)
    assert c.inscripcion_hasta == datetime(2026, 11, 20, 23, 59)
    assert c.hora == "10:15"
    assert c.distancias_km == [7.1, 11.2, 18.1]  # sin el senderismo


def test_youevent_abre_solo_fichas_en_plazo():
    pedidas = []

    def bajar(url):
        pedidas.append(url)
        return muestra("youevent-ficha.html")

    youevent.leer(muestra("youevent.html"), descargar_ficha=bajar, desde=date(2026, 11, 21), hasta=date(2026, 11, 21))
    assert len(pedidas) == 2  # El Molar y Brihuega


def test_fam():
    carreras, descartes = fam.leer(muestra("fam.html"))
    assert len(carreras) == 53
    assert any("Suspendido" in d for d in descartes)
    c = buscar(carreras, "Cross Universidad Alfonso X")
    assert (c.fecha, c.poblacion, c.provincia, c.modalidad) == (
        date(2026, 11, 21), "Villanueva de la Cañada", "Madrid", "cross")
    sv = buscar(carreras, "San Silvestre Vallecana")
    assert sv.fecha == date(2026, 12, 31) and sv.url_inscripcion == "https://www.sansilvestrevallecana.com/"
    assert buscar(carreras, "Cross Ciudad de Alcorcón").url_inscripcion is None  # el reglamento es un PDF
    assert fam.urls(date(2026, 12, 1), date(2027, 1, 15))[-1].endswith("cal_year=2027")


def test_orycronsport():
    enlaces = orycronsport.enlaces(muestra("orycronsport.html"))
    assert len(enlaces) == 9
    carreras, descartes = orycronsport.leer(muestra("orycronsport.html"),
                                            descargar_ficha=lambda u: muestra("orycronsport-ficha.html"))
    assert any("BTT" in d for d in descartes) and any("Cicloturista" in d for d in descartes)
    c, motivo = orycronsport.leer_ficha(muestra("orycronsport-ficha.html"), "https://x",
                                        "II Carrera Popular Almenara de Tormes - Enusa", "Inscripciones abiertas")
    assert motivo is None
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 11, 22), "11:00", "Almenara de Tormes", "Salamanca")
    assert c.inscripcion_hasta == datetime(2026, 11, 19, 23, 59) and c.distancias_km == [10.0]
    assert orycronsport._provincia("El Barco de Ávila", "") == "Ávila"


def test_timingsys():
    eventos = timingsys.eventos(muestra("timingsys.html"))
    assert len(eventos) == 8
    carreras, descartes = timingsys.leer(muestra("timingsys.html"), descargar_ficha=lambda u: muestra("timingsys-ficha.html"))
    assert len(carreras) == 5  # fuera escuelas, entrenamiento solidario y ciclismo
    assert any("CYCLING" in d for d in descartes) and any("ENTRENAMIENTO" in d for d in descartes)
    ev = next(e for e in eventos if e["url"].endswith("/800"))
    c, _ = timingsys.leer_ficha(muestra("timingsys-ficha.html"), ev)
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 11, 21), "11:00", "Albacete", "Albacete")
    assert (c.inscripcion_desde, c.inscripcion_hasta) == (datetime(2026, 9, 29, 0, 0), datetime(2026, 11, 19, 19, 0))


def test_dipualba():
    carreras, _ = dipualba.leer([(muestra("dipualba.html"), None), (muestra("dipualba-trail.html"), "trail")])
    assert len(carreras) == 5
    c = buscar(carreras, "Navas de Jorquera")
    assert (c.fecha, c.poblacion, c.provincia, c.distancias_km) == (date(2026, 11, 28), "Navas de Jorquera", "Albacete", [8.0])
    t = buscar(carreras, "Trail Alcaraz")
    assert (t.modalidad, t.distancias_km) == ("trail", [16.7])
    assert dipualba.recortar(b'<img src="data:image/png;base64,AAAA==">') == b'<img src="">'


def test_timingsys_fichas_nueva_y_cronomancha():
    ev = {"url": "https://timingsys.com/event/809", "nombre": "XX Carrera de Navidad Jareña", "tipo": "A PIE",
          "fecha": date(2026, 12, 19)}
    c, _ = timingsys.leer_ficha(muestra("timingsys-ficha-nueva.html"), ev)
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 12, 19), "16:30", "Villanueva de la Jara", "Cuenca")
    assert c.inscripcion_hasta == datetime(2026, 12, 17, 23, 59)
    ev = {"url": "https://timingsys.com/event/808", "nombre": "CARRERA DE NAVIDAD DE MANZANARES 2026", "tipo": "A PIE",
          "fecha": date(2026, 12, 20)}
    c, _ = timingsys.leer_ficha(muestra("timingsys-ficha-cronomancha.html"), ev)
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 12, 20), "11:00", "Manzanares", "Ciudad Real")
    assert c.inscripcion_hasta is None  # el plazo que muestra es de la edición de 2025
    assert timingsys._provincia_en("43 Edición Carrera del Pavo Cuenca 2026") == "Cuenca"


def test_orycronsport_distancias():
    texto = "Día:\nDomingo 27 de Diciembre de 2026\nLugar:\nEl Barco de Ávila\nRecorrido:\n300m - 650m - 3,2km - 6,2km\n* Nota"
    c, _ = orycronsport.leer_ficha(texto, "https://x", "XIV San Silvestre Solidaria Barcense")
    assert (c.distancias_km, c.provincia) == ([3.2, 6.2], "Ávila")
