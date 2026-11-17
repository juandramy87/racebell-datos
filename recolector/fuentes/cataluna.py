"""Ayudas comunes de las fuentes de Cataluña: los 947 municipios catalanes con su provincia (INE,
relación de municipios a 1/1/2026), los meses en catalán y las palabras catalanas de las modalidades,
para que `nz.clasificar` y `nz.distancias_del_nombre` entiendan «cursa», «caminada», «mitja marató»…

Muchas fuentes catalanas no dan la provincia (o ni siquiera el pueblo): con esta tabla se saca del
nombre del pueblo o del nombre de la carrera («Cursa de Parets del Vallès» → Parets del Vallès, Barcelona)."""
from __future__ import annotations

import html
import re
from datetime import date
from functools import lru_cache
from typing import Optional

from nucleo import normalizar as nz

# Nombre oficial (con el artículo delante) separado por «|», por provincia.
_MUNICIPIOS = {
    "Barcelona": (
        "Abrera|Aguilar de Segarra|Aiguafreda|Alella|Alpens|Arenys de Mar|Arenys de Munt|Argentona|Argençola|Artés|"
        "Avinyonet del Penedès|Avinyó|Avià|Badalona|Badia del Vallès|Bagà|Balenyà|Balsareny|Barberà del Vallès|"
        "Barcelona|Begues|Bellprat|Berga|Bigues i Riells del Fai|Borredà|Cabrera d'Anoia|Cabrera de Mar|Cabrils|"
        "Calaf|Calders|Caldes d'Estrac|Caldes de Montbui|Calella|Calldetenes|Callús|Calonge de Segarra|Campins|"
        "Canet de Mar|Canovelles|Canyelles|Capellades|Capolat|Cardedeu|Cardona|Carme|Casserres|Castell de l'Areny|"
        "Castellar de n'Hug|Castellar del Riu|Castellar del Vallès|Castellbell i el Vilar|Castellbisbal|Castellcir|"
        "Castelldefels|Castellet i la Gornal|Castellfollit de Riubregós|Castellfollit del Boix|Castellgalí|"
        "Castellnou de Bages|Castellolí|Castellterçol|Castellví de Rosanes|Castellví de la Marca|Centelles|Cercs|"
        "Cerdanyola del Vallès|Cervelló|Collbató|Collsuspina|Copons|Corbera de Llobregat|Cornellà de Llobregat|"
        "Cubelles|Cànoves i Samalús|Dosrius|El Bruc|El Brull|El Masnou|El Papiol|El Pla del Penedès|"
        "El Pont de Vilomara i Rocafort|El Prat de Llobregat|Els Hostalets de Pierola|Els Prats de Rei|Esparreguera|"
        "Esplugues de Llobregat|Figaró-Montmany|Fogars de Montclús|Fogars de la Selva|Folgueroles|Fonollosa|"
        "Font-rubí|Fígols|Gaià|Gallifa|Gavà|Gelida|Gironella|Gisclareny|Granera|Granollers|Gualba|"
        "Guardiola de Berguedà|Gurb|Igualada|Jorba|L'Ametlla del Vallès|L'Espunyola|L'Esquirol|L'Estany|"
        "L'Hospitalet de Llobregat|La Garriga|La Granada|La Llacuna|La Llagosta|La Nou de Berguedà|"
        "La Palma de Cervelló|La Pobla de Claramunt|La Pobla de Lillet|La Quar|La Roca del Vallès|"
        "La Torre de Claramunt|Les Cabanyes|Les Franqueses del Vallès|Les Masies de Roda|Les Masies de Voltregà|"
        "Llinars del Vallès|Lliçà d'Amunt|Lliçà de Vall|Lluçà|Malgrat de Mar|Malla|Manlleu|Manresa|Marganell|"
        "Martorell|Martorelles|Masquefa|Matadepera|Mataró|Mediona|Moià|Molins de Rei|Mollet del Vallès|"
        "Monistrol de Calders|Monistrol de Montserrat|Montcada i Reixac|Montclar|Montesquiu|Montgat|Montmajor|"
        "Montmaneu|Montmeló|Montornès del Vallès|Montseny|Muntanyola|Mura|Navarcles|Navàs|Olesa de Bonesvalls|"
        "Olesa de Montserrat|Olivella|Olost|Olvan|Olèrdola|Oristà|Orpí|Orís|Pacs del Penedès|Palafolls|"
        "Palau-solità i Plegamans|Pallejà|Parets del Vallès|Perafita|Piera|Pineda de Mar|Polinyà|Pontons|"
        "Prats de Lluçanès|Premià de Dalt|Premià de Mar|Puig-reig|Puigdàlber|Pujalt|Rajadell|Rellinars|Ripollet|"
        "Roda de Ter|Rubió|Rubí|Rupit i Pruit|Sabadell|Sagàs|Saldes|Sallent|Sant Adrià de Besòs|"
        "Sant Agustí de Lluçanès|Sant Andreu de Llavaneres|Sant Andreu de la Barca|Sant Antoni de Vilamajor|"
        "Sant Bartomeu del Grau|Sant Boi de Llobregat|Sant Boi de Lluçanès|Sant Cebrià de Vallalta|Sant Celoni|"
        "Sant Climent de Llobregat|Sant Cugat Sesgarrigues|Sant Cugat del Vallès|Sant Esteve Sesrovires|"
        "Sant Esteve de Palautordera|Sant Feliu Sasserra|Sant Feliu de Codines|Sant Feliu de Llobregat|"
        "Sant Fost de Campsentelles|Sant Fruitós de Bages|Sant Hipòlit de Voltregà|Sant Iscle de Vallalta|"
        "Sant Jaume de Frontanyà|Sant Joan Despí|Sant Joan de Vilatorrada|Sant Julià de Cerdanyola|"
        "Sant Julià de Vilatorta|Sant Just Desvern|Sant Llorenç Savall|Sant Llorenç d'Hortons|Sant Martí Sarroca|"
        "Sant Martí Sesgueioles|Sant Martí d'Albars|Sant Martí de Centelles|Sant Martí de Tous|Sant Mateu de Bages|"
        "Sant Pere Sallavinera|Sant Pere de Ribes|Sant Pere de Riudebitlles|Sant Pere de Torelló|"
        "Sant Pere de Vilamajor|Sant Pol de Mar|Sant Quintí de Mediona|Sant Quirze Safaja|Sant Quirze de Besora|"
        "Sant Quirze del Vallès|Sant Sadurní d'Anoia|Sant Sadurní d'Osormort|Sant Salvador de Guardiola|"
        "Sant Vicenç de Castellet|Sant Vicenç de Montalt|Sant Vicenç de Torelló|Sant Vicenç dels Horts|"
        "Santa Cecília de Voltregà|Santa Coloma de Cervelló|Santa Coloma de Gramenet|Santa Eugènia de Berga|"
        "Santa Eulàlia de Riuprimer|Santa Eulàlia de Ronçana|Santa Fe del Penedès|Santa Margarida de Montbui|"
        "Santa Margarida i els Monjos|Santa Maria d'Oló|Santa Maria de Besora|Santa Maria de Martorelles|"
        "Santa Maria de Merlès|Santa Maria de Miralles|Santa Maria de Palautordera|Santa Perpètua de Mogoda|"
        "Santa Susanna|Santpedor|Sentmenat|Seva|Sitges|Sobremunt|Sora|Subirats|Súria|Tagamanent|Talamanca|Taradell|"
        "Tavertet|Tavèrnoles|Teià|Terrassa|Tiana|Tona|Tordera|Torelló|Torrelavit|Torrelles de Foix|"
        "Torrelles de Llobregat|Ullastrell|Vacarisses|Vallbona d'Anoia|Vallcebre|Vallgorguina|Vallirana|Vallromanes|"
        "Veciana|Vic|Vilada|Viladecans|Viladecavalls|Vilafranca del Penedès|Vilalba Sasserra|Vilanova de Sau|"
        "Vilanova del Camí|Vilanova del Vallès|Vilanova i la Geltrú|Vilassar de Dalt|Vilassar de Mar|"
        "Vilobí del Penedès|Viver i Serrateix|Òdena|Òrrius"
    ),
    "Girona": (
        "Agullana|Aiguaviva|Albanyà|Albons|Alp|Amer|Anglès|Arbúcies|Argelaguer|Avinyonet de Puigventós|Banyoles|"
        "Begur|Bellcaire d'Empordà|Besalú|Bescanó|Beuda|Biure|Blanes|Boadella i les Escaules|Bolvir|Bordils|Borrassà|"
        "Breda|Brunyola i Sant Martí Sapresa|Bàscara|Cabanelles|Cabanes|Cadaqués|Caldes de Malavella|"
        "Calonge i Sant Antoni|Campdevànol|Campelles|Campllong|Camprodon|Camós|Canet d'Adri|Cantallops|Capmany|"
        "Cassà de la Selva|Castell d'Aro, Platja d'Aro i s'Agaró|Castellfollit de la Roca|Castelló d'Empúries|Celrà|"
        "Cervià de Ter|Cistella|Colera|Colomers|Cornellà del Terri|Corçà|Crespià|"
        "Cruïlles, Monells i Sant Sadurní de l'Heura|Darnius|Das|El Far d'Empordà|El Port de la Selva|Espinelves|"
        "Espolla|Esponellà|Figueres|Flaçà|Foixà|Fontanals de Cerdanya|Fontanilles|Fontcoberta|Forallac|"
        "Fornells de la Selva|Fortià|Garrigoles|Garriguella|Garrigàs|Ger|Girona|Gombrèn|Gualta|Guils de Cerdanya|"
        "Hostalric|Isòvol|Jafre|Juià|L'Armentera|L'Escala|La Bisbal d'Empordà|La Cellera de Ter|La Jonquera|La Pera|"
        "La Selva de Mar|La Tallada d'Empordà|La Vajol|La Vall d'en Bas|La Vall de Bianya|Les Llosses|"
        "Les Planes d'Hostoles|Les Preses|Lladó|Llagostera|Llambilles|Llanars|Llançà|Llers|Lloret de Mar|Llívia|"
        "Madremanya|Maià de Montcal|Masarac i Vilarnadal|Massanes|Maçanet de Cabrenys|Maçanet de la Selva|Meranges|"
        "Mieres|Mollet de Peralada|Molló|Mont-ras|Montagut i Oix|Navata|Ogassa|Olot|Ordis|Osor|Palafrugell|Palamós|"
        "Palau de Santa Eulàlia|Palau-sator|Palau-saverdera|Palol de Revardit|Pals|Pardines|Parlavà|Pau|"
        "Pedret i Marzà|Peralada|Planoles|Pont de Molins|Pontós|Porqueres|Portbou|Puigcerdà|Quart|Queralbs|Rabós|"
        "Regencós|Ribes de Freser|Riells i Viabrea|Ripoll|Riudarenes|Riudaura|Riudellots de la Selva|Riumors|Roses|"
        "Rupià|Sales de Llierca|Salt|Sant Andreu Salou|Sant Aniol de Finestres|Sant Climent Sescebes|"
        "Sant Feliu de Buixalleu|Sant Feliu de Guíxols|Sant Feliu de Pallerols|Sant Ferriol|Sant Gregori|"
        "Sant Hilari Sacalm|Sant Jaume de Llierca|Sant Joan de Mollet|Sant Joan de les Abadesses|Sant Joan les Fonts|"
        "Sant Jordi Desvalls|Sant Julià de Ramis|Sant Julià del Llor i Bonmatí|Sant Llorenç de la Muga|"
        "Sant Martí Vell|Sant Martí de Llémena|Sant Miquel de Campmajor|Sant Miquel de Fluvià|Sant Mori|"
        "Sant Pau de Segúries|Sant Pere Pescador|Santa Coloma de Farners|Santa Cristina d'Aro|"
        "Santa Llogaia d'Àlguema|Santa Pau|Sarrià de Ter|Saus, Camallera i Llampaies|Serinyà|Serra de Daró|Setcases|"
        "Sils|Siurana|Susqueda|Terrades|Torrent|Torroella de Fluvià|Torroella de Montgrí|Tortellà|Toses|Tossa de Mar|"
        "Ullastret|Ullà|Ultramort|Urús|Vall-llobrega|Vallfogona de Ripollès|Ventalló|Verges|Vidreres|Vidrà|"
        "Vila-sacra|Vilabertran|Vilablareix|Viladamat|Viladasens|Vilademuls|Viladrau|Vilafant|Vilajuïga|"
        "Vilallonga de Ter|Vilamacolum|Vilamalla|Vilamaniscle|Vilanant|Vilaür|Vilobí d'Onyar|Vilopriu"
    ),
    "Lleida": (
        "Abella de la Conca|Agramunt|Aitona|Albatàrrec|Albesa|Alcanó|Alcarràs|Alcoletge|Alfarràs|Alfés|Algerri|"
        "Alguaire|Alins|Almacelles|Almatret|Almenar|Alpicat|Alt Àneu|Alàs i Cerc|Alòs de Balaguer|Anglesola|Arbeca|"
        "Arres|Arsèguel|Artesa de Lleida|Artesa de Segre|Aspa|Baix Pallars|Balaguer|Barbens|Bassella|Bausen|Belianes|"
        "Bell-lloc d'Urgell|Bellaguarda|Bellcaire d'Urgell|Bellmunt d'Urgell|Bellpuig|Bellver de Cerdanya|Bellvís|"
        "Benavent de Segrià|Biosca|Bossòst|Bovera|Bòrdes, Es|Cabanabona|Cabó|Camarasa|Canejan|Castell de Mur|"
        "Castellar de la Ribera|Castelldans|Castellnou de Seana|Castellserà|Castelló de Farfanya|Cava|Cervera|"
        "Cervià de les Garrigues|Ciutadilla|Clariana de Cardener|Coll de Nargó|Conca de Dalt|Corbins|Cubells|"
        "El Cogul|El Palau d'Anglesola|El Poal|El Pont de Bar|El Pont de Suert|El Soleràs|El Vilosell|Els Alamús|"
        "Els Omellons|Els Omells de na Gaia|Els Plans de Sió|Els Torms|Espot|Estamariu|Estaràs|Esterri d'Àneu|"
        "Esterri de Cardós|Farrera|Fondarella|Foradada|Fulleda|Fígols i Alinyà|Gavet de la Conca|"
        "Gimenells i el Pla de la Font|Golmés|Granyanella|Granyena de Segarra|Granyena de les Garrigues|Guimerà|"
        "Guissona|Guixers|Gósol|Isona i Conca Dellà|Ivars d'Urgell|Ivars de Noguera|Ivorra|Josa i Tuixén|Juncosa|"
        "Juneda|L'Albagés|L'Albi|L'Espluga Calba|La Baronia de Rialb|La Coma i la Pedra|La Floresta|La Fuliola|"
        "La Granadella|La Granja d'Escarp|La Guingueta d'Àneu|La Molsosa|La Pobla de Cérvoles|La Pobla de Segur|"
        "La Portella|La Sentiu de Sió|La Seu d'Urgell|La Torre de Cabdella|La Vall de Boí|La Vansa i Fórnols|Les|"
        "Les Avellanes i Santa Linya|Les Borges Blanques|Les Oluges|Les Valls d'Aguilar|Les Valls de Valira|Linyola|"
        "Lladorre|Lladurs|Llardecans|Llavorsí|Lleida|Lles de Cerdanya|Llimiana|Llobera|Maials|Maldà|Massalcoreig|"
        "Massoteres|Menàrguens|Miralcamp|Mollerussa|Montellà i Martinet|Montferrer i Castellbò|Montgai|"
        "Montoliu de Lleida|Montoliu de Segarra|Montornès de Segarra|Nalec|Naut Aran|Navès|Odèn|Oliana|Oliola|Olius|"
        "Organyà|Os de Balaguer|Ossó de Sió|Penelles|Peramola|Pinell de Solsonès|Pinós|Ponts|Prats i Sansor|Preixana|"
        "Preixens|Prullans|Puiggròs|Puigverd d'Agramunt|Puigverd de Lleida|Rialp|Ribera d'Ondara|Ribera d'Urgellet|"
        "Riner|Riu de Cerdanya|Rosselló|Salàs de Pallars|Sanaüja|Sant Esteve de la Sarga|Sant Guim de Freixenet|"
        "Sant Guim de la Plana|Sant Llorenç de Morunys|Sant Martí de Riucorb|Sant Ramon|Sarroca de Bellera|"
        "Sarroca de Lleida|Senterada|Seròs|Sidamon|Solsona|Soriguera|Sort|Soses|Sudanell|Sunyer|Talarn|Talavera|"
        "Tarroja de Segarra|Tarrés|Tiurana|Tornabous|Torre-serona|Torrebesses|Torrefarrera|Torrefeta i Florejacs|"
        "Torregrossa|Torrelameu|Torres de Segre|Torà|Tremp|Tàrrega|Térmens|Tírvia|Vall de Cardós|"
        "Vallbona de les Monges|Vallfogona de Balaguer|Verdú|Vielha e Mijaran|Vila-sana|Vilagrassa|Vilaller|Vilamòs|"
        "Vilanova de Bellpuig|Vilanova de Meià|Vilanova de Segrià|Vilanova de l'Aguda|Vilanova de la Barca|Vinaixa|"
        "Àger"
    ),
    "Tarragona": (
        "Aiguamúrcia|Albinyana|Alcanar|Alcover|Aldover|Alfara de Carles|Alforja|Alió|Almoster|Altafulla|Amposta|"
        "Arbolí|Arnes|Ascó|Banyeres del Penedès|Barberà de la Conca|Batea|Bellmunt del Priorat|Bellvei|Benifallet|"
        "Benissanet|Blancafort|Bonastre|Bot|Botarell|Bràfim|Cabacés|Cabra del Camp|Calafell|Camarles|Cambrils|"
        "Capafonts|Capçanes|Caseres|Castellvell del Camp|Colldejou|Conesa|Constantí|Corbera d'Ebre|"
        "Cornudella de Montsant|Creixell|Cunit|Deltebre|Duesaigües|El Catllar|El Lloar|El Masroig|El Milà|El Molar|"
        "El Montmell|El Morell|El Perelló|El Pinell de Brai|El Pla de Santa Maria|El Pont d'Armentera|El Rourell|"
        "El Vendrell|Els Garidells|Els Guiamets|Els Pallaresos|Falset|Figuerola del Camp|Flix|Forès|Freginals|"
        "Gandesa|Garcia|Ginestar|Godall|Gratallops|Horta de Sant Joan|L'Albiol|L'Aldea|L'Aleixar|L'Ametlla de Mar|"
        "L'Ampolla|L'Arboç|L'Argentera|L'Espluga de Francolí|La Bisbal de Montsant|La Bisbal del Penedès|La Canonja|"
        "La Fatarella|La Febró|La Figuera|La Galera|La Masó|La Morera de Montsant|La Nou de Gaià|La Palma d'Ebre|"
        "La Pobla de Mafumet|La Pobla de Massaluca|La Pobla de Montornès|La Riba|La Riera de Gaià|La Ràpita|"
        "La Secuita|La Selva del Camp|La Sénia|La Torre de Fontaubella|La Torre de l'Espanyol|La Vilella Alta|"
        "La Vilella Baixa|Les Borges del Camp|Les Piles|Llorac|Llorenç del Penedès|Margalef|Marçà|Mas de Barberans|"
        "Masdenverge|Masllorenç|Maspujols|Miravet|Mont-ral|Mont-roig del Camp|Montblanc|Montbrió del Camp|Montferri|"
        "Móra d'Ebre|Móra la Nova|Nulles|Passanant i Belltall|Paüls|Perafort|Pira|Poboleda|Pontils|Porrera|"
        "Pradell de la Teixeta|Prades|Prat de Comte|Pratdip|Puigpelat|Querol|Rasquera|Renau|Reus|Riba-roja d'Ebre|"
        "Riudecanyes|Riudecols|Riudoms|Rocafort de Queralt|Roda de Berà|Rodonyà|Roquetes|Salomó|Salou|"
        "Sant Jaume d'Enveja|Sant Jaume dels Domenys|Santa Bàrbara|Santa Coloma de Queralt|Santa Oliva|Sarral|"
        "Savallà del Comtat|Senan|Solivella|Tarragona|Tivenys|Tivissa|Torredembarra|Torroja del Priorat|Tortosa|"
        "Ulldecona|Ulldemolins|Vallclara|Vallfogona de Riucorb|Vallmoll|Valls|Vandellòs i l'Hospitalet de l'Infant|"
        "Vespella de Gaià|Vila-rodona|Vila-seca|Vilabella|Vilalba dels Arcs|Vilallonga del Camp|"
        "Vilanova d'Escornalbou|Vilanova de Prades|Vilaplana|Vilaverd|Vimbodí i Poblet|Vinebre|Vinyols i els Arcs|"
        "Xerta"
    ),
}
# Formas cortas habituales en los nombres de las carreras → municipio.
_ALIAS = {
    "sant cugat": "Sant Cugat del Vallès", "sant boi": "Sant Boi de Llobregat", "cerdanyola": "Cerdanyola del Vallès",
    "hospitalet": "L'Hospitalet de Llobregat", "l hospitalet": "L'Hospitalet de Llobregat",
    "llavaneres": "Sant Andreu de Llavaneres", "vilafranca": "Vilafranca del Penedès", "mollet": "Mollet del Vallès",
    "parets": "Parets del Vallès", "sant sadurni": "Sant Sadurní d'Anoia", "esplugues": "Esplugues de Llobregat",
    "montcada": "Montcada i Reixac", "torroella": "Torroella de Montgrí", "platja d aro": "Castell d'Aro, Platja d'Aro i s'Agaró",
    "vilanova i la geltru": "Vilanova i la Geltrú", "ciutat de vilanova": "Vilanova i la Geltrú",
    "santa perpetua": "Santa Perpètua de Mogoda", "sant feliu de guixols": "Sant Feliu de Guíxols",
    "seu d urgell": "La Seu d'Urgell", "seu vella": "Lleida", "bigues": "Bigues i Riells del Fai", "bigues i riells": "Bigues i Riells del Fai",
    "les franqueses": "Les Franqueses del Vallès", "franqueses": "Les Franqueses del Vallès",
    "lerida": "Lleida", "gerona": "Girona", "sant andreu de la barca": "Sant Andreu de la Barca",
}
# Municipios cuyo nombre es también una palabra corriente: no se buscan dentro del nombre de una carrera
# («Cursa de les Fonts» no es en Les, «Cursa per la Pau» no es en Pau).
_NO_EN_NOMBRE = {"les", "pau", "sort", "bot", "das", "ger", "cava", "mura", "malla", "quart", "pira", "seva",
                 "carme", "ponts", "alins", "alio", "aspa", "arres", "biure", "ordis", "senan", "sora", "riner",
                 "valls", "vila", "jorba", "olius", "nalec", "gaia", "salt", "amer", "flix", "toses", "renau"}

