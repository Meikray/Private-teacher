"""Point d'entrée du serveur de l'Assistant Professeur Personnel.

Ce fichier ne contient que les « routes » (les adresses de l'API). Le
travail est fait par les modules spécialisés :
- app/ia.py        : la discussion avec Claude ;
- app/memoire.py   : la mémoire pédagogique locale (SQLite) ;
- app/documents.py : les documents de cours ;
- app/modes.py     : les modes du professeur ;
- app/parcours.py  : la carte des concepts.
"""

import json
from pathlib import Path
from typing import Literal

import anthropic
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import documents, ia, memoire
from app.modes import DETAILS, MODE_PAR_DEFAUT, MODES, lister_modes
from app.parcours import DOMAINES, ETATS

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


# Adresse principale (/) : affiche la page de l'application.
@app.get("/")
def page_accueil():
    # FileResponse renvoie un fichier tel quel au navigateur.
    return FileResponse(DOSSIER_STATIC / "index.html")


# ---------------------------------------------------------------------------
# Discussion avec le professeur
# ---------------------------------------------------------------------------


# Un message de la conversation.
# Literal["user", "assistant"] n'accepte QUE ces deux valeurs : la page ne
# peut pas se faire passer pour le « système » et changer les consignes.
class Message(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1)


# Forme des données reçues : toute la conversation (du plus ancien message
# au plus récent) et les réglages choisis sur la page.
class Conversation(BaseModel):
    historique: list[Message] = Field(min_length=1)
    mode: str = MODE_PAR_DEFAUT
    detail: Literal["court", "normal", "detaille"] = "normal"
    recherche_web: bool = False


# Forme des données renvoyées : la réponse et les concepts mis à jour
# (la carte 3D s'en sert pour se rafraîchir).
class ReponseProfesseur(BaseModel):
    reponse: str
    concepts_mis_a_jour: list[str]


def construire_contexte(donnees):
    """Assemble les informations ajoutées aux consignes du professeur."""
    morceaux = [MODES[donnees.mode]["consigne"]]
    if DETAILS[donnees.detail]:
        morceaux.append(DETAILS[donnees.detail])
    morceaux.append(memoire.resume_pour_professeur())
    extraits = documents.contexte_pour_professeur(donnees.historique[-1].content)
    if extraits:
        morceaux.append(extraits)
    return "\n\n".join(morceaux)


def verifier(donnees):
    """Vérifications communes aux deux routes de discussion."""
    if donnees.mode not in MODES:
        raise HTTPException(status_code=422, detail="Mode inconnu.")
    if donnees.historique[-1].role != "user":
        raise HTTPException(
            status_code=422, detail="Le dernier message doit venir de l'élève."
        )


def creer_executeur(concepts_mis_a_jour):
    """Crée la fonction appelée quand l'IA utilise l'outil de progression.

    Les concepts mis à jour sont ajoutés à la liste concepts_mis_a_jour.
    """
    def executer_outil(nom, entree):
        if nom != "enregistrer_progression":
            return "Outil inconnu."
        resultat = memoire.appliquer_progression(entree)
        concepts_mis_a_jour.extend(resultat["mis_a_jour"])
        if resultat["ignores"]:
            return "Enregistré. Identifiants inconnus ignorés : " + ", ".join(resultat["ignores"])
        return "Progression enregistrée."

    return executer_outil


def traduire_erreur(erreur):
    """Transforme une erreur de l'IA en (code HTTP, message compréhensible).

    L'ordre compte : on teste les erreurs les plus précises d'abord.
    Renvoie None si l'erreur n'est pas une erreur connue de l'IA.
    """
    if isinstance(erreur, ia.ErreurFournisseur):
        return erreur.code_http, erreur.message
    if isinstance(erreur, anthropic.AuthenticationError):
        return 500, "Clé API manquante ou invalide : vérifie ton fichier .env."
    if isinstance(erreur, anthropic.RateLimitError):
        return 429, "Trop de demandes, réessaie dans un instant."
    if isinstance(erreur, anthropic.APIConnectionError):
        return 503, "Impossible de joindre Claude. Vérifie ta connexion."
    if isinstance(erreur, anthropic.APIError):
        return 502, "Erreur du service Claude."
    if isinstance(erreur, anthropic.AnthropicError):
        # Dernier filet de sécurité : par exemple une clé API introuvable.
        return 500, "Problème de configuration de Claude : vérifie ta clé API dans le fichier .env."
    return None


# @app.post (et non @app.get) : la page ENVOIE des données au serveur.
# Cette route renvoie la réponse complète d'un coup (utile pour les tests
# et pour d'autres programmes). La page web utilise /chat/flux ci-dessous.
@app.post("/chat")
def chat(donnees: Conversation) -> ReponseProfesseur:
    verifier(donnees)
    # model_dump() transforme chaque Message en simple dictionnaire Python,
    # le format attendu par le module IA.
    historique = [message.model_dump() for message in donnees.historique]
    concepts_mis_a_jour = []
    try:
        texte = ia.demander_au_professeur(
            historique,
            contexte=construire_contexte(donnees),
            executer_outil=creer_executeur(concepts_mis_a_jour),
            recherche_web=donnees.recherche_web,
        )
    except (ia.ErreurFournisseur, anthropic.AnthropicError) as erreur:
        code, message = traduire_erreur(erreur)
        raise HTTPException(status_code=code, detail=message)

    memoire.enregistrer_activite("message")
    return ReponseProfesseur(reponse=texte, concepts_mis_a_jour=concepts_mis_a_jour)


