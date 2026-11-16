# Fuentes de carreras (investigación del 16/11/2026)

Sacado de buscar dónde se inscribe cada carrera que nos faltaba los findes 21–22/11 y 28–29/11 frente a running.life. «Hecho» = ya tiene lector.

| Fuente | Zona | Listado | Cierre de inscripción | Andaluzas próximas | Estado |
|---|---|---|---|---|---|
| Dorsalchip | Málaga, Cádiz, Granada, Córdoba | API JSON `publicapi.dorsalchip.es/api/ProximosEventos` | Sí, exacto | ~50 | Hecho |
| Tecnocrono (AvaiBook) | Sierra de Cádiz, Sevilla | `avaibooksports.com/listado-tecnocrono.php` | Sí | ~20 | Hecho |
| Sesca | Cádiz | `crono.sesca.es/` | PDF | ~5 | Hecho |
| Global-Tempo | Granada, Almería, Córdoba | portada + fichas `carreras.php?id=N` (hay fichas ocultas: se sondean los id) | PDF | ~15 | Hecho |
| FAA | Toda Andalucía | `atletismofaa.es/carreraspopulares/` | En el cartel | ~25 | Hecho |
| **Gesconchip** | Cádiz, Sevilla, Málaga, Jaén | `gesconchip.es/proximas-pruebas` (HTML; `data-fecha`/`data-hora` de cierre o cambio de tarifa) | Sí | ~33 | Hecho |
| **Corredores Populares** | Sevilla, Córdoba | `corredorespopulares.es/inscripciones.php` (NO usar `/calendario/`: es agregador). robots prohíbe `/*?*` | Sí | ~12 | Hecho |
| **Cronius Sport** (AvaiBook) | Huelva, norte de Sevilla | portada `croniussport.es` (bloques fecha + `imPopUpWin('…/inscripcion/<slug>/')`); fichas AvaiBook con JSON-LD y «Plazo de inscripción Del … al …» | Sí | ~11 | Hecho |
| **Inscrik** | Almería, Granada, Jaén | portada `inscrik.com/`; fichas `/evento/<slug>/` con JSON-LD. robots prohíbe `/api/` | `validFrom` de ofertas | ~11 | Hecho |
| **Deportime** | Jaén (+ Córdoba, Cádiz) | `deportime.es/proximas-carreras/` (Modern Events Calendar); ficha con JSON-LD | Estado (Agotado/Registro) | ~13 | Hecho |
| **Runnink** | Cádiz | `runnink.com/calendario/` (sin www). robots: Crawl-delay 10 | — | ~12 | Hecho |
| **Todofondo** (Diputación Almería) | Almería | `todofondo.net/prueba/proximas/` | Estado | ~6 | Hecho |
| **Alcanza tu Meta** | Levante almeriense | `alcanzatumeta.es/calendario` (`<time datetime>`, `.atmc-where`, cierre) | Sí | ~4 | Hecho |
| **Sportmaniacs** | España (Huelva, Sevilla, Jaén, Cádiz) | `sportmaniacs.com/es/races?page=N` (nombre, fecha, localidad) + JSON-LD de la ficha (provincia). Se recuerda la provincia de cada ficha en `datos/sportmaniacs-provincias.json` para no reabrirla. robots prohíbe `/app`, `/results`, `/rankings` | — | ~10 | Hecho |
| **Ola! Rivers** | Málaga, Cádiz, Córdoba, Almería, Sevilla | `olarivers.com/proximas-pruebas/` (provincia, lugar, tipo y fin de inscripción en `data-date`) | Sí | ~20 | Hecho |
| **Cronofinisher** | Extremadura (+ Cádiz, Jaén, Huelva) | `cronofinisher.com/calendario/` + `/calendario//pg=N/` (GET) | «Hasta: dd-mm-aaaa» | ~6 | Hecho |
| **Time2Run** | Jaén, Granada, Córdoba, Sevilla | `time2run.es/eventos-proximos/` (nombre, fecha, categoría) + JSON-LD de la ficha en RockTheSport si la enlaza. Sin provincia: se deduce del nombre o queda pendiente | De RockTheSport | ~3 | Hecho |
| **TuCarrera.es** | Almería | `tucarrera.es/api/events.php` (el JSON que pinta su directorio) | — | ~3 | Hecho |
| **Ruta 091** | Circuito Policía Nacional | `ruta091.es/carreras` (Córdoba y Écija; las demás son de fuera) | En el reglamento | 2 | Hecho |
| FAA Live (calendario federado) | Toda Andalucía (circuitos provinciales de campo a través: Sevilla, Jaén, Cádiz/Jerez…) | `web.faalive.com/Calendar`: app Blazor que pide los datos a `manager.faalive.com`; sin HTML que leer | — | ~10/finde en temporada de cross | Pendiente (ver nota) |
| **Montur Eventos** | Almería (Albox, Chirivel) | `montureventos.com/proximos-eventos/` (WordPress, `data-title`/`data-city-name`/`data-category`/`data-date` y hora en el pie). Se quitan senderismo y marchas | — | ~6 (CxM con meses de antelación) | Hecho (16/11) |
| **Cruzando la Meta** | Almería, Granada, Jaén, Sevilla | `cruzandolameta.es/pruebas/` (tarjetas por mes; lugar «… (Provincia)»; municipio del lugar o del nombre). Inscribe en Inscrik pero publica antes | «Cierra el …» (día) | ~14 | Hecho (16/11) |
| RockTheSport | España | sitemap `events-es.xml` filtrado por municipios andaluces (`datos/municipios-andalucia.json`, de Wikipedia) + JSON-LD de cada ficha; desde el 16/11 también las fichas sin municipio en el nombre (300 nuevas por pasada, recordadas en `rockthesport-vistos.json`); robots prohíbe `/api/` | `validThrough` | ~2–5 | Hecho |
| RunRun Sports | — | sin listado | — | — | Descartada |

