"""Test d'intégration du module IA avec la VRAIE bibliothèque anthropic.

Au lieu d'un faux client, on utilise le vrai client anthropic, mais branché
sur un « faux réseau » (MockTransport) : aucune requête ne sort de
l'ordinateur. On vérifie ainsi que :
- la requête HTTP envoyée à l'API est correctement construite ;
- la boucle d'outils fonctionne avec les vrais objets de la bibliothèque.
"""

import json

import anthropic
import httpx2

from app import ia

# Deux réponses simulées de l'API : d'abord un appel d'outil, puis le texte final.
REPONSES = [
    {
        "id": "msg_1", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "stop_reason": "tool_use", "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "content": [
            {"type": "thinking", "thinking": "", "signature": "sig"},
            {"type": "text", "text": "Bien vu !"},
            {
                "type": "tool_use", "id": "toolu_1", "name": "enregistrer_progression",
                "input": {
                    "concepts": [{"id": "boucle", "etat": 3, "remarque": ""}],
                    "erreurs": [], "niveau_aide": 1, "exercice": "aucun",
                    "demande_solution_directe": False,
                },
            },
        ],
    },
    {
        "id": "msg_2", "type": "message", "role": "assistant", "model": "claude-opus-5-5",
        "stop_reason": "end_turn", "stop_sequence": None,
        "usage": {"input_tokens": 12, "output_tokens": 4},
        "content": [{"type": "text", "text": "Que se passe-t-il si i ne change jamais ?"}],
    },
]


def test_requetes_envoyees_par_le_vrai_sdk():
    requetes = []

    def faux_reseau(requete):
        requetes.append(requete)
        return httpx2.Response(200, json=REPONSES[len(requetes) - 1])

    client = anthropic.Anthropic(
        api_key="cle-de-test",
        http_client=anthropic.DefaultHttpxClient(transport=httpx2.MockTransport(faux_reseau)),
        max_retries=0,
    )
    outils_executes = []

    def executer_outil(nom, entree):
        outils_executes.append((nom, entree))
        return "Progression enregistrée."

    reponse = ia.demander_au_professeur(
        [{"role": "user", "content": "Ma boucle ne s'arrête pas."}],
        contexte="MODE TEST",
        executer_outil=executer_outil,
        client=client,
    )

    assert reponse == "Bien vu !\n\nQue se passe-t-il si i ne change jamais ?"
    assert outils_executes[0][1]["concepts"][0]["id"] == "boucle"

    # Première requête : paramètres et en-tête « bêta » de l'option de secours.
    premiere = requetes[0]
    assert premiere.url.path == "/v1/messages"
    assert "server-side-fallback-2026-07-01" in premiere.headers["anthropic-beta"]
    corps = json.loads(premiere.content)
    assert corps["model"] == "claude-opus-5-5"
    assert corps["fallbacks"] == "default"
    assert corps["output_config"] == {"effort": "medium"}
    assert corps["tools"][0]["name"] == "enregistrer_progression"
    assert corps["tools"][0]["strict"] is True
    assert corps["system"][1]["text"] == "MODE TEST"

    # Deuxième requête : la réponse précédente (réflexion comprise) est
    # renvoyée telle quelle, suivie du résultat de l'outil.
    corps = json.loads(requetes[1].content)
    assistant, resultat = corps["messages"][-2], corps["messages"][-1]
    assert assistant["role"] == "assistant"
    assert [bloc["type"] for bloc in assistant["content"]] == ["thinking", "text", "tool_use"]
    assert resultat["content"][0] == {
        "type": "tool_result", "tool_use_id": "toolu_1", "content": "Progression enregistrée.",
    }