# Même chose, mais la réponse est DIFFUSÉE au fur et à mesure : la page
# affiche le texte pendant que le professeur l'écrit. Format « NDJSON » :
# une ligne JSON par événement ({"type": "texte" | "statut" | "erreur" | "fin", ...}).
@app.post("/chat/flux")
def chat_flux(donnees: Conversation):
    verifier(donnees)
    historique = [message.model_dump() for message in donnees.historique]
    contexte = construire_contexte(donnees)
    concepts_mis_a_jour = []

    def evenements():
        ligne = lambda evenement: json.dumps(evenement, ensure_ascii=False) + "\n"
        try:
            for evenement in ia.demander_en_flux(
                historique,
                contexte=contexte,
                executer_outil=creer_executeur(concepts_mis_a_jour),
                recherche_web=donnees.recherche_web,
            ):
                yield ligne(evenement)
        except (ia.ErreurFournisseur, anthropic.AnthropicError) as erreur:
            # La réponse a déjà commencé : on ne peut plus changer le code
            # HTTP, donc l'erreur est envoyée comme un événement.
            yield ligne({"type": "erreur", "contenu": traduire_erreur(erreur)[1]})
            return
        memoire.enregistrer_activite("message")
        yield ligne({"type": "fin", "concepts_mis_a_jour": concepts_mis_a_jour})

    return StreamingResponse(evenements(), media_type="application/x-ndjson")


# ---------------------------------------------------------------------------
# Informations pour la page : modes, parcours, tableau de bord
# ---------------------------------------------------------------------------


@app.get("/api/config")
def config():
    """Quel professeur répond (IA locale gratuite ou Claude) ?"""
    return ia.description()


@app.get("/api/modes")
def modes():
    return {"modes": lister_modes(), "par_defaut": MODE_PAR_DEFAUT}


@app.get("/api/parcours")
def parcours():
    """La carte des connaissances : domaines, concepts et leur état."""
    return {"domaines": DOMAINES, "etats": ETATS, "concepts": memoire.lister_concepts()}


@app.get("/api/tableau-de-bord")
def tableau_de_bord():
    return memoire.tableau_de_bord()


# ---------------------------------------------------------------------------
# Mémoire pédagogique : voir, corriger, supprimer, réinitialiser (section 20)
# ---------------------------------------------------------------------------


class ModificationConcept(BaseModel):
    etat: int = Field(ge=0, le=len(ETATS) - 1)
    remarque: str = ""


@app.put("/api/concepts/{concept_id}")
def modifier_concept(concept_id: str, modification: ModificationConcept):
    if not memoire.mettre_a_jour_concept(concept_id, modification.etat, modification.remarque):
        raise HTTPException(status_code=404, detail="Concept inconnu.")
    return {"ok": True}


@app.delete("/api/concepts/{concept_id}")
def oublier_concept(concept_id: str):
    memoire.oublier_concept(concept_id)
    return {"ok": True}


@app.get("/api/erreurs")
def erreurs():
    return {"erreurs": memoire.lister_erreurs()}


@app.delete("/api/erreurs/{erreur_id}")
def supprimer_erreur(erreur_id: int):
    memoire.supprimer_erreur(erreur_id)
    return {"ok": True}


class Profil(BaseModel):
    objectifs: str = ""
    langage_etudie: str = ""
    niveau_estime: str = ""
    cours_actuels: str = ""


@app.get("/api/profil")
def lire_profil():
    return memoire.lire_profil()


@app.put("/api/profil")
def modifier_profil(profil: Profil):
    memoire.modifier_profil(profil.model_dump())
    return {"ok": True}


@app.post("/api/memoire/reinitialiser")
def reinitialiser_memoire():
    memoire.reinitialiser()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Documents de cours (section 16)
# ---------------------------------------------------------------------------


@app.get("/api/documents")
def lister_documents():
    return {"documents": documents.lister(), "extensions": sorted(documents.EXTENSIONS)}


@app.post("/api/documents")
async def importer_document(fichier: UploadFile):
    # On lit au plus TAILLE_MAX + 1 octets : suffisant pour détecter un
    # fichier trop gros sans le charger entièrement en mémoire.
    contenu = await fichier.read(documents.TAILLE_MAX + 1)
    try:
        return documents.importer(fichier.filename or "document", contenu)
    except documents.DocumentInvalide as erreur:
        raise HTTPException(status_code=400, detail=str(erreur))


@app.delete("/api/documents/{document_id}")
def supprimer_document(document_id: int):
    if not documents.supprimer(document_id):
        raise HTTPException(status_code=404, detail="Document introuvable.")
    return {"ok": True}
