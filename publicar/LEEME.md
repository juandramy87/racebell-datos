# Publicar los datos de Racebell (Cloudflare Pages)

La app descarga `https://racebell-datos.pages.dev/carreras.json`. Hasta que exista, usa la copia que lleva dentro
(`app/assets/datos/carreras.json`) y `URL_CARRERAS` sigue en `null` (`app/src/datos/config.ts`).

## Primera vez (lo hace el usuario, o Claude con su visto bueno)
1. `npx wrangler login`: entrar con la cuenta de Cloudflare de Fuentepatos.
2. `./publicar/publicar.sh`: crea el proyecto `racebell-datos` la primera vez (wrangler lo pregunta) y sube el JSON.
3. Comprobar que abre `https://racebell-datos.pages.dev/carreras.json`.
4. Poner esa URL en `URL_CARRERAS` y compilar la app.

Coste: 0 € (plan gratuito de Pages: 500 subidas al mes; usamos 1 al día).

## Cada día
- **Opción B, en GitHub Actions:** `.github/workflows/recolector.yml` recoge, guarda las tablas y publica. Hace falta:
  1. Este repositorio es público: GitHub Actions no tiene límite de minutos.
  2. En Cloudflare, crear un token con permiso «Cloudflare Pages: Edit» y copiar el ID de la cuenta.
  3. En GitHub → Settings → Secrets → Actions: `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`.
  4. Lanzarlo a mano una vez (Actions → «Recolector diario» → Run workflow) y revisar el resultado.
  Riesgo: las máquinas de GitHub están en EE. UU. y alguna web podría bloquearlas o ir más lenta; se ve en la primera pasada.
