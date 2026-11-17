"""Ronda 4: Canarias (copias recortadas de las webs del 17/11/2026)."""
from datetime import date

from fuentes import canaryrun, holaislascanarias
from tests.test_lectores import buscar, muestra

DESDE, HASTA = date(2026, 11, 17), date(2027, 1, 31)


def _ficha_hola(url: str) -> bytes:
    return muestra("holaislascanarias-" + url.rstrip("/").split("/")[-1] + ".html")


def test_holaislascanarias_listado():
    eventos = holaislascanarias.listado(muestra("holaislascanarias.html"))
    assert len(eventos) == 8
    pino = next(e for e in eventos if e["nombre"] == "Trail Pino Santo")
    assert (pino["isla"], pino["fecha_texto"]) == ("Gran Canaria", "06 Diciembre 2026")
    assert pino["url"] == "https://www.holaislascanarias.com/eventos/gran-canaria/trail-pino-santo/"


def test_holaislascanarias():
    carreras, descartes = holaislascanarias.leer(muestra("holaislascanarias.html"), _ficha_hola, DESDE, HASTA)
    assert sorted(c.nombre for c in carreras) == ["La San Silvestre Garachiquense", "Playa Blanca Music Run Night",
                                                  "Trail Pino Santo"]
    pino = buscar(carreras, "Pino Santo")
    assert (pino.fecha, pino.poblacion, pino.provincia, pino.modalidad) == (
        date(2026, 12, 6), "Santa Brígida", "Las Palmas", "trail")
    assert pino.url_inscripcion == "https://trailpinosanto.com/"
    assert pino.fuente.url.endswith("/eventos/gran-canaria/trail-pino-santo/")
    assert pino.coords and 27.5 < pino.coords[0] < 29.5
    playa = buscar(carreras, "Playa Blanca")
    assert (playa.poblacion, playa.provincia) == ("Yaiza", "Las Palmas")
    assert playa.url_inscripcion == "https://summitsportsevents.com/"  # sin utm_ ni fbclid
    gara = buscar(carreras, "Garachiquense")
    assert (gara.fecha, gara.poblacion, gara.provincia) == (date(2026, 12, 31), "Garachico", "Santa Cruz de Tenerife")
    assert gara.url_inscripcion is None  # solo Facebook: no es una inscripción
    assert any("natación" in d and "Blue Challenge" in d for d in descartes)
    assert any("Open Water" in d for d in descartes) and any("Trail Bike" in d for d in descartes)
    assert any("sin día exacto (Ene 2027): Tenerguera" in d for d in descartes)
    assert any("4 al 6 Dic" in d for d in descartes)


def test_holaislascanarias_fecha():
    assert holaislascanarias._fecha("06 Diciembre 2026") == date(2026, 12, 6)
    assert holaislascanarias._fecha("1 Ene 2027") == date(2027, 1, 1)
    assert holaislascanarias._fecha("Ene 2027") is None
    assert holaislascanarias._fecha("4 al 6 Dic 2026") is None


def test_holaislascanarias_fuera_de_plazo_no_abre_fichas():
    abiertas = []
    holaislascanarias.leer(muestra("holaislascanarias.html"), lambda u: abiertas.append(u) or _ficha_hola(u),
                           date(2027, 1, 1), date(2027, 1, 31))
    assert abiertas == []


def test_canaryrun():
    carreras, descartes = canaryrun.leer(muestra("canaryrun.json"))
    assert [c.nombre for c in carreras] == ["Llano del Camello 2026", "Tenerguera Trail 8k",
                                            "Carrera de Montaña Guía de Isora"]
    llano = buscar(carreras, "Llano del Camello")
    assert (llano.fecha, llano.hora, llano.provincia) == (date(2026, 12, 6), "10:00", "Santa Cruz de Tenerife")
    assert llano.poblacion == "San Miguel de Abona"  # el lugar es un barrio: el municipio sale del ayuntamiento
    assert llano.url_inscripcion == "https://www.trivalleguimar.com/carrera-popular-llano-del-camello"
    teneguera = buscar(carreras, "Tenerguera")
    assert (teneguera.fecha, teneguera.poblacion, teneguera.modalidad, teneguera.distancias_km) == (
        date(2027, 1, 10), "Santiago del Teide", "trail", [8.0])
    assert teneguera.url_inscripcion == teneguera.fuente.url  # sin web propia: la ficha de CanaryRun
    assert buscar(carreras, "Guía de Isora").modalidad == "montaña"
    assert descartes == ["no es a pie: III Travesía The Blue Challenge"]
