"""Point d'entrée du serveur de l'Assistant Professeur Personnel.

Ce fichier contient :
- une route de test (/health) pour vérifier que le serveur répond ;
- l'affichage de la page web de discussion (dossier static/).
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Chemin du dossier static/, calculé à partir de l'emplacement de ce fichier.
# Path(__file__) = ce fichier (app/main.py) ; .parent = le dossier app/ ;
# .parent.parent = la racine du projet. Ainsi, le serveur trouve toujours
# static/, quel que soit le dossier d'où on le lance.
DOSSIER_STATIC = Path(__file__).parent.parent / "static"

# Crée l'application serveur. Le titre apparaît dans la documentation
# automatique de l'API (page /docs).
app = FastAPI(title="Assistant Professeur Personnel")

# Rend accessibles les fichiers du dossier static/ (HTML, CSS, JS)
# à l'adresse /static (ex. /static/style.css).
app.mount("/static", StaticFiles(directory=DOSSIER_STATIC), name="static")


# Le « décorateur » @app.get relie une adresse (ici /health) à une fonction :
# quand quelqu'un visite /health, FastAPI appelle la fonction health().
@app.get("/health")
def health():
    # FastAPI transforme automatiquement ce dictionnaire Python en JSON.
    return {"status": "ok"}


# Adresse principale (/) : affiche la page de discussion.
@app.get("/")
def page_accueil():
    # FileResponse renvoie un fichier tel quel au navigateur.
    return FileResponse(DOSSIER_STATIC / "index.html")
