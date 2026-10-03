"""Tests de la route /chat (version « écho »)."""

from fastapi.testclient import TestClient

from app.main import app

# TestClient est un « faux navigateur » qui interroge le serveur
# sans avoir besoin de le démarrer vraiment.
client = TestClient(app)


def test_chat_echo():
    # Un message normal doit être renvoyé en écho.
    response = client.post("/chat", json={"message": "bonjour"})
    assert response.status_code == 200
    assert response.json() == {"reponse": "Tu as écrit : bonjour"}


def test_chat_refuse_donnees_invalides():
    # Sans champ "message", FastAPI doit refuser la requête.
    # 422 est le code HTTP qui signifie « données invalides ».
    response = client.post("/chat", json={"autre_champ": "bonjour"})
    assert response.status_code == 422
