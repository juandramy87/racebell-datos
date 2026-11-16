from datetime import date

from fuentes import rockthesport
from tests.test_lectores import muestra


def test_rockthesport_solo_abre_fichas_andaluzas_de_carreras(tmp_path):
    abiertas = []

    bilbao = (b'<script type="application/ld+json">{"@type":"SportsEvent","name":"XXXI Carrera Las Arenas",'
              b'"startDate":"2026-12-06T10:00:00","location":{"address":{"addressLocality":"Getxo"},'
              b'"geo":{"latitude":"43.33","longitude":"-3.01"}}}</script>')

    def descargar_ficha(url):
        abiertas.append(url)
        return bilbao if "bilbao" in url else muestra("rockthesport-fonelas.html")

    carreras, _ = rockthesport.leer(muestra("rockthesport-sitemap.xml"), descargar_ficha=descargar_ficha,
                                    desde=date(2026, 11, 16), hasta=date(2026, 12, 31),
                                    ruta_vistos=tmp_path / "vistos.json")
    assert not any("marcha" in u for u in abiertas)  # las marchas ni se abren
    assert len(carreras) == 1  # «Las Arenas» parece el municipio malagueño Arenas, pero sus coordenadas son de Bizkaia
    c = carreras[0]
    assert (c.fecha, c.hora, c.poblacion, c.provincia) == (date(2026, 11, 22), "09:45", "Fonelas", "Granada")
    abiertas.clear()
    rockthesport.leer(muestra("rockthesport-sitemap.xml"), descargar_ficha=descargar_ficha,
                      desde=date(2026, 11, 16), hasta=date(2026, 12, 31), ruta_vistos=tmp_path / "vistos.json")
    assert not any("bilbao" in u for u in abiertas)  # la ficha no andaluza ya no se vuelve a abrir


def test_rockthesport_abre_una_vez_las_fichas_sin_municipio_en_el_nombre(tmp_path):
    sitemap = ('<loc>https://web.rockthesport.com/es/event/xviii-calamorro-skyrace</loc>'
               '<loc>https://web.rockthesport.com/es/event/trail-de-los-picos</loc>')
    malaga = (b'<script type="application/ld+json">{"@type":"SportsEvent","name":"XVIII Calamorro Skyrace",'
              b'"startDate":"2027-03-07T09:00:00","location":{"address":{"addressLocality":"Benalm\xc3\xa1dena",'
              b'"addressRegion":"M\xc3\xa1laga","postalCode":"29639"}}}</script>')
    leon = (b'<script type="application/ld+json">{"@type":"SportsEvent","name":"Trail de los Picos",'
            b'"startDate":"2027-05-01T09:00:00","location":{"address":{"addressLocality":"Riano",'
            b'"addressRegion":"Le\xc3\xb3n","postalCode":"24900"}}}</script>')
    abiertas = []

    def descargar_ficha(url):
        abiertas.append(url)
        return malaga if "calamorro" in url else leon

    leer = lambda: rockthesport.leer(sitemap, descargar_ficha=descargar_ficha, desde=date(2026, 11, 16),
                                     hasta=date(2027, 12, 31), ruta_vistos=tmp_path / "vistos.json")
    carreras, _ = leer()
    assert [(c.nombre, c.provincia) for c in carreras] == [("XVIII Calamorro Skyrace", "Málaga"), ("Trail de los Picos", "León")]
    abiertas.clear()
    leer()
    assert abiertas  # las de España se vuelven a abrir para seguir sus cambios
