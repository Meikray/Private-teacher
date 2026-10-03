"""Tests du module IA (app/ia.py), avec un faux client Claude.

Aucun vrai appel à Claude n'est fait : pas de clé API, pas d'Internet,
pas de coût.
"""

from types import SimpleNamespace

from app import ia
from app.consignes import CONSIGNES_PROFESSEUR


class FauxClient:
    """Imite le client anthropic : client.beta.messages.create(...).

    Il note les paramètres reçus à chaque appel (pour les vérifier) et
    renvoie, dans l'ordre, les réponses préparées à l'avance.
    """

    def __init__(self, *reponses_preparees):
        self.appels = []
        self.reponses = list(reponses_preparees)
        # SimpleNamespace crée un objet simple avec les attributs donnés :
        # ici, il permet d'écrire client.beta.messages.create(...).
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self.create))

    def create(self, **parametres):
        # On copie la liste des messages : la boucle la modifie ensuite.
        self.appels.append({**parametres, "messages": list(parametres["messages"])})
        return self.reponses.pop(0)


HISTORIQUE = [{"role": "user", "content": "Qu'est-ce qu'une boucle ?"}]


def texte(contenu):
    return SimpleNamespace(type="text", text=contenu)


def reponse_normale():
    # Une réponse typique d'Opus 5.5 : un bloc de réflexion (vide)
    # suivi d'un bloc de texte.
    return SimpleNamespace(
        stop_reason="end_turn",
        content=[
            SimpleNamespace(type="thinking", thinking=""),
            texte("À ton avis, que fait une boucle ?"),
        ],
    )


def test_envoie_les_bons_parametres():
    faux = FauxClient(reponse_normale())
    ia.demander_au_professeur(HISTORIQUE, contexte="MODE TEST", client=faux)

    recus = faux.appels[0]
    assert recus["model"] == "claude-opus-5-5"
    assert recus["system"][0]["text"] == CONSIGNES_PROFESSEUR
    assert recus["system"][1]["text"] == "MODE TEST"
    assert recus["messages"] == HISTORIQUE
    assert recus["output_config"] == {"effort": "medium"}
    assert recus["fallbacks"] == "default"
    assert recus["betas"] == ["server-side-fallback-2026-07-01"]
    noms_outils = [outil["name"] for outil in recus["tools"]]
    assert noms_outils == ["enregistrer_progression"]


def test_recherche_web_ajoute_l_outil():
    faux = FauxClient(reponse_normale())
    ia.demander_au_professeur(HISTORIQUE, recherche_web=True, client=faux)
    noms_outils = [outil["name"] for outil in faux.appels[0]["tools"]]
    assert noms_outils == ["enregistrer_progression", "web_search"]


def test_garde_seulement_les_blocs_de_texte():
    faux = FauxClient(reponse_normale())
    reponse = ia.demander_au_professeur(HISTORIQUE, client=faux)
    assert reponse == "À ton avis, que fait une boucle ?"


def test_refus_renvoie_le_message_prevu():
    refus = SimpleNamespace(stop_reason="refusal", content=[])
    faux = FauxClient(refus)
    reponse = ia.demander_au_professeur(HISTORIQUE, client=faux)
    assert reponse == ia.MESSAGE_REFUS


def test_boucle_d_outils():
    # 1er appel : Claude écrit un texte puis appelle l'outil de progression.
    appel_outil = SimpleNamespace(
        type="tool_use", id="outil_1", name="enregistrer_progression",
        input={"concepts": []},
    )
    premiere = SimpleNamespace(
        stop_reason="tool_use", content=[texte("Très bien !"), appel_outil]
    )
    # 2e appel : Claude termine sa réponse.
    seconde = SimpleNamespace(stop_reason="end_turn", content=[texte("Continuons.")])
    faux = FauxClient(premiere, seconde)

    appels_outil = []

    def executer_outil(nom, entree):
        appels_outil.append((nom, entree))
        return "Progression enregistrée."

    reponse = ia.demander_au_professeur(HISTORIQUE, executer_outil=executer_outil, client=faux)

    assert appels_outil == [("enregistrer_progression", {"concepts": []})]
    assert reponse == "Très bien !\n\nContinuons."
    # Le 2e appel renvoie la réponse de Claude puis le résultat de l'outil.
    messages = faux.appels[1]["messages"]
    assert messages[-2] == {"role": "assistant", "content": premiere.content}
    assert messages[-1]["content"][0] == {
        "type": "tool_result",
        "tool_use_id": "outil_1",
        "content": "Progression enregistrée.",
    }


def test_la_boucle_est_limitee():
    # Un Claude qui appellerait des outils sans fin : la boucle doit s'arrêter.
    appel = SimpleNamespace(type="tool_use", id="x", name="enregistrer_progression", input={})
    reponses = [SimpleNamespace(stop_reason="tool_use", content=[appel])] * (ia.MAX_TOURS + 2)
    faux = FauxClient(*reponses)
    ia.demander_au_professeur(HISTORIQUE, client=faux)
    assert len(faux.appels) == ia.MAX_TOURS
