"""Federación Aragonesa de Atletismo (FAA): «Calendario y Resultados FAA»
(`federacionaragonesadeatletismo.com/competiciones/calendario-y-resultados-faa/2021-2/`). Lista HTML con fecha,
nombre, tipo de prueba (Ruta, Campo a Través, Montaña-Trail, Pista…) y lugar. Sin parámetro muestra las
próximas del año en curso; `?yyy=2027` da las del año siguiente. Se quedan Ruta, Campo a Través y
Montaña-Trail. La provincia sale del municipio (tabla de los 731 municipios de Aragón, de Wikipedia).
robots.txt: prohíbe /files/, /images/, /admin/, /libs/ y /settings/; el calendario se puede leer."""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Optional

from bs4 import BeautifulSoup

from nucleo import normalizar as nz
from nucleo.modelo import Carrera, Fuente

ID = "atletismoaragon"
URL = "https://www.federacionaragonesadeatletismo.com/competiciones/calendario-y-resultados-faa/2021-2/"
_TIPOS = {"ruta": "asfalto", "campo a traves": "cross", "montana trail": "trail"}
# Etiquetas de la FAA que no son parte del nombre: «(Auton)», «(Local)», «(Homologada)», «(No homologado)»…
_ETIQUETAS = re.compile(r"\s*\((?:auton|local|rfea|internacional[^)]*|(?:no )?homologad[oa][^)]*)\)", re.I)

