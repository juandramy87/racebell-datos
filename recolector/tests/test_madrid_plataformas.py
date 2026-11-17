"""Tests de Madrid (ciudad y plataformas comunes): barrios de la capital, fichas de RockTheSport que el lector
general descarta y la Carrera de las Ciudades contra el Cáncer de Páncreas (copias recortadas del 17/11/2026)."""
from datetime import date, datetime

from fuentes import cancerpancreas, madridcapital, rtsmadrid
from tests.test_lectores import buscar, muestra


def test_barrios_de_madrid():
    assert madridcapital.barrio("10K / 5K Sanchinarro 2027") == "Sanchinarro"
    assert madridcapital.barrio("Casco Histórico de Barajas") == "Casco Histórico de Barajas"
    assert madridcapital.lugar("Hortaleza") == madridcapital.MADRID
    assert madridcapital.lugar("XXIII Cross Popular Salvar el Pinar de la Elipa") == madridcapital.MADRID
    # Nombres que se confunden: solo con coordenadas en el término de Madrid.
    assert madridcapital.lugar("Hellín") is None
    assert madridcapital.lugar("Hellín", coords=(40.43, -3.62)) == madridcapital.MADRID
    assert madridcapital.lugar("Hortaleza", coords=(38.51, -1.70)) is None  # coordenadas de Hellín (Albacete)
    assert madridcapital.lugar("Carrera de Alcobendas") is None
    assert madridcapital.es_de_madrid("Embajadores") and madridcapital.es_de_madrid("Puerta Bonita")
    assert not madridcapital.es_de_madrid("Getafe")


def _vistos():
    sin = {"espana": False, "v2": True, "motivo": "fuera de España o sin provincia: X (None)"}
    return {
        "10k-5k-sanchinarro-2027": sin,
        "xi-san-silvestre-de-hortaleza-2026": sin,
        "xxiii-cross-popular-salvar-el-pinar-de-la-elipa": {"espana": False, "motivo":
                                                            "coordenadas fuera del municipio del nombre"},
        "i-trail-de-la-picota-de-pezuela-de-las-torres": {"espana": False, "motivo":
                                                          "coordenadas fuera del municipio del nombre"},
        "ibiza-media-maraton-2027": sin,
        "duatlon-de-carabanchel": sin,  # no es a pie: ni se abre
        "carrera-de-getafe": {"espana": True, "provincia": "Madrid", "fecha": "2026-12-01"},  # ya la lee rockthesport
        "trofeo-de-pueblo": sin,  # sin pista de Madrid en el slug: ni se abre
    }


def test_rtsmadrid_candidatas():
    assert rtsmadrid.candidatas(_vistos()) == [
        "10k-5k-sanchinarro-2027", "i-trail-de-la-picota-de-pezuela-de-las-torres", "ibiza-media-maraton-2027",
        "xi-san-silvestre-de-hortaleza-2026", "xxiii-cross-popular-salvar-el-pinar-de-la-elipa"]
    assert rtsmadrid.municipio_madrid("I Trail de la Picota de Pezuela de las Torres") == "Pezuela de las Torres"
    assert rtsmadrid.municipio_madrid("Ibiza Media Maratón") is None


def test_rtsmadrid_lee_fichas():
    pedidas = []

    def bajar(url):
        pedidas.append(url)
        slug = url.rsplit("/", 1)[-1]
        return muestra(f"rtsmadrid-{slug[:30]}.html")

    carreras, descartes = rtsmadrid.leer(_vistos(), descargar_ficha=bajar,
                                         desde=date(2026, 11, 17), hasta=date(2027, 1, 31))
    assert len(pedidas) == 5
    sanchinarro = buscar(carreras, "Sanchinarro")
    assert (sanchinarro.fecha, sanchinarro.hora, sanchinarro.poblacion, sanchinarro.provincia) == (
        date(2027, 1, 24), "10:00", "Madrid", "Madrid")
    assert sanchinarro.inscripcion_hasta == datetime(2027, 1, 22, 21, 0)
    assert sanchinarro.fuente.id == "rtsmadrid"
    assert sanchinarro.fuente.url == "https://web.rockthesport.com/es/event/10k-5k-sanchinarro-2027"
    assert "Inscripciones agotadas" not in sanchinarro.previos  # RockTheSport dice SoldOut en todas
    hortaleza = buscar(carreras, "San Silvestre de Hortaleza")
    assert (hortaleza.fecha, hortaleza.poblacion) == (date(2026, 12, 19), "Madrid")
    assert "Barrio o distrito: Hortaleza" in hortaleza.previos
    elipa = buscar(carreras, "Pinar de la Elipa")
    assert (elipa.fecha, elipa.poblacion, elipa.modalidad) == (date(2026, 11, 22), "Madrid", "cross")
    assert len(carreras) == 3  # Pezuela (septiembre) queda fuera del periodo; Ibiza no es de Madrid
    assert any("ibiza-media-maraton" in d for d in descartes)

    todas, _ = rtsmadrid.leer(_vistos(), descargar_ficha=bajar, desde=date(2026, 1, 1), hasta=date(2027, 12, 31))
    pezuela = buscar(todas, "Pezuela")
    assert (pezuela.fecha, pezuela.poblacion, pezuela.provincia, pezuela.modalidad) == (
        date(2026, 9, 12), "Pezuela de las Torres", "Madrid", "trail")


def test_cancerpancreas():
    carreras, descartes = cancerpancreas.leer(muestra("cancerpancreas.html"))
    assert not descartes and len(carreras) == 7
    madrid = buscar(carreras, "Páncreas - Madrid")
    assert (madrid.fecha, madrid.poblacion, madrid.provincia, madrid.modalidad) == (
        date(2026, 11, 22), "Madrid", "Madrid", "asfalto")
    assert madrid.fuente.url == "https://carreracancerpancreas.es/carrera-madrid/" == madrid.url_inscripcion
    assert madrid.fuente.id == "cancerpancreas"
    vila = buscar(carreras, "Vilamartín")
    assert (vila.fecha, vila.poblacion, vila.provincia) == (date(2026, 11, 15), "Vilamartín de Valdeorras", "Ourense")
    assert vila.fuente.url.endswith("/carrera-vilamartin/")
    bcn = buscar(carreras, "Barcelona")
    assert (bcn.fecha, bcn.provincia) == (date(2026, 12, 13), "Barcelona")
    assert "/cursa-barcelona/" in bcn.fuente.url
    assert buscar(carreras, "Santiago").provincia == "A Coruña"
    assert not any("virtual" in c.nombre.lower() for c in carreras)
