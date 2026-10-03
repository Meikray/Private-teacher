"""Module IA : le seul fichier de l'application qui parle à Claude.

Si un jour on change de fournisseur d'IA, c'est uniquement ce fichier
qu'il faudra modifier.

La clé API n'apparaît nulle part ici : la bibliothèque anthropic la lit
elle-même dans la variable d'environnement ANTHROPIC_API_KEY.
"""

import anthropic

from app.consignes import CONSIGNES_PROFESSEUR

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

MESSAGE_REFUS = (
    "Je ne peux pas répondre à cette question. "
    "Essaie de la reformuler, ou pose-la autrement."
)


def demander_au_professeur(historique, client=None):
    """Envoie la conversation à Claude et renvoie la réponse du professeur.

    historique : liste de messages, du plus ancien au plus récent, par ex.
        [{"role": "user", "content": "Qu'est-ce qu'une variable ?"},
         {"role": "assistant", "content": "Bonne question ! ..."},
         {"role": "user", "content": "Et un pointeur ?"}]
    client : utilisé par les tests pour fournir un « faux Claude ».
        En temps normal, on le laisse vide et un vrai client est créé.
    """
    if client is None:
        client = anthropic.Anthropic()

    reponse = client.beta.messages.create(
        model=MODELE,
        max_tokens=MAX_TOKENS,
        system=CONSIGNES_PROFESSEUR,
        messages=historique,
        output_config={"effort": EFFORT},
        betas=[BETA_SECOURS],
        fallbacks="default",
    )

    # Même avec l'option de secours, toute la chaîne peut refuser.
    if reponse.stop_reason == "refusal":
        return MESSAGE_REFUS

    # La réponse est une liste de « blocs ». Elle peut commencer par des blocs
    # de réflexion (vides) : on ne garde que les blocs de type "text".
    textes = [bloc.text for bloc in reponse.content if bloc.type == "text"]
    return "\n".join(textes)
