from datetime import date, datetime

from nucleo import normalizar as nz
from nucleo.duplicados import deduplicar, misma_carrera
from nucleo.modelo import Carrera, Fuente


def carrera(nombre, fuente, poblacion=None, fecha=date(2026, 11, 22), **extra):
    return Carrera(nombre=nombre, fecha=fecha, fuente=Fuente(fuente, f"https://{fuente}/x"), poblacion=poblacion, **extra)


def test_nombre_en_mayusculas_a_titulo():
    assert nz.nombre("XIII CARRERA LA CORDOBARIA NAVIDAD 2026") == "XIII Carrera la Cordobaria Navidad 2026"
    assert nz.nombre("“VI CXM TOLETA”") == "VI CxM Toleta"
    assert nz.nombre("We Run UMA") == "We Run UMA"  # si no viene en mayúsculas, no se toca


def test_clasificar():
    assert nz.clasificar("XXXIX Cross Pinares Cartaya") == (True, "cross")
    assert nz.clasificar("VI CxM Toleta") == (True, "montaña")
    assert nz.clasificar("Media Maratón de Roquetas") == (True, "asfalto")
    # Duatlones (hay bici) y escalada no son carreras a pie, aunque digan «cross».
    assert nz.clasificar("VII Duatlón Cros Rincón") == (False, None)
    assert nz.clasificar("II Duatlón Cross Tres Arroyos") == (False, None)
    assert nz.clasificar("VI Open Boulder Ciudad de Valladolid") == (False, None)
    assert nz.clasificar("XXXIV Cursa del Club Natació Sabadell")[0] is True
    assert nz.clasificar("III BTT Desierto de Gorafe")[0] is False
    assert nz.clasificar("KDD Mountainbike Jubrique")[0] is False
    assert nz.clasificar("I Encuentro de Mujeres Marchadoras")[0] is False


def test_provincia():
    assert nz.provincia("MALAGA") == "Málaga"
    assert nz.provincia("Jaén ") == "Jaén"
    assert nz.provincia("Madrid") == "Madrid" and nz.provincia("Vizcaya") == "Bizkaia"
    assert nz.provincia("Illes Balears") == "Baleares" and nz.provincia("Francia") is None
    assert nz.comunidad("Lleida") == "cataluna" and nz.provincia_por_cp("48001") == "Bizkaia"


def test_une_la_misma_carrera_de_dos_fuentes():
    a = carrera("XXXIX Cross Pinares Cartaya", "dorsalchip", "Cartaya", inscripcion_hasta=datetime(2026, 11, 19, 14))
    b = carrera("Pinares de Cartaya", "faa", cartel="https://faa/cartel.webp")
    b.marcar("Población, precio, cierre y previos solo en el cartel", "pendiente_cartel")
    assert misma_carrera(a, b)
    unicas, registro = deduplicar([a, b])
    assert len(unicas) == 1 and len(registro) == 1
    u = unicas[0]
    assert u.fuente.id == "dorsalchip" and [f.id for f in u.otras_fuentes] == ["faa"]
    assert u.cartel == "https://faa/cartel.webp"  # el hueco se rellena con la otra fuente
    assert [t for _, t in u.avisos_calidad] == ["Precio y previos solo en el cartel de la FAA"]


def test_no_une_carreras_distintas():
    a = carrera("X San Silvestre de Torremolinos", "dorsalchip", "Torremolinos")
    b = carrera("San Silvestre Lantejuela 2026", "tecnocrono", "Lantejuela")
    c = carrera("5Km y 10Km XI Carrera Holiday World", "dorsalchip", "Benalmádena")
    d = carrera("Media Maratón XI Carrera Holiday World", "dorsalchip", "Benalmádena")
    e = carrera("XXXIX Cross Pinares Cartaya", "faa", fecha=date(2026, 11, 29))
    assert not misma_carrera(a, b)
    assert not misma_carrera(c, d)  # misma fuente: son pruebas distintas
    assert len(deduplicar([a, b, c, d, e])[0]) == 5


def test_sesca_toma_la_provincia_de_otra_fuente():
    a = carrera("V Cross Rural Torrecera", "sesca", "Torrecera", provincia="Cádiz")
    a.marcar("Provincia supuesta (Cádiz): Sesca no la indica", "pendiente_cartel")
    b = carrera("V Cross Rural Torrecera", "dorsalchip", "Torrecera", provincia="Cádiz",
                inscripcion_hasta=datetime(2026, 11, 20))
    u = deduplicar([a, b])[0][0]
    assert not any("Provincia supuesta" in t for _, t in u.avisos_calidad)