MESES = {"gen": 1, "ene": 1, "feb": 2, "mar": 3, "abr": 4, "mai": 5, "may": 5, "jun": 6, "jul": 7,
         "ago": 8, "set": 9, "sep": 9, "oct": 10, "nov": 11, "des": 12, "dic": 12}

# Catalán → castellano, sobre el texto ya pasado por `nz.clave` (minúsculas y sin tildes).
_PALABRAS = [
    (r"\bmitja marato\b", "media maraton"), (r"\bmitja\b", "media"), (r"\bmarato\b", "maraton"),
    (r"\bcurs(a|es) (de|per) muntanya\b", "carrera por montana"), (r"\bmuntanya\b", "montana"),
    (r"\bcurs(a|es)\b", "carrera"), (r"\bcros\b", "cross"), (r"\bcaminad(a|es)\b", "marcha"),
    (r"\bmarx(a|es)\b", "marcha"), (r"\bpassejad(a|es)\b", "paseo"), (r"\bduatlo\b", "duatlon"),
    (r"\btriatlo\b", "triatlon"), (r"\baquatlo\b", "acuatlon"), (r"\bnatacio\b", "natacion"),
    (r"\bbicicleta\b", "bici"), (r"\bciclisme\b", "ciclismo"), (r"\bvertical\b", "kv"),
    (r"\bcani ?(trail|cross|marcha)\b", "canicross"), (r"\bcrono ?escalada\b", "kv"),
    (r"\bcarrera i marcha\b", "carrera y marcha"), (r"\bmarcha i carrera\b", "marcha y carrera"),
]
_INFANTIL = re.compile(r"\b(infantil|infantils|kids|mini|minis|escolar|escolars|junior|juvenil|cadet|benjami|alevi)\b")


