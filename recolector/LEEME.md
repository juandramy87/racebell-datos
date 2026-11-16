# Recolector de Racebell

Lee las carreras populares de las webs oficiales, une las repetidas y escribe `datos/carreras.json` (lo que descargará la app).

## Uso

```bash
cd recolector
.venv/bin/python recolectar.py            # próximos 60 días (usa la copia del día si ya existe)
.venv/bin/python recolectar.py --sin-cache
.venv/bin/python cobertura.py 2026-11-21  # cobertura de ese finde frente a running.life
.venv/bin/python -m pytest -q             # tests con copias guardadas de las webs
```

Primera vez: `/opt/homebrew/bin/python3.11 -m venv .venv && .venv/bin/pip install beautifulsoup4 pytest`.

## Piezas

| Archivo | Qué hace |
|---|---|
| `fuentes/dorsalchip.py` | API JSON pública. Cierre de inscripción exacto. Málaga sobre todo. |
| `fuentes/tecnocrono.py` | Listado de AvaiBook Sports (schema.org). Plazos «desde … hasta …». Sierra de Cádiz y Sevilla. |
| `fuentes/sesca.py` | Listado HTML. Población, fecha y metros. Provincia supuesta: Cádiz. Cierre en el PDF. |
| `fuentes/globaltempo.py` | Portada + ficha de cada prueba (provincia y localidad). Granada y Almería. **Nunca** lee ni guarda los inscritos que publica la ficha. |
| `fuentes/faa.py` | Carreras populares de la FAA: fecha, nombre corto y cartel. Lo demás está en el cartel. |
| `fuentes/sportmaniacs.py` | Listado por páginas + JSON-LD de las fichas en plazo (provincia). Recuerda la provincia de cada ficha en `datos/sportmaniacs-provincias.json`. |
| `fuentes/olarivers.py` | Próximas pruebas de Ola! Rivers: provincia, lugar, tipo y fin de inscripción. |
| `fuentes/cronofinisher.py` | Calendario (2–3 páginas); solo las andaluzas. «Hasta: dd-mm-aaaa». |
| `fuentes/time2run.py` | Eventos de Time2Run + JSON-LD de su ficha en RockTheSport cuando la enlaza. Sin provincia (pendiente). |
| `fuentes/tucarrera.py`, `fuentes/ruta091.py` | Directorio JSON de TuCarrera.es (Almería) y circuito Ruta 091 (Córdoba, Écija). |
| `fuentes/jsonld.py` | Lee fichas con JSON-LD; `recortar` deja solo el JSON-LD antes de guardar en caché. |
| `nucleo/modelo.py` | Formato común (`Carrera`) y estado de la inscripción calculado con la hora actual. |
| `nucleo/normalizar.py` | Nombres, provincias, modalidades y descarte de lo que no es a pie (bici, marchas, natación…). |
| `nucleo/duplicados.py` | Une la misma carrera de varias fuentes (mismo día + pueblo + nombre parecido; nunca dentro de una misma fuente). |
| `nucleo/red.py` | Descargas educadas: User-Agent propio, 3 s entre peticiones a una misma web, caché del día en `datos/cache/`. |
| `cobertura.py` | Compara un finde con running.life. Solo para medir: nada de running.life entra en los datos. |

## Calidad de cada carrera

- `fuente`: todo lo da la web oficial.
- `pendiente_cartel`: falta algo que solo está en el cartel o en la normativa en PDF (lo leerá Claude en tandas).
- `dudoso`: algo no cuadra; revisar antes de publicar.

Cada aviso explica qué falta (`avisos_calidad`). `datos/informe.json` guarda lo leído por fuente, los descartes y las uniones, para revisarlos.

## Estado (16/11/2026)

19 fuentes con lector (ver `FUENTES.md`): 135 carreras andaluzas en los próximos 45 días (151 antes de unir 15 repetidas).

| Finde | Nuestras | running.life | En común | Cobertura |
|---|---|---|---|---|
| 21–22 nov | 35 | 31 | 29 | **95 %** (era 81 %) |
| 28–29 nov | 10 | 12 | 8 | **71 %** (era 43 %); 77 % sin contar la «Fungo Hybrid Race» (las híbridas no cuentan) |

Faltan el 21–22: Geoparque Trail Fonelas (RockTheSport, sin listado legible) y la de Jaén (cancelada).
Faltan el 28–29: Circuito Diputación de Sevilla de Campo a Través (Mairena del Alcor) y Cross Popular Ciudad de Jerez
(calendario federado FAA Live, sin HTML: ver `FUENTES.md`), Duatlón Contrarreloj por Equipos El Ejido (RockTheSport /
Fed. Andaluza de Triatlón) y la Fungo Hybrid Race (descartada a propósito).

Correcciones a mano (carreras canceladas que la fuente aún muestra): `correcciones.json`.
Si una web no envía su certificado intermedio, `nucleo/red.py` descarga con curl (que sí valida el certificado).
