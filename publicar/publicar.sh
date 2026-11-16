#!/bin/zsh
# Sube recolector/datos/carreras.json a Cloudflare Pages (proyecto «racebell-datos»).
# Solo lo ejecuta el usuario, o Claude con su visto bueno. La primera vez: `npx wrangler login`
# (abre el navegador para entrar en la cuenta de Cloudflare de Fuentepatos).
set -eu
cd "$(dirname "$0")/.."
SITIO=$(mktemp -d)
cp recolector/datos/carreras.json publicar/_headers "$SITIO/"
python3 -c "import json,sys; d=json.load(open('$SITIO/carreras.json')); assert len(d['carreras'])>20, 'pocas carreras: no se publica'"
npx --yes wrangler@4 pages deploy "$SITIO" --project-name racebell-datos --branch main --commit-dirty=true
rm -rf "$SITIO"
echo "Publicado: https://racebell-datos.pages.dev/carreras.json"