Notas:
- La «Carrera por la No Violencia de Género» de Jaén (22/11) está **cancelada** (CSIF, 10/11: el Patronato suspendió las carreras de noviembre por falta de Policía Local), aunque Deportime la sigue mostrando como «Agotado».
- Fechas que los agregadores dan mal: Santiponce y Cross Pinar del Rey son el 22/11 según la inscripción oficial (no el 29).
- Dónde se inscribe cada carrera que faltaba el finde 28–29/11: Ultra Maratón Costa de Almería → TuCarrera.es;
  Caras Nortes Skyrace → Time2Run (inscripción en RockTheSport); CxM Sierra Albarracín → Ola! Rivers (inscripción en
  Tecnocrono, ya cerrada, por eso no sale en el listado de AvaiBook); Campo a Través Sierra Ahillos (Alcaudete) →
  Sportmaniacs; Circuito Diputación de Sevilla de Campo a Través (Mairena del Alcor) → FAA Live
  (`web.faalive.com/ch/2026/14549/`); Cross Popular Ciudad de Jerez → circuito provincial de Jerez (FAA, sin página
  propia encontrada); Duatlón Contrarreloj por Equipos El Ejido → Federación Andaluza de Triatlón / RockTheSport.
- FAA Live: el calendario de competiciones federadas de la FAA (incluye los circuitos provinciales de cross) solo se
  ve con su app web; leerlo exigiría usar la API interna de `manager.faalive.com`, que no está documentada. Pendiente
  de decidir si se pide permiso a la FAA o se busca otra vía.
- Las carreras híbridas (Hyrox, «Hybrid Race», categoría «fitness») se descartan en `nucleo/normalizar.py`.


## Carreras anunciadas (`anunciadas.json`, desde el 16/11/2026)
Las plataformas solo publican una carrera al abrir la inscripción (1–3 meses antes). Para ver las grandes con más
tiempo (medias, maratones, ultras), Claude apunta a mano la fecha de la próxima edición sacada de su web **oficial**
(`fuentes/anunciadas.py`). Cuando una plataforma la publica, se une y manda la plataforma. Las que solo tienen fecha en
agregadores van con `fecha_provisional` y sin web oficial no se publican. Revisarlas cada mes: `sin_fecha` dice cuáles
faltan por anunciar. El calendario de la RFEA (`atletismorfea.es/calendario`) se probó y solo trae las de nivel nacional.
