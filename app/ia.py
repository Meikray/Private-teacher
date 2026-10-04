"""Module IA : le seul fichier de l'application qui parle à une IA.

Deux « fournisseurs » sont possibles (variable FOURNISSEUR dans .env) :
- "ollama" (par défaut) : une IA GRATUITE qui tourne sur ton ordinateur
  grâce au logiciel Ollama (https://ollama.com). Pas de clé, pas de compte,
  et tes messages ne quittent pas ta machine ;
- "anthropic" : Claude, plus performant mais payant (clé API nécessaire,
  lue par la bibliothèque anthropic dans ANTHROPIC_API_KEY).

Fonctionnement : l'IA peut utiliser des « outils » pendant sa réponse.
- enregistrer_progression : elle note dans la mémoire locale ce qu'elle a
  observé (concepts compris ou fragiles, erreurs, niveau d'aide donné) ;
- accès à Internet (optionnel, case « Internet » des Réglages) :
  web_search pour Claude ; lire_page_web et rechercher_wikipedia pour
  l'IA locale (voir app/internet.py).
Quand l'IA appelle un outil, on l'exécute, on lui renvoie le résultat,
et elle continue sa réponse : c'est la « boucle d'outils ».
"""

import json
import os

import anthropic
import httpx

from app import internet
from app.consignes import CONSIGNES_PROFESSEUR
from app.parcours import CONCEPTS, ETATS

# Fournisseur par défaut : gratuit et local.
FOURNISSEUR_PAR_DEFAUT = "ollama"

# Modèle local par défaut : bon en français, sait utiliser des outils,
# environ 4,7 Go à télécharger, 8 Go de mémoire vive conseillés.
# Pour un PC modeste : "qwen2.5:3b" (environ 2 Go).
MODELE_OLLAMA_PAR_DEFAUT = "qwen2.5:7b"
URL_OLLAMA_PAR_DEFAUT = "http://127.0.0.1:11434"


class ErreurFournisseur(Exception):
    """Erreur compréhensible venant du fournisseur d'IA (ex. Ollama non lancé)."""

    def __init__(self, code_http, message):
        super().__init__(message)
        self.code_http = code_http
        self.message = message


def fournisseur():
    """Le fournisseur choisi dans .env ("ollama" ou "anthropic")."""
    return os.environ.get("FOURNISSEUR", FOURNISSEUR_PAR_DEFAUT).strip().lower()


def modele_ollama():
    return os.environ.get("MODELE_OLLAMA", MODELE_OLLAMA_PAR_DEFAUT).strip()


def description():
    """Texte affiché sur la page : quel professeur répond ?"""
    if fournisseur() == "anthropic":
        return {"fournisseur": "anthropic", "modele": MODELE, "gratuit": False,
                "recherche_web": True}
    return {"fournisseur": "ollama", "modele": modele_ollama(), "gratuit": True,
            "recherche_web": True}


# Le modèle Claude utilisé comme professeur (choisi par l'élève).
MODELE = "claude-opus-5-5"

# Nombre maximal de tokens dans une réponse. Ce plafond compte aussi la
# « réflexion » du modèle (toujours active sur Opus 5.5) : s'il est trop bas,
# la réponse risque d'être coupée.
MAX_TOKENS = 16000

# L'effort contrôle combien le modèle réfléchit (donc la qualité, le temps
# et le coût) : "low", "medium", "high", "xhigh" ou "max".
EFFORT = "medium"

# Option de secours : si Claude refuse une question à tort, un autre modèle
# choisi par Anthropic prend le relais. Elle nécessite cet en-tête « bêta ».
BETA_SECOURS = "server-side-fallback-2026-07-01"

# Nombre maximal d'allers-retours avec les outils pour une seule question
# (sécurité contre une boucle sans fin).
MAX_TOURS = 6

MESSAGE_REFUS = (
    "Je ne peux pas répondre à cette question. "
    "Essaie de la reformuler, ou pose-la autrement."
)

# Liste « identifiant : nom » des concepts, donnée à Claude pour qu'il
# utilise les bons identifiants quand il enregistre la progression.
_CATALOGUE = "\n".join(f"{c['id']} : {c['nom']}" for c in CONCEPTS)
_ETATS = ", ".join(f"{i} = {nom}" for i, nom in enumerate(ETATS))

