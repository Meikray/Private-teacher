#!/usr/bin/env bash
# ==========================================================
#  Lanceur Mac / Linux de l'Assistant Professeur Personnel.
#  Dans un terminal :  ./lancer_mac_linux.sh
#  Il installe ce qu'il faut (la première fois), puis démarre
#  le serveur et ouvre le navigateur. Pour arrêter : Ctrl+C.
# ==========================================================
set -e
cd "$(dirname "$0")"

# --- 1. Trouver Python ---
if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 est introuvable. Installe-le depuis https://www.python.org/downloads/"
  exit 1
fi

# --- 2. Environnement virtuel (seulement la première fois) ---
if [ ! -f .venv/bin/activate ]; then
  echo "Création de l'environnement virtuel..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate

# --- 3. Bibliothèques (rapide si elles sont déjà installées) ---
echo "Vérification des bibliothèques..."
python -m pip install -q -r requirements.txt

# --- 4. Clé API dans .env ---
[ -f .env ] || cp .env.example .env
if grep -q "mets-ta-cle-ici" .env; then
  echo
  echo "Il faut ta clé API Anthropic (créée sur https://console.anthropic.com, rubrique « API Keys »)."
  # -s : la clé ne s'affiche pas à l'écran pendant que tu la colles.
  read -r -s -p "Colle ta clé ici puis appuie sur Entrée (rien ne s'affiche, c'est normal) : " CLE
  echo
  if [ -z "$CLE" ]; then
    echo "Aucune clé saisie. Relance le lanceur quand tu l'auras."
    exit 1
  fi
  # Remplace la ligne de la clé dans .env (sans afficher la clé).
  CLE="$CLE" python - <<'PY'
import os, pathlib
fichier = pathlib.Path(".env")
lignes = [
    "ANTHROPIC_API_KEY=" + os.environ["CLE"].strip()
    if ligne.startswith("ANTHROPIC_API_KEY=") else ligne
    for ligne in fichier.read_text(encoding="utf-8").splitlines()
]
fichier.write_text("\n".join(lignes) + "\n", encoding="utf-8")
PY
  unset CLE
  chmod 600 .env  # seul ton compte peut lire ce fichier
  echo "Clé enregistrée dans .env (ce fichier n'est jamais envoyé sur GitHub)."
fi

# --- 5. Ouvrir le navigateur dans 3 secondes, puis démarrer le serveur ---
URL="http://127.0.0.1:8000"
(
  sleep 3
  if command -v open >/dev/null 2>&1; then open "$URL"          # Mac
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL" # Linux
  fi
) >/dev/null 2>&1 &
echo
echo "Serveur démarré sur $URL  (Ctrl+C pour l'arrêter)"
exec python -m uvicorn app.main:app