def a_castellano(texto: Optional[str]) -> str:
    t = nz.clave(html.unescape(texto or ""))
    for patron, cambio in _PALABRAS:
        t = re.sub(patron, cambio, t)
    return t


def clasificar(*textos: Optional[str]) -> tuple[bool, Optional[str]]:
    """`nz.clasificar` entendiendo el catalán («Cursa i caminada» sí es a pie; «Caminada» sola, no)."""
    return nz.clasificar(*(a_castellano(t) for t in textos if t))


def distancias(nombre: str) -> list[float]:
    """«37a Mitja Marató i 10 Km» → [10, 21.097]; «Cursa de Parets (5 i 10 Km)» → [5, 10]."""
    t = a_castellano(nombre)
    juntas = [float(x) for a, b in re.findall(r"\b(\d{1,2}) (?:i|y) (\d{1,3}) ?km?\b", t) for x in (a, b)]
    return sorted(set(nz.distancias_del_nombre(t)) | set(juntas))


def es_infantil(nombre: str) -> bool:
    """Pruebas solo para niños o escolares («(Curses Infantils)», «… KIDS», «La Mini»): se descartan."""
    t = nz.clave(html.unescape(nombre))
    if re.search(r"\((curses? )?infantils?\)", nombre.lower()):
        return True
    return bool(_INFANTIL.search(t)) and not distancias(nombre) and not re.search(r"\b(popular|open|absolut)", t)


