"""Lectores de Baleares, Canarias, Aragón y Extremadura (copias guardadas el 17/11/2026)."""
from datetime import date, datetime

from fuentes import atletismoaragon, elitechip, faex, faib, gesport
from tests.test_lectores import buscar, muestra


def test_elitechip_tipo_manda_y_cierre_con_hora():
    carreras, descartes = elitechip.leer([muestra("elitechip.json")])
    assert {c.provincia for c in carreras} == {"Baleares"}
    c = buscar(carreras, "S’Hostal de Montuïri")
    assert (c.fecha, c.poblacion, c.modalidad) == (date(2026, 12, 8), "Montuïri", "asfalto")
    assert c.inscripcion_hasta == datetime(2026, 12, 7, 21, 0)
    assert c.fuente.url == "https://www.elitechip.net/es/competiciones/xii-carrera-de-s-hostal-de-montuiri-2026"
    assert buscar(carreras, "Cursa Des Tro").modalidad == "trail"  # tipo «TrailRunning»
    assert buscar(carreras, "Muntanyes d'Artà").modalidad == "montaña"  # tipo «Cursa per Muntanya»
    assert buscar(carreras, "Mini Marató Formentera").poblacion == "Formentera"
    assert buscar(carreras, "Urban Race Rafa Nadal").poblacion == "Manacor"
    nombres = " ".join(c.nombre for c in carreras)
    for fuera in ("Duatló", "Hyrotxí", "Passa-Passa", "Sitra", "Camina", "Puig Roig KIDS", "Sant Silvestre Kids"):
        assert fuera not in nombres, fuera
    assert any("Duatlón" in d for d in descartes) and any("solo infantil" in d for d in descartes)


def test_elitechip_un_mes_por_peticion_y_recorte():
    urls = elitechip.urls(date(2026, 11, 17), date(2027, 1, 16))
    assert [u.split("fromDate=")[1][:10] for u in urls] == ["2026-11-01", "2026-12-01", "2027-01-01"]
    assert "toDate=2026-11-30" in urls[0]
    recortado = elitechip.recortar(b'[{"id": 1, "nombreCompeticion": "X", "estado": {"inscritos": 100}}]')
    assert b"inscritos" not in recortado and b'"X"' in recortado


def test_elitechip_municipios():
    assert elitechip.municipio("bar-restaurant s'hostal (c/ constitucio, s/n) mallorca montuiri") == "Montuïri"
    assert elitechip.municipio("pista de atletismo de magaluf magaluf") == "Calvià"
    assert elitechip.municipio("ciutadella de menorca") == "Ciutadella de Menorca"
    assert elitechip.municipio("Cursa del Consell de Mallorca") is None


def test_faib_calendario_por_modalidad():
    carreras, descartes = faib.leer([muestra(f"faib-{m}.html") for m in faib.MODALIDADES])
    c = buscar(carreras, "Mitja marató & 10 km Porreres")
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 11, 22), "10:00", "Porreres", "Baleares")
    assert c.distancias_km == [10.0, 21.097]  # «Mitja marató & 10 km»
    assert buscar(carreras, "Sa Sobrassada").hora == "16:30"
    assert buscar(carreras, "Cursa Ruta 09 Alcudia").hora is None  # «00:10» = sin hora
    assert buscar(carreras, "Emilio de la Cámara").modalidad == "cross"
    assert buscar(carreras, "Trail dels Fars").modalidad == "trail"
    assert buscar(carreras, "San Silvestre Palma").poblacion == "Palma"
    assert buscar(carreras, "Hostal de Montuïri").nombre == "Cursa S’Hostal de Montuïri 2026"  # sin «– Campeonato IB…»
    assert sum(c.nombre == "3 Días Trail Ibiza 2026" for c in carreras) == 1  # larga y ultra: un solo evento
    nombres = " ".join(c.nombre for c in carreras)
    assert "Control" not in nombres and "Kids" not in nombres and "Atletisme Adaptat" not in nombres
    assert any("control" in d for d in descartes)