# Municipios de Aragón por provincia (Wikipedia, «Anexo:Municipios de la provincia de …», 11/2026).
_MUNICIPIOS = {
    "Huesca": (
        "Abiego|Abizanda|Adahuesca|Agüero|Aínsa-Sobrarbe|Aísa|Albalate de Cinca|Albalatillo|Albelda|Albero Alto|"
        "Albero Bajo|Alberuela de Tubo|Alcalá de Gurrea|Alcalá del Obispo|Alcampell|Alcolea de Cinca|Alcubierre|"
        "Alerre|Alfántega|Almudévar|Almunia de San Juan|Almuniente|Alquézar|Altorricón|Angüés|Ansó|Antillón|"
        "Aragüés del Puerto|Arén|Argavieso|Arguis|Ayerbe|Azanuy-Alins|Azara|Azlor|Baélls|Bailo|Baldellou|Ballobar|"
        "Banastás|Barbastro|Barbués|Barbuñales|Bárcabo|Belver de Cinca|Benabarre|Benasque|Beranuy|Berbegal|Bielsa|"
        "Bierge|Biescas|Binaced|Binéfar|Bisaurri|Biscarrués|Blecua y Torres|Boltaña|Bonansa|Borau|Broto|"
        "Caldearenas|Campo|Camporrélls|Canal de Berdún|Candasnos|Canfranc|Capdesaso|Capella|Casbas de Huesca|"
        "Castejón de Monegros|Castejón del Puente|Castejón de Sos|Castelflorite|Castiello de Jaca|Castigaleu|"
        "Castillazuelo|Castillonroy|Chalamera|Chía|Chimillas|Colungo|Esplús|Estada|Estadilla|"
        "Estopiñán del Castillo|Fago|Fanlo|Fiscal|Fonz|Foradada del Toscar|Fraga|La Fueva|Gistaín|El Grado|Grañén|"
        "Graus|Gurrea de Gállego|Hoz de Jaca|Hoz y Costean|Huerto|Huesca|Ibieca|Igriés|Ilche|Isábena|Jaca|Jasa|"
        "Labuerda|Laluenga|Lalueza|Lanaja|Laperdiguera|Lascellas-Ponzano|Lascuarre|Laspaúles|Laspuña|Loarre|"
        "Loporzano|Loscorrales|Lupiñén-Ortilla|Monesma y Cajigar|Monflorite-Lascasas|Montanuy|Monzón|Naval|"
        "Novales|Nueno|Olvena|Ontiñena|Osso de Cinca|Palo|Panticosa|Peñalba|Las Peñas de Riglos|"
        "Peralta de Alcofea|Peralta de Calasanz|Peraltilla|Perarrúa|Pertusa|Piracés|Plan|Poleñino|Pozán de Vero|"
        "La Puebla de Castro|Puente de Montañana|Puente la Reina de Jaca|Puértolas|El Pueyo de Araguás|"
        "Pueyo de Santa Cruz|Quicena|Robres|Sabiñánigo|Sahún|Salas Altas|Salas Bajas|Salillas|Sallent de Gállego|"
        "San Esteban de Litera|Sangarrén|San Juan de Plan|San Miguel del Cinca|Santa Cilia|Santa Cruz de la Serós|"
        "Santaliestra y San Quílez|Santa María de Dulcis|Sariñena|Secastilla|Seira|Sena|Senés de Alcubierre|Sesa|"
        "Sesué|Siétamo|Sopeira|La Sotonera|Tamarite de Litera|Tardienta|Tella-Sin|Tierz|Tolva|Torla-Ordesa|"
        "Torralba de Aragón|Torre la Ribera|Torrente de Cinca|Torres de Alcanadre|Torres de Barbués|Tramaced|"
        "Valfarta|Valle de Bardají|Valle de Hecho|Valle de Lierp|Velilla de Cinca|Vencillón|Viacamp y Litera|"
        "Vicién|Villanova|Villanúa|Villanueva de Sigena|Yebra de Basa|Yésero|Zaidín"
    ),
    "Teruel": (
        "Ababuj|Abejuela|Aguatón|Aguaviva|Aguilar del Alfambra|Alacón|Alba|Albalate del Arzobispo|Albarracín|"
        "Albentosa|Alcaine|Alcalá de la Selva|Alcañiz|Alcorisa|Alfambra|Aliaga|Allepuz|Alloza|Allueva|Almohaja|"
        "Alobras|Alpeñés|Anadón|Andorra|Arcos de las Salinas|Arens de Lledó|Argente|Ariño|Azaila|Bádenas|Báguena|"
        "Bañón|Barrachina|Bea|Beceite|Bello|Belmonte de San José|Berge|Bezas|Blancas|Blesa|Bordón|Bronchales|"
        "Bueña|Burbáguena|Cabra de Mora|Calaceite|Calamocha|Calanda|Calomarde|Camañas|Camarena de la Sierra|"
        "Camarillas|Caminreal|Cantavieja|Cañada de Benatanduz|La Cañada de Verich|Cañada Vellida|"
        "Cañizar del Olivar|Cascante del Río|Castejón de Tornos|Castel de Cabra|El Castellar|Castellote|Castelnou|"
        "Castelserás|Cedrillas|Celadas|Cella|La Cerollera|La Codoñera|Corbalán|Cortes de Aragón|Cosa|Cretas|"
        "Crivillén|La Cuba|Cubla|Cucalón|El Cuervo|Cuevas de Almudén|Cuevas Labradas|Ejulve|Escorihuela|Escucha|"
        "Estercuel|Ferreruela de Huerva|Fonfría|Formiche Alto|Fórnoles|Fortanete|Foz-Calanda|La Fresneda|"
        "Frías de Albarracín|Fuenferrada|Fuentes Calientes|Fuentes Claras|Fuentes de Rubielos|Fuentespalda|Galve|"
        "Gargallo|Gea de Albarracín|La Ginebrosa|Griegos|Guadalaviar|Gúdar|Híjar|Hinojosa de Jarque|"
        "La Hoz de la Vieja|Huesa del Común|La Iglesuela del Cid|Jabaloyas|Jarque de la Val|Jatiel|Jorcas|Josa|"
        "Lagueruela|Lanzuela|Libros|Lidón|Linares de Mora|Lledó|Loscos|Maicas|Manzanera|Martín del Río|"
        "Mas de las Matas|La Mata de los Olmos|Mazaleón|Mezquita de Jarque|Mirambel|Miravete de la Sierra|Molinos|"
        "Monforte de Moyuela|Monreal del Campo|Monroyo|Montalbán|Monteagudo del Castillo|Monterde de Albarracín|"
        "Mora de Rubielos|Moscardón|Mosqueruela|Muniesa|Noguera de Albarracín|Nogueras|Nogueruelas|Obón|Odón|"
        "Ojos Negros|Olba|Oliete|Los Olmos|Orihuela del Tremedal|Orrios|Palomar de Arroyos|Pancrudo|"
        "Las Parras de Castellote|Peñarroya de Tastavins|Peracense|Peralejos|Perales del Alfambra|Pitarque|Plou|"
        "El Pobo|La Portellada|Pozondón|Pozuel del Campo|La Puebla de Híjar|La Puebla de Valverde|Puertomingalvo|"
        "Ráfales|Rillo|Riodeva|Ródenas|Royuela|Rubiales|Rubielos de la Cérida|Rubielos de Mora|Salcedillo|Saldón|"
        "Samper de Calanda|San Agustín|San Martín del Río|Santa Cruz de Nogueras|Santa Eulalia|Sarrión|"
        "Segura de los Baños|Seno|Singra|Terriente|Teruel|Toril y Masegoso|Tormón|Tornos|Torralba de los Sisones|"
        "Torre de Arcas|Torre de las Arcas|Torre del Compte|Torre los Negros|Torrecilla de Alcañiz|"
        "Torrecilla del Rebollar|Torrelacárcel|Torremocha de Jiloca|Torres de Albarracín|Torrevelilla|Torrijas|"
        "Torrijo del Campo|Tramacastiel|Tramacastilla|Tronchón|Urrea de Gaén|Utrillas|Valacloche|Valbona|"
        "Valdealgorfa|Valdecuenca|Valdelinares|Valdeltormo|Valderrobres|Valjunquera|El Vallecillo|"
        "Veguillas de la Sierra|Villafranca del Campo|Villahermosa del Campo|Villanueva del Rebollar de la Sierra|"
        "Villar del Cobo|Villar del Salz|Villarluengo|Villarquemado|Villarroya de los Pinares|Villastar|Villel|"
        "Vinaceite|Visiedo|Vivel del Río Martín|La Zoma"
    ),
    "Zaragoza": (
        "Abanto|Acered|Agón|Aguarón|Aguilón|Ainzón|Aladrén|Alagón|Alarba|Alberite de San Juan|Albeta|Alborge|"
        "Alcalá de Ebro|Alcalá de Moncayo|Alconchel de Ariza|Aldehuela de Liestos|Alfajarín|Alfamén|Alforque|"
        "Alhama de Aragón|Almochuel|La Almolda|Almonacid de la Cuba|Almonacid de la Sierra|"
        "La Almunia de Doña Godina|Alpartir|Ambel|Anento|Aniñón|Añón de Moncayo|Aranda de Moncayo|Arándiga|Ardisa|"
        "Ariza|Artieda|Asín|Atea|Ateca|Azuara|Badules|Bagüés|Balconchán|Bárboles|Bardallur|Belchite|"
        "Belmonte de Gracián|Berdejo|Berrueco|Biel|Bijuesca|Biota|Bisimbre|Boquiñeni|Bordalba|Borja|Botorrita|"
        "Brea de Aragón|Bubierca|Bujaraloz|Bulbuente|Bureta|El Burgo de Ebro|El Buste|Cabañas de Ebro|"
        "Cabolafuente|Cadrete|Calatayud|Calatorao|Calcena|Calmarza|Campillo de Aragón|Carenas|Cariñena|Caspe|"
        "Castejón de Alarba|Castejón de las Armas|Castejón de Valdejasa|Castiliscar|Cervera de la Cañada|"
        "Cerveruela|Cetina|Chiprana|Chodes|Cimballa|Cinco Olivas|Clarés de Ribota|Codo|Codos|Contamina|Cosuenda|"
        "Cuarte de Huerva|Cubel|Las Cuerlas|Daroca|Ejea de los Caballeros|Embid de Ariza|Encinacorba|Épila|Erla|"
        "Escatrón|Fabara|Farlete|Fayón|Los Fayos|Figueruelas|Fombuena|El Frago|El Frasno|Fréscano|Fuendejalón|"
        "Fuendetodos|Fuentes de Ebro|Fuentes de Jiloca|Gallocanta|Gallur|Gelsa|Godojos|Gotor|Grisel|Grisén|"
        "Herrera de los Navarros|Ibdes|Illueca|Isuerre|Jaraba|Jarque de Moncayo|Jaulín|La Joyosa|Lagata|"
        "Langa del Castillo|Layana|Lécera|Lechón|Leciñena|Letux|Litago|Lituénigo|Lobera de Onsella|Longares|"
        "Longás|Lucena de Jalón|Luceni|Luesia|Luesma|Lumpiaque|Luna|Maella|Magallón|Mainar|Malanquilla|Maleján|"
        "Mallén|Malón|Maluenda|Manchones|Mara|María de Huerva|Marracos|Mediana de Aragón|Mequinenza|"
        "Mesones de Isuela|Mezalocha|Mianos|Miedes de Aragón|Monegrillo|Moneva|Monreal de Ariza|Monterde|Montón|"
        "Morata de Jalón|Morata de Jiloca|Morés|Moros|Moyuela|Mozota|Muel|La Muela|Munébrega|Murero|"
        "Murillo de Gállego|Navardún|Nigüella|Nombrevilla|Nonaspe|Novallas|Novillas|Nuévalos|Nuez de Ebro|Olvés|"
        "Orcajo|Orera|Orés|Oseja|Osera de Ebro|Paniza|Paracuellos de Jiloca|Paracuellos de la Ribera|Pastriz|"
        "Pedrola|Las Pedrosas|Perdiguera|Piedratajada|Pina de Ebro|Pinseque|Los Pintanos|Plasencia de Jalón|"
        "Pleitas|Plenas|Pomer|Pozuel de Ariza|Pozuelo de Aragón|Pradilla de Ebro|La Puebla de Albortón|"
        "La Puebla de Alfindén|Puendeluna|Purujosa|Quinto|Remolinos|Retascón|Ricla|Romanos|Rueda de Jalón|Ruesca|"
        "Sabiñán|Sádaba|Salillas de Jalón|Salvatierra de Esca|Samper del Salz|San Martín de la Virgen de Moncayo|"
        "San Mateo de Gállego|Santa Cruz de Grío|Santa Cruz de Moncayo|Santa Eulalia de Gállego|Santed|Sástago|"
        "Sediles|Sestrica|Sierra de Luna|Sigüés|Sisamón|Sobradiel|Sos del Rey Católico|Tabuenca|Talamantes|"
        "Tarazona|Tauste|Terrer|Tierga|Tobed|Torralba de los Frailes|Torralba de Ribota|Torralbilla|Torrehermosa|"
        "Torrelapaja|Torrellas|Torres de Berrellén|Torrijo de la Cañada|Tosos|Trasmoz|Trasobares|Uncastillo|"
        "Undués de Lerda|Urrea de Jalón|Urriés|Used|Utebo|Val de San Martín|Valdehorna|Valmadrid|Valpalmas|"
        "Valtorres|Velilla de Ebro|Velilla de Jiloca|Vera de Moncayo|Vierlas|Villadoz|Villafeliche|"
        "Villafranca de Ebro|Villalba de Perejil|Villalengua|Villamayor de Gállego|Villanueva de Gállego|"
        "Villanueva de Huerva|Villanueva de Jiloca|Villar de los Navarros|Villarreal de Huerva|"
        "Villarroya de la Sierra|Villarroya del Campo|La Vilueña|Vistabella|La Zaida|Zaragoza|Zuera"
    ),}
