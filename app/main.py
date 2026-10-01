"""Point d'entrée du serveur de l'Assistant Professeur Personnel.

Pour l'instant, ce fichier contient seulement une route de test (/health)
qui permet de vérifier que le serveur démarre et répond.
"""

from fastapi import FastAPI

# Crée l'application serveur. Le titre apparaît dans la documentation
# automatique de l'API (page /docs).
app = FastAPI(title="Assistant Professeur Personnel")


# Le « décorateur » @app.get relie une adresse (ici /health) à une fonction :
# quand quelqu'un visite /health, FastAPI appelle la fonction health().
@app.get("/health")
def health():
    # FastAPI transforme automatiquement ce dictionnaire Python en JSON.
    return {"status": "ok"}