def test_atletismo_aragon():
    carreras, descartes = atletismoaragon.leer([muestra("atletismoaragon-1.html"), muestra("atletismoaragon-2.html")])
    c = buscar(carreras, "Mularroya Trail")
    assert c.nombre == "XX Mularroya Trail"  # sin «(Auton)»
    assert (c.fecha, c.poblacion, c.provincia, c.modalidad) == (date(2026, 11, 22), "La Almunia de Doña Godina",
                                                               "Zaragoza", "trail")
    assert buscar(carreras, "Cross de la Montaña").modalidad == "cross"  # el tipo Campo a Través manda
    assert buscar(carreras, "San Silvestre Barbastro").provincia == "Huesca"
    assert buscar(carreras, "Ciudad de Teruel").provincia == "Teruel"
    assert buscar(carreras, "Ciudad de Cariñena").poblacion == "Cariñena"  # la FAA pone «Zaragoza»
    assert buscar(carreras, "Fuentes de Ebro").distancias_km == [5.0, 10.0]
    assert not any("Short Track" in c.nombre or "Control" in c.nombre for c in carreras)
    assert any("Pista Cubierta" in d for d in descartes)
    assert atletismoaragon.urls(date(2026, 11, 17))[1].endswith("?yyy=2027")


def test_atletismo_aragon_municipios():
    assert atletismoaragon.municipio("Palacio de los deportes (zaragoza)") == ("Zaragoza", "Zaragoza")
    assert atletismoaragon.municipio("Zaragoza estadio corona de aragón") == ("Zaragoza", "Zaragoza")
    assert atletismoaragon.municipio("Frescano") == ("Fréscano", "Zaragoza")
    assert atletismoaragon.municipio("Burgos") == (None, None)


def test_faex():
    carreras, descartes = faex.leer([muestra("faex.html")])
    c = buscar(carreras, "Media Maratón Ciudad de Trujillo")
    assert (c.fecha, c.poblacion, c.provincia, c.distancias_km) == (date(2026, 12, 20), "Trujillo", "Cáceres", [21.097])
    assert buscar(carreras, "Guadajira").provincia == "Badajoz"  # pedanía, no está en la tabla de municipios
    assert buscar(carreras, "Cross Navideño Valdelacalzada").modalidad == "cross"
    nombres = " ".join(c.nombre for c in carreras)
    for fuera in ("Control de Marcas", "Jornada", "Campeonato de España", "Marcha", "Milla en Pista"):
        assert fuera not in nombres, fuera
    assert any("Campeonato de España de Marcha" in d for d in descartes)
    assert faex.municipio("La Garrovilla") == ("La Garrovilla", "Badajoz")
    assert faex.municipio("Castro Urdiales") == (None, None)


def test_faex_paginas():
    html = muestra("faex.html")
    assert faex.calendarios(html, date(2026, 11, 17)) == ["https://www.atletismo-ext.com/es/calendario-181/2026"]
    otras = faex.otras_paginas(html, "https://www.atletismo-ext.com/es/calendario-181/2026")
    assert otras[0].endswith("?pagina=2") and len(otras) == 5


def test_gesport_y_ficha_chronotrack():
    fichas, descartes = gesport.enlaces(muestra("gesport.html"))
    url = "https://inscripciones.chronotrackcanarias.com/inscripcion/xxxvi-media-maraton-ciudad-de-tacoronte-2026/"
    assert url in fichas and fichas[url] == "running"
    assert not any("pedaleando" in u or "hybrid" in u or "echo-hy" in u for u in fichas)
    assert any("HYBRID" in d for d in descartes) and any("CICLISMO" in d for d in descartes)
    ficha = muestra("gesport-ficha.html")
    carreras, _ = gesport.leer(muestra("gesport.html"), descargar_ficha=lambda u: ficha if u == url else b"")
    c = buscar(carreras, "Tacoronte")
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 12, 20), "08:30", "Tacoronte",
                                                         "Santa Cruz de Tenerife")
    assert c.inscripcion_hasta == datetime(2026, 12, 16, 23, 59)
    assert {"nombre": "Media Maraton", "euros": 28.0} in c.precios
