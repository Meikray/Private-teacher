"""Point d'entrée du serveur de l'Assistant Professeur Personnel.

Ce fichier contient :
- une route de test (/health) pour vérifier que le serveur répond ;
- l'affichage de la page web de discussion (dossier static/) ;
- la route /chat, qui transmet la conversation au professeur (Claude).
"""

from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import ia

# Lit le fichier .env (s'il existe) et rend ses variables, comme la clé API,
# visibles pour le programme. La clé n'est jamais écrite dans le code.
load_dotenv()

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


# Un message de la conversation.
# Literal["user", "assistant"] n'accepte QUE ces deux valeurs : la page ne
# peut pas se faire passer pour le « système » et changer les consignes.
class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str


# Forme des données reçues : toute la conversation, du plus ancien
# message au plus récent. Si la page envoie autre chose, FastAPI refuse
# automatiquement la requête.
class Conversation(BaseModel):
    historique: list[Message]


# Forme des données renvoyées : un objet JSON avec un champ "reponse".
class ReponseProfesseur(BaseModel):
    reponse: str


# @app.post (et non @app.get) : la page ENVOIE des données au serveur.
@app.post("/chat")
def chat(donnees: Conversation) -> ReponseProfesseur:
    # model_dump() transforme chaque Message en simple dictionnaire Python,
    # le format attendu par le module IA.
    historique = [message.model_dump() for message in donnees.historique]

    # On transforme chaque erreur possible en message compréhensible.
    # L'ordre compte : on teste les erreurs les plus précises d'abord.
    try:
        texte = ia.demander_au_professeur(historique)
    except anthropic.AuthenticationError:
        raise HTTPException(
            status_code=500,
            detail="Clé API manquante ou invalide : vérifie ton fichier .env.",
        )
    except anthropic.RateLimitError:
        raise HTTPException(
            status_code=429,
            detail="Trop de demandes, réessaie dans un instant.",
        )
    except anthropic.APIConnectionError:
        raise HTTPException(
            status_code=503,
            detail="Impossible de joindre Claude. Vérifie ta connexion.",
        )
    except anthropic.APIError:
        raise HTTPException(status_code=502, detail="Erreur du service Claude.")
    except anthropic.AnthropicError:
        # Dernier filet de sécurité : toute autre erreur de la bibliothèque,
        # par exemple une clé API introuvable (fichier .env absent).
        raise HTTPException(
            status_code=500,
            detail="Problème de configuration de Claude : vérifie ta clé API dans le fichier .env.",
        )

    return ReponseProfesseur(reponse=texte)