def texto(valor: Optional[str]) -> str:
    """Quita entidades HTML («&#039;», «&#8211;») y espacios de sobra."""
    return re.sub(r"\s+", " ", html.unescape(valor or "")).strip()


def fecha(valor: str) -> Optional[date]:
    """«21 novembre 2026», «22-Novembre-2026», «03/12/2026» → date."""
    t = nz.clave(valor)
    m = re.search(r"\b(\d{1,2}) (\d{1,2}) (\d{4})\b", t)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = re.search(r"\b(\d{1,2}) (?:de |d )?([a-z]{3})[a-z]* (?:de )?(\d{4})\b", t)
    if m and m.group(2) in MESES:
        return date(int(m.group(3)), MESES[m.group(2)], int(m.group(1)))
    return None


@lru_cache(maxsize=1)
def _tabla() -> dict[str, tuple[str, str]]:
    tabla = {}
    for provincia, nombres in _MUNICIPIOS.items():
        for n in nombres.split("|"):
            tabla[nz.clave(n)] = (n, provincia)
            sin_articulo = re.sub(r"^(el|la|els|les|l|lo) ", "", nz.clave(n))
            tabla.setdefault(sin_articulo, (n, provincia))
    for alias, n in _ALIAS.items():
        tabla[nz.clave(alias)] = tabla[nz.clave(n)]
    return tabla


