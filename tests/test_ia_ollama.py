"""Tests du fournisseur gratuit et local (Ollama), avec un faux serveur Ollama.

httpx.MockTransport remplace le réseau : aucune requête ne sort de
l'ordinateur et Ollama n'a pas besoin d'être installé pour les tests.
"""

import json

import httpx
import pytest

from app import ia


@pytest.fixture(autouse=True)
def fournisseur_ollama(monkeypatch):
    monkeypatch.setenv("FOURNISSEUR", "ollama")
    monkeypatch.setenv("MODELE_OLLAMA", "qwen2.5:7b")


def faux_ollama(reponses):
    """Crée un client httpx qui renvoie les réponses prévues, dans l'ordre,
    et garde une copie de chaque requête reçue."""
    requetes = []

    def repondre(requete):
        requetes.append(json.loads(requete.content))
        statut, corps = reponses[len(requetes) - 1]
        return httpx.Response(statut, json=corps) if isinstance(corps, dict) else httpx.Response(statut, text=corps)

    return httpx.Client(transport=httpx.MockTransport(repondre)), requetes


HISTORIQUE = [{"role": "user", "content": "Qu'est-ce qu'une boucle ?"}]


def test_reponse_simple():
    client, requetes = faux_ollama([(200, {"message": {"role": "assistant", "content": "À ton avis ?"}})])
    reponse = ia.demander_au_professeur(HISTORIQUE, contexte="MODE TEST", client=client)

    assert reponse == "À ton avis ?"
    corps = requetes[0]
    assert corps["model"] == "qwen2.5:7b"
    assert corps["stream"] is False
    assert corps["messages"][0]["role"] == "system"
    assert corps["messages"][0]["content"].endswith("MODE TEST")
    assert corps["messages"][1:] == HISTORIQUE
    assert corps["tools"][0]["function"]["name"] == "enregistrer_progression"


def test_boucle_d_outils():
    appel = {"function": {"name": "enregistrer_progression", "arguments": {"concepts": []}}}
    client, requetes = faux_ollama([
        (200, {"message": {"role": "assistant", "content": "", "tool_calls": [appel]}}),
        (200, {"message": {"role": "assistant", "content": "Continuons."}}),
    ])
    recus = []

    def executer_outil(nom, entree):
        recus.append((nom, entree))
        return "Progression enregistrée."

    reponse = ia.demander_au_professeur(HISTORIQUE, executer_outil=executer_outil, client=client)

    assert reponse == "Continuons."
    assert recus == [("enregistrer_progression", {"concepts": []})]
    dernier = requetes[1]["messages"][-1]
    assert dernier == {
        "role": "tool", "tool_name": "enregistrer_progression",
        "content": "Progression enregistrée.",
    }


def test_modele_sans_outils():
    # Un modèle qui ne gère pas les outils : on réessaie sans outils.
    client, requetes = faux_ollama([
        (400, '{"error":"qwen does not support tools"}'),
        (200, {"message": {"role": "assistant", "content": "Bonjour"}}),
    ])
    assert ia.demander_au_professeur(HISTORIQUE, client=client) == "Bonjour"
    assert "tools" not in requetes[1]


def test_modele_non_installe():
    client, _ = faux_ollama([(404, {"error": "model 'qwen2.5:7b' not found"})])
    with pytest.raises(ia.ErreurFournisseur, match="ollama pull qwen2.5:7b"):
        ia.demander_au_professeur(HISTORIQUE, client=client)


def test_ollama_non_lance():
    def refuser(requete):
        raise httpx.ConnectError("refusé", request=requete)

    client = httpx.Client(transport=httpx.MockTransport(refuser))
    with pytest.raises(ia.ErreurFournisseur) as erreur:
        ia.demander_au_professeur(HISTORIQUE, client=client)
    assert erreur.value.code_http == 503
    assert "Ollama" in erreur.value.message


def test_description():
    assert ia.description() == {
        "fournisseur": "ollama", "modele": "qwen2.5:7b", "gratuit": True, "recherche_web": False,
    }