# Núcleos y nombres cortos que la FAA usa como lugar.
_OTROS = {"ainsa": ("Aínsa-Sobrarbe", "Huesca"), "torla": ("Torla-Ordesa", "Huesca"),
          "formigal": ("Sallent de Gállego", "Huesca"), "cerler": ("Benasque", "Huesca"),
          "candanchu": ("Aisa", "Huesca")}
_TABLA = {nz.clave(m): (m, p) for p, nombres in _MUNICIPIOS.items() for m in nombres.split("|")} | _OTROS
_PATRON = re.compile(r"\b(" + "|".join(sorted((re.escape(k) for k in _TABLA), key=len, reverse=True)) + r")\b")


def municipio(lugar: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """«La almunia de doña godina» → («La Almunia de Doña Godina», «Zaragoza»); «Palacio de los deportes
    (zaragoza)» → («Zaragoza», «Zaragoza»). (None, None) si no es un municipio aragonés."""
    if not lugar:
        return None, None
    t = nz.clave(lugar)
    if t in _TABLA:
        return _TABLA[t]
    for dentro in re.findall(r"\(([^)]+)\)", lugar):
        if nz.clave(dentro) in _TABLA:
            return _TABLA[nz.clave(dentro)]
    hallados = _PATRON.findall(t)
    return _TABLA[max(hallados, key=len)] if hallados else (None, None)


def urls(hoy: date) -> list[str]:
    return [URL, f"{URL}?yyy={hoy.year + 1}"]


def leer(paginas: list[bytes | str]) -> tuple[list[Carrera], list[str]]:
    carreras: list[Carrera] = []
    descartes: list[str] = []
    vistas: set[str] = set()
    for pagina in paginas:
        sopa = BeautifulSoup(pagina, "html.parser")
        for li in sopa.select("ul.list li"):
            enlace = li.find("a", href=True)
            fecha_el, nombre_el = li.select_one(".fecha"), li.select_one(".named")
            tipo_el, lugar_el = li.select_one(".pruebad"), li.select_one(".lugard")
            if not (enlace and fecha_el and nombre_el):
                continue
            url = enlace["href"]
            if url in vistas:
                continue
            vistas.add(url)
            nombre = nz.nombre(_ETIQUETAS.sub("", nombre_el.get_text(" ", strip=True)))
            tipo = tipo_el.get_text(" ", strip=True) if tipo_el else ""
            modalidad_tipo = _TIPOS.get(re.sub(r"[^a-z ]", " ", nz.clave(tipo)).replace("  ", " ").strip())
            if not modalidad_tipo:
                descartes.append(f"no es carrera popular a pie: {nombre} ({tipo})")
                continue
            a_pie, modalidad = nz.clasificar(nombre)
            if not a_pie:
                descartes.append(f"no es a pie: {nombre} ({tipo})")
                continue
            try:
                fecha = datetime.strptime(fecha_el.get_text(strip=True), "%d/%m/%Y").date()
            except ValueError:
                descartes.append(f"fecha ilegible: {nombre}")
                continue
            lugar = lugar_el.get_text(" ", strip=True) if lugar_el else ""
            poblacion, provincia = municipio(lugar)
            if not provincia:
                descartes.append(f"lugar fuera de Aragón o desconocido: {nombre} ({lugar})")
                continue
            if modalidad_tipo == "cross" or modalidad is None or (modalidad_tipo == "trail" and modalidad != "montaña"):
                modalidad = modalidad_tipo  # «Cross de la Montaña» es un cross
            elif modalidad_tipo == "asfalto" and modalidad == "pista":
                modalidad = "asfalto"  # «Milla Urbana» va por la calle
            if poblacion == provincia:  # la FAA a veces pone la capital: «5K 10K Ciudad de Cariñena» → Zaragoza
                otro, otra_provincia = municipio(nombre)
                if otro and otra_provincia == provincia:
                    poblacion = otro
            # «Medio Maratón» es una media (normalizar solo conoce «Media Maratón»).
            distancias = nz.distancias_del_nombre(re.sub(r"(?i)medio marat", "Media Marat", nombre))
            c = Carrera(nombre=nombre, fecha=fecha, fuente=Fuente(ID, url), poblacion=poblacion, provincia=provincia,
                        modalidad=modalidad, distancias_km=distancias)
            c.marcar("Hora y cierre de inscripción en el reglamento de la FAA", "pendiente_cartel")
            carreras.append(c)
    return carreras, descartes