def municipio(valor: Optional[str]) -> Optional[tuple[str, str]]:
    """Nombre de un pueblo tal como lo da la fuente → (municipio oficial, provincia), o None si no es catalán.
    Entiende «PINELL DE BRAI, EL», «SANT GREGORI (MUNICIPIO)», «Vidreres (Girona)» o «08619 Castell de l'Areny»."""
    if not valor:
        return None
    t = texto(valor)
    t = re.sub(r"\((municipio|municipi|[^)]*\d[^)]*)\)", " ", t, flags=re.I)
    t = re.sub(r"\b\d{5}\b", " ", t).strip(" ,-")
    t = re.sub(r"\b(st|sta)\.? ", lambda m: "Sant " if m.group(1).lower() == "st" else "Santa ", t, flags=re.I)
    m = re.match(r"^(.*), ?(el|la|els|les|l'|lo)$", t, re.I)
    if m:
        t = f"{m.group(2)} {m.group(1)}"
    tabla = _tabla()
    # «SANT LLORENÇ (MATADEPERA)»: el municipio puede ir entre paréntesis; «GIRONA-ELS ANGELS»: el pueblo va primero.
    pruebas = [t, re.sub(r"\s*\(.*?\)\s*", " ", t), *re.findall(r"\(([^)]*)\)", t), *t.split("-")]
    for prueba in pruebas:
        hallado = tabla.get(nz.clave(prueba))
        if hallado:
            return hallado
    return None


@lru_cache(maxsize=1)
def _patron() -> re.Pattern:
    claves = sorted((k for k in _tabla() if k not in _NO_EN_NOMBRE and len(k) > 3), key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(k) for k in claves) + r")\b")


def municipio_en(nombre: Optional[str]) -> Optional[tuple[str, str]]:
    """Busca un municipio catalán dentro del nombre de la carrera (el más largo que aparezca)."""
    encontrados = _patron().findall(nz.clave(texto(nombre)))
    if not encontrados:
        return None
    return _tabla()[max(encontrados, key=len)]
