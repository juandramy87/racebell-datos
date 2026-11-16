# Racebell · datos de carreras

Recolector de las carreras populares a pie (asfalto, trail, montaña y cross) que usa la app **Racebell**. Lee las
webs públicas de cronometradores, plataformas de inscripción y federaciones, une los duplicados y publica cada día
un único archivo:

**https://racebell-datos.pages.dev/carreras.json**

- `recolector/`: lectores de cada fuente (`fuentes/`), normalización y unión (`nucleo/`), tests con páginas de
  ejemplo (`tests/`) y la lista de fuentes con lo que da cada una (`FUENTES.md`).
- `publicar/`: cabeceras del sitio de Cloudflare Pages.
- `.github/workflows/recolector.yml`: la pasada diaria (05:15 UTC).

Normas: se respeta el robots.txt de cada web, se guarda solo lo necesario para mostrar la carrera (nombre, fecha,
lugar, distancias, precios, plazos de inscripción y enlace oficial) y nunca listas de inscritos ni clasificaciones.
Cada carrera enlaza a su web oficial, que es la que manda.

¿Organizas una carrera y quieres que aparezca, o que corrijamos algo? Escribe a contact@fuentepatos.com.
