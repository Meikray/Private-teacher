"""Tests du module IA (app/ia.py), avec un faux client Claude.

Aucun vrai appel à Claude n'est fait : pas de clé API, pas d'Internet,
pas de coût.
"""

from types import SimpleNamespace

from app import ia
from app.consignes import CONSIGNES_PROFESSEUR


class FauxClient:
    """Imite le client anthropic : client.beta.messages.create(...).

    Il note les paramètres reçus (pour les vérifier) et renvoie
    une réponse préparée à l'avance.
    """

    def __init__(self, reponse_preparee):
        self.parametres_recus = None
        self.reponse_preparee = reponse_preparee
        # SimpleNamespace crée un objet simple avec les attributs donnés :
        # ici, il permet d'écrire client.beta.messages.create(...).
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **parametres):
        self.parametres_recus = parametres
        return self.reponse_preparee


HISTORIQUE = [{"role": "user", "content": "Qu'est-ce qu'une boucle ?"}]


def reponse_normale():
    # Une réponse typique d'Opus 5.5 : un bloc de réflexion (vide)
    # suivi d'un bloc de texte.
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            SimpleNamespace(type="text", text="À ton avis, que fait une boucle ?"),
        ],
    )


def test_envoie_les_bons_parametres():
    faux = FauxClient(reponse_normale())
    ia.demander_au_professeur(HISTORIQUE, client=faux)

    recus = faux.parametres_recus
    assert recus["model"] == "claude-opus-5-5"
    assert recus["system"] == CONSIGNES_PROFESSEUR
    assert recus["messages"] == HISTORIQUE
    assert recus["output_config"] == {"effort": "medium"}
    assert recus["fallbacks"] == "default"
    assert recus["betas"] == ["server-side-fallback-2026-07-01"]


def test_garde_seulement_les_blocs_de_texte():
    faux = FauxClient(reponse_normale())
    texte = ia.demander_au_professeur(HISTORIQUE, client=faux)
    assert texte == "À ton avis, que fait une boucle ?"


def test_refus_renvoie_le_message_prevu():
    refus = SimpleNamespace(stop_reason="refusal", content=[])
    faux = FauxClient(refus)
    texte = ia.demander_au_professeur(HISTORIQUE, client=faux)
    assert texte == ia.MESSAGE_REFUS
