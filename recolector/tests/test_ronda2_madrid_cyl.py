"""Tests de la segunda ronda de lectores de Madrid y Castilla y León (copias recortadas del 17/11/2026)."""
from datetime import date, datetime

from fuentes import fetacyl, soriatletismo, timinglap
from tests.test_lectores import buscar, muestra


def test_timinglap():
    carreras, descartes = timinglap.leer(muestra("timinglap.html"))
    assert len(carreras) == 6 and not descartes
    c = buscar(carreras, "Cross Challenge los Fresnos")
    assert (c.fecha, c.hora, c.poblacion, c.provincia, c.modalidad) == (
        date(2026, 11, 22), "10:15", "Torrejón de Ardoz", "Madrid", "cross")
    assert c.inscripcion_hasta == datetime(2026, 11, 18, 14, 0)
    assert c.fuente.id == "timinglap"
    assert c.fuente.url.endswith("/inscripcion/i-cross-challenge-los-fresnos-torrejon-de-ardoz/")
    assert c.url_inscripcion == c.fuente.url
    daganzo = buscar(carreras, "Legua Nocturna")
    assert (daganzo.poblacion, daganzo.hora, daganzo.modalidad) == ("Daganzo de Arriba", "20:00", "asfalto")


def test_fetacyl_calendario_y_ficha():
    assert len(fetacyl.eventos(muestra("fetacyl.html"))) == 11
    recorte = fetacyl.recortar_ficha(muestra("fetacyl-ficha.html"))
    assert b"INSCRITOS" not in recorte and b"Laguna de Duero" in recorte
    assert fetacyl.lugar_de_ficha(recorte) == ("Laguna de Duero", "Valladolid")
    assert fetacyl.lugar_de_ficha("LUGAR: Barrio El Crucero (Burgos) ORGANIZADOR: X")[1] == "Burgos"
    assert fetacyl.lugar_de_ficha("FECHA DE LA PRUEBA: 22-11-2026") == (None, None)

    pedidas = []

    def bajar(url):
        pedidas.append(url)
        return recorte if "pavo" in url else b"FECHA DE LA PRUEBA: 22-11-2026"

    carreras, descartes = fetacyl.leer(muestra("fetacyl.html"), descargar_ficha=bajar,
                                       desde=date(2026, 11, 17), hasta=date(2026, 12, 31))
    pavo = buscar(carreras, "Pedestre del Pavo")
    assert (pavo.fecha, pavo.poblacion, pavo.provincia, pavo.fuente.id) == (
        date(2026, 12, 13), "Laguna de Duero", "Valladolid", "fetacyl")
    assert len(carreras) == 1  # las demás fichas de prueba no dicen el lugar
    assert any("Cerco a Numancia" in d and "sin lugar" in d for d in descartes)
    assert any("marcha en ruta" in d for d in descartes) and any("Clubes de Campo" in d for d in descartes)
    assert all("2026-03" not in u for u in pedidas)  # solo se abren las fichas del periodo
    assert not any("Cto." in u for u in pedidas)


def test_soriatletismo():
    portada = muestra("soriatletismo-portada.html")
    assert soriatletismo.temporadas(portada, date(2026, 11, 17), date(2026, 12, 31)) == [
        "https://soriatletismo.com/competiciones/temporada/14/temporada-2026"]
    carreras, descartes = soriatletismo.leer(muestra("soriatletismo.html"))
    cerco = buscar(carreras, "Cerco a Numancia")
    assert (cerco.fecha, cerco.poblacion, cerco.provincia) == (date(2026, 11, 22), "Garray", "Soria")
    royo = buscar(carreras, "Vilviestre Royana")
    assert (royo.fecha, royo.poblacion) == (date(2026, 12, 31), "El Royo")
    assert buscar(carreras, "Villa de Abejar").modalidad == "cross"
    assert buscar(carreras, "Medio Maraton Ciudad de Soria").poblacion == "Soria"  # lugar vacío: sale del nombre
    assert not descartes
