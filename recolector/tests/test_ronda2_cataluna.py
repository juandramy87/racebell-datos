"""Segunda ronda de Cataluña (17/11/2026): Athletic Events (Tarragona), Gesport (Maresme, Circuit Maresmenc de
Cros), Circuit de Curses del Pla de l'Estany y CronoCheck. Muestras recortadas en tests/muestras/ (sin datos
personales: solo listados, el título de una página y el JSON-LD de una ficha)."""
from datetime import date

from fuentes import athleticevents, cronocheck, gesportcat, plaestany
from fuentes import cataluna as cat
from tests.test_lectores import buscar, muestra


def test_marato_de_3cat_no_es_un_maraton():
    assert cat.distancias("15a Cursa i Caminada Solidària per la Marató 3Cat - TGN") == []
    assert cat.distancias("Junts per la Marató de 3Cat 2026 Sant Boi") == []
    assert cat.distancias("Cursa de La Marató de TV3 (5 i 10 Km)") == [5.0, 10.0]
    assert cat.distancias("37a Mitja Marató i 10K Ciutat de Vilanova") == [10.0, 21.097]


def test_athleticevents():
    carreras, descartes = athleticevents.leer(muestra("athleticevents.html"))
    assert len(carreras) == 3
    c = buscar(carreras, "Sant Silvestre de Tarragona")
    assert (c.fecha, c.poblacion, c.provincia) == (date(2026, 12, 31), "Tarragona", "Tarragona")
    assert c.fuente.url == "https://www.athleticevents.net/cursa/22a-cursa-sant-silvestre-de-tarragona-542"
    assert buscar(carreras, "Marató 3cat").poblacion == "Tarragona"  # «TGN»
    assert buscar(carreras, "Perafort").poblacion == "Perafort"  # «PERAFORT I PUGDELFÍ»
    assert any("Marxa Altafulla" in d for d in descartes)  # marcha: no es a pie


def test_gesportcat_circuit_maresmenc():
    carreras, descartes = gesportcat.leer_circuit(muestra("gesportcat-circuit.html"))
    pueblos = {c.nombre: c.poblacion for c in carreras}
    assert pueblos["9è Cros de Pineda"] == "Pineda de Mar"
    assert pueblos["31è Cros de Malgrat"] == "Malgrat de Mar"
    assert pueblos["46è Cros dels Arenys"] == "Arenys de Mar"
    assert pueblos["4rt Cros semi urbà de Llavaneres"] == "Sant Andreu de Llavaneres"
    assert pueblos["32è Cros Ciutat de Calella"] == "Calella"
    c = buscar(carreras, "Cros d’Alella")
    assert (c.fecha, c.provincia, c.modalidad) == (date(2026, 12, 13), "Barcelona", "cross")
    assert buscar(carreras, "Tordera").fecha == date(2026, 10, 17)  # «17 d’octubre»
    assert any("Santa Susanna" in d for d in descartes)  # AJORNAT
    assert all("Circuit Maresmenc" in c.previos[0] for c in carreras)


def test_gesportcat_portada():
    assert gesportcat.enlaces_portada(muestra("gesportcat-portada.html")) == [
        ("https://gesport.cat/cursa-la-5k-de-sant-vicenc-de-montalt/", date(2026, 12, 20))]
    carreras, _ = gesportcat.leer(muestra("gesportcat-portada.html"), muestra("gesportcat-circuit.html"),
                                  descargar_ficha=lambda url: muestra("gesportcat-5k.html"))
    c = buscar(carreras, "5K de Sant Vicenç")
    assert (c.poblacion, c.provincia, c.distancias_km) == ("Sant Vicenç de Montalt", "Barcelona", [5.0])


def test_plaestany():
    carreras, descartes = plaestany.leer(muestra("plaestany.html"))
    assert len(carreras) == 6 and not descartes
    c = buscar(carreras, "Marxa Popular de Banyoles")
    assert (c.fecha, c.poblacion, c.provincia, c.distancias_km) == (date(2026, 11, 22), "Banyoles", "Girona", [6.6])
    assert buscar(carreras, "Porqueres").fecha == date(2026, 12, 8)
    assert buscar(carreras, "Run-Run").poblacion == "Cornellà del Terri"
    assert buscar(carreras, "Fontcoberta").fuente.url == "https://cursesplaestany.cat/cursa-popular-fontcoberta/"


def test_cronocheck():
    fichas = []

    def ficha(url):
        fichas.append(url)
        return muestra("cronocheck-ficha.html")

    carreras, descartes = cronocheck.leer(muestra("cronocheck.html"), descargar_ficha=ficha, hoy=date(2026, 11, 17))
    c = buscar(carreras, "Sant Silvestre Manresana")
    assert (c.fecha, c.poblacion, c.provincia) == (date(2026, 12, 26), "Manresa", "Barcelona")
    assert buscar(carreras, "Junts per la Marató").poblacion == "Sant Boi de Llobregat"
    assert buscar(carreras, "Cardedeu").fecha == date(2026, 12, 12)
    assert not any("Múixing" in c.nombre or "Canicross" in c.nombre for c in carreras)
    assert any("solo para socios" in d for d in descartes)  # Trail dels Íbers
    assert not any("Familiar per la Vida Girona" in c.nombre for c in carreras)  # ya pasó (15/11)
    assert cronocheck.lugar_de_ficha(muestra("cronocheck-ficha.html")) is None  # «No disponible»