OUTIL_PROGRESSION = {
    "name": "enregistrer_progression",
    "description": (
        "Enregistre dans la mémoire pédagogique locale ce que tu as observé chez "
        "l'élève. Appelle cet outil quand tu as appris quelque chose de nouveau sur "
        "son niveau (un concept découvert, compris, fragile ou maîtrisé ; une erreur "
        "révélatrice ; un exercice terminé), puis termine ta réponse normalement. "
        "N'en parle pas à l'élève sauf s'il le demande. Un concept n'est « Maîtrisé » "
        "ou plus que si l'élève l'a utilisé sans aide importante.\n"
        f"États possibles : {_ETATS}.\n"
        "niveau_aide : le niveau d'aide le plus élevé que tu as donné dans ce message "
        "(0 = aucune aide, 1 = question, 2 = indice léger, 3 = indice précis, "
        "4 = explication, 5 = solution guidée, 6 = solution complète).\n"
        f"Identifiants de concepts valides :\n{_CATALOGUE}"
    ),
    "strict": True,
    "input_schema": {
        "type": "object",
        "properties": {
            "concepts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "etat": {"type": "integer", "enum": list(range(len(ETATS)))},
                        "remarque": {"type": "string"},
                    },
                    "required": ["id", "etat", "remarque"],
                    "additionalProperties": False,
                },
            },
            "erreurs": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "concept": {"type": "string"},
                        "description": {"type": "string"},
                    },
                    "required": ["concept", "description"],
                    "additionalProperties": False,
                },
            },
            "niveau_aide": {"type": "integer", "enum": [0, 1, 2, 3, 4, 5, 6]},
            "exercice": {
                "type": "string",
                "enum": ["aucun", "reussi_sans_aide", "reussi_avec_aide", "echoue"],
            },
            "demande_solution_directe": {"type": "boolean"},
        },
        "required": [
            "concepts", "erreurs", "niveau_aide", "exercice", "demande_solution_directe",
        ],
        "additionalProperties": False,
    },
}

# Recherche web exécutée par Anthropic (outil « serveur »). Elle est payante
# en plus des tokens : on la limite à 3 recherches par question.
OUTIL_RECHERCHE_WEB = {"type": "web_search_20260209", "name": "web_search", "max_uses": 3}


def _sans_outil(nom, entree):
    """Exécuteur par défaut : n'enregistre rien."""
    return "Aucune action effectuée."


def demander_au_professeur(
    historique,
    contexte="",
    executer_outil=_sans_outil,
    recherche_web=False,
    client=None,
):
    """Envoie la conversation à l'IA choisie et renvoie la réponse (texte).

    Les paramètres sont décrits dans _demander_a_claude et _demander_a_ollama.
    """
    if fournisseur() == "anthropic":
        return _demander_a_claude(historique, contexte, executer_outil, recherche_web, client)
    return _demander_a_ollama(historique, contexte, executer_outil, recherche_web, client)


def _demander_a_claude(
    historique,
    contexte="",
    executer_outil=_sans_outil,
    recherche_web=False,
    client=None,
):
    """Envoie la conversation à Claude et renvoie la réponse du professeur (texte).

    historique : liste de messages, du plus ancien au plus récent, par ex.
        [{"role": "user", "content": "Qu'est-ce qu'une variable ?"},
         {"role": "assistant", "content": "Bonne question ! ..."},
         {"role": "user", "content": "Et un pointeur ?"}]
    contexte : informations ajoutées aux consignes (mode, profil, extraits de cours).
    executer_outil : fonction appelée quand Claude utilise un outil local ;
        elle reçoit (nom, entree) et renvoie un texte de résultat.
    recherche_web : True pour autoriser la recherche sur Internet.
    client : utilisé par les tests pour fournir un « faux Claude ».
        En temps normal, on le laisse vide et un vrai client est créé.
    """
    if client is None:
        client = anthropic.Anthropic()

    # Les consignes générales ne changent jamais : on les marque « à mettre en
    # cache » (moins cher et plus rapide). Le contexte, lui, change à chaque fois.
    system = [{
        "type": "text",
        "text": CONSIGNES_PROFESSEUR,
        "cache_control": {"type": "ephemeral"},
    }]
    if contexte:
        system.append({"type": "text", "text": contexte})

    outils = [OUTIL_PROGRESSION]
    if recherche_web:
        outils.append(OUTIL_RECHERCHE_WEB)

    messages = list(historique)
    morceaux = []  # le texte de chaque réponse de Claude

    for _ in range(MAX_TOURS):
        reponse = client.beta.messages.create(
            model=MODELE,
            max_tokens=MAX_TOKENS,
            system=system,
            tools=outils,
            messages=messages,
            output_config={"effort": EFFORT},
            betas=[BETA_SECOURS],
            fallbacks="default",
        )

        # Même avec l'option de secours, toute la chaîne peut refuser.
        if reponse.stop_reason == "refusal":
            morceaux.append(MESSAGE_REFUS)
            break

        # La réponse est une liste de « blocs ». Elle peut contenir des blocs
        # de réflexion (vides) ou d'outils : on ne garde que le texte.
        texte = "".join(bloc.text for bloc in reponse.content if bloc.type == "text")
        if texte.strip():
            morceaux.append(texte)

        if reponse.stop_reason == "tool_use":
            # On renvoie la réponse telle quelle (blocs de réflexion compris),
            # puis le résultat de chaque outil local appelé.
            messages.append({"role": "assistant", "content": reponse.content})
            resultats = [
                {
                    "type": "tool_result",
                    "tool_use_id": bloc.id,
                    "content": executer_outil(bloc.name, bloc.input),
                }
                for bloc in reponse.content
                if bloc.type == "tool_use"
            ]
            messages.append({"role": "user", "content": resultats})
            continue

        if reponse.stop_reason == "pause_turn":
            # Une recherche web longue a été mise en pause : on relance pour
            # que Claude continue là où il s'est arrêté.
            messages.append({"role": "assistant", "content": reponse.content})
            continue

        break  # réponse terminée (end_turn, max_tokens...)

    return "\n\n".join(morceaux)


