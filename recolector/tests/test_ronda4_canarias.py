"""Ronda 4: Canarias (copias recortadas de las webs del 17/11/2026)."""
from datetime import date

from fuentes import canaryrun, holaislascanarias
from tests.test_lectores import buscar, muestra

DESDE, HASTA = date(2026, 11, 17), date(2027, 1, 31)


def _html(texto: str) -> str:
    import json
    return '<script>self.__next_f.push([1,' + json.dumps(texto) + '])</script>'


EV = [
    {"id": "1", "title": "San Silvestre Lagunera", "url": "/eventos/tenerife/ssl/", "resourceType": "agenda",
     "island": "Tenerife", "municipality": "San Cristóbal de La Laguna", "dateFrom": "2026-12-31",
     "dateTo": "2026-12-31", "coordinates": {"lat": 28.48, "lng": -16.31}},
    {"id": "2", "title": "Tamadaba Trail", "url": "/eventos/gran-canaria/tamadaba-trail/", "resourceType": "agenda",
     "island": "Gran Canaria", "municipality": "Agaete", "dateFrom": "", "dateTo": "",
     "estimatedMonth": "Noviembre", "estimatedYear": 2026},
    {"id": "3", "title": "Maratón Corralejo", "url": "/eventos/fuerteventura/mc/", "resourceType": "agenda",
     "island": "Fuerteventura", "municipality": "La Oliva", "dateFrom": "", "dateTo": "",
     "estimatedMonth": "Diciembre", "estimatedYear": 2026},
    {"id": "4", "title": "The Blue Challenge", "url": "/eventos/tenerife/tbc/", "resourceType": "agenda",
     "island": "Tenerife", "description": "Travesía a nado en aguas abiertas", "dateFrom": "2026-12-05",
     "dateTo": "2026-12-05"},
]


def _ficha(url):
    import json
    if "tamadaba" in url:  # un mes entero: no es un día
        ld = '{"@graph":[{"@type":"Event","startDate":"2026-11-01T00:00:00+0000","endDate":"2026-11-30T00:00:00+0000"}]}'
        return json.dumps({"ld": ld, "web": None}).encode()
    ld = '{"@graph":[{"@type":"Event","startDate":"2026-12-12T00:00:00+0000","endDate":"2026-12-12T00:00:00+0000"}]}'
    return json.dumps({"ld": ld, "web": '"goToWebsiteButton":{"label":"Ver la web","url":"https://www.maratoncorralejo.com/?utm_source=x"}'}).encode()


def test_holaislascanarias_pagina_y_municipios():
    t = ('"id":"municipality","availableItems":[{"id":"arona","count":2},{"id":"fasnia","count":0}]'
         ',"selected":["' + holaislascanarias.CATEGORIA + '"],"resources":[{"id":"1","resourceType":"agenda"},'
         '{"id":"x","resourceType":"cruise"}],"totalResults":23')
    eventos, total, filtrado = holaislascanarias.pagina(_html(t))
    assert (len(eventos), total, filtrado) == (1, 23, True)
    assert holaislascanarias.municipios(_html(t)) == ["arona"]
    assert holaislascanarias.pagina(_html('"resources":[],"totalResults":0'))[2] is False  # sin filtrar


def test_holaislascanarias():
    carreras, descartes = holaislascanarias.leer(EV, _ficha, DESDE, HASTA)
    assert sorted(c.nombre for c in carreras) == ["Maratón Corralejo", "San Silvestre Lagunera"]
    ssl = buscar(carreras, "Lagunera")
    assert (ssl.fecha, ssl.poblacion, ssl.provincia) == (date(2026, 12, 31), "San Cristóbal de La Laguna",
                                                         "Santa Cruz de Tenerife")
    mc = buscar(carreras, "Corralejo")
    assert (mc.fecha, mc.provincia, mc.url_inscripcion) == (date(2026, 12, 12), "Las Palmas", "https://www.maratoncorralejo.com/")
    assert any("sin día exacto" in d and "Tamadaba" in d for d in descartes)
    assert any("natación" in d and "Blue Challenge" in d for d in descartes)


def test_holaislascanarias_web_cortada():
    assert holaislascanarias._web("https://inscripciones.conchipcanarias.com/inscripcion/xii-5km…") is None


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
