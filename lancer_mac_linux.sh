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
  echo "Il faut mettre ta clé API dans le fichier .env."
  echo "L'éditeur va s'ouvrir : remplace « mets-ta-cle-ici » par ta clé, enregistre et quitte."
  read -r -p "Appuie sur Entrée pour ouvrir l'éditeur..." _
  "${EDITOR:-nano}" .env
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