# ---------------------------------------------------------------------------
# Ollama : IA gratuite et locale
# ---------------------------------------------------------------------------

# Le même outil de progression, au format attendu par Ollama.
OUTIL_PROGRESSION_OLLAMA = {
    "type": "function",
    "function": {
        "name": OUTIL_PROGRESSION["name"],
        "description": OUTIL_PROGRESSION["description"],
        "parameters": OUTIL_PROGRESSION["input_schema"],
    },
}


def _demander_a_ollama(
    historique, contexte="", executer_outil=_sans_outil, recherche_web=False, client=None,
):
    """Envoie la conversation au modèle local (Ollama) et renvoie la réponse.

    On utilise l'API HTTP d'Ollama (POST /api/chat), qui tourne sur ton
    ordinateur. client : un httpx.Client (les tests en fournissent un faux).
    """
    url = os.environ.get("OLLAMA_URL", URL_OLLAMA_PAR_DEFAUT).rstrip("/") + "/api/chat"
    modele = modele_ollama()
    # Un modèle local peut être lent : on lui laisse jusqu'à 10 minutes.
    client = client or httpx.Client(timeout=600)

    systeme = CONSIGNES_PROFESSEUR + ("\n\n" + contexte if contexte else "")
    outils = [OUTIL_PROGRESSION_OLLAMA]
    if recherche_web:
        outils += internet.OUTILS_INTERNET
        systeme += "\n\n" + internet.CONSIGNE_INTERNET
    messages = [{"role": "system", "content": systeme}, *historique]
    # Taille de la « mémoire de travail » du modèle (en tokens). Plus grande
    # avec Internet, car les pages lues prennent de la place.
    contexte_max = int(os.environ.get("CONTEXTE_OLLAMA", 16384 if recherche_web else 8192))
    morceaux = []

    for _ in range(MAX_TOURS):
        corps = {
            "model": modele,
            "messages": messages,
            "stream": False,
            "options": {"num_ctx": contexte_max},
        }
        if outils:
            corps["tools"] = outils

        try:
            reponse = client.post(url, json=corps)
        except httpx.ConnectError:
            raise ErreurFournisseur(
                503,
                "L'IA locale ne répond pas : lance l'application Ollama "
                "(ou tape « ollama serve » dans un terminal).",
            )
        except httpx.TimeoutException:
            raise ErreurFournisseur(
                504, "L'IA locale a mis trop de temps à répondre. Réessaie."
            )

        if reponse.status_code == 404:
            raise ErreurFournisseur(
                500,
                f"Le modèle « {modele} » n'est pas installé : tape "
                f"« ollama pull {modele} » dans un terminal.",
            )
        if reponse.status_code == 400 and "does not support tools" in reponse.text and outils:
            # Certains modèles ne savent pas utiliser d'outils : on continue
            # sans (la progression ne sera alors pas enregistrée automatiquement).
            outils = []
            continue
        if reponse.status_code != 200:
            raise ErreurFournisseur(502, "Erreur de l'IA locale : " + reponse.text[:200])

        message = reponse.json().get("message", {})
        texte = (message.get("content") or "").strip()
        if texte:
            morceaux.append(texte)

        appels = message.get("tool_calls") or []
        if not appels:
            break

        # On renvoie le message de l'IA, puis le résultat de chaque outil.
        messages.append(message)
        for appel in appels:
            fonction = appel.get("function", {})
            arguments = fonction.get("arguments") or {}
            if isinstance(arguments, str):
                try:
                    arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    arguments = {}
            nom = fonction.get("name", "")
            if nom in internet.NOMS_OUTILS_INTERNET:
                resultat = internet.executer(nom, arguments)
            else:
                resultat = executer_outil(nom, arguments)
            messages.append({"role": "tool", "tool_name": nom, "content": resultat})

    return "\n\n".join(morceaux)
