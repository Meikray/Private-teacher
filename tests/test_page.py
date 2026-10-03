"""Tests de la page web de discussion."""

from fastapi.testclient import TestClient

from app.main import app

# TestClient est un « faux navigateur » qui interroge le serveur
# sans avoir besoin de le démarrer vraiment.
client = TestClient(app)


def test_page_accueil():
    # L'adresse principale doit renvoyer la page HTML de discussion.
    response = client.get("/")
    assert response.status_code == 200
    assert "Assistant Professeur Personnel" in response.text


def test_fichiers_statiques():
    # Le navigateur doit pouvoir charger le JavaScript et le CSS.
    assert client.get("/static/app.js").status_code == 200
    assert client.get("/static/style.css").status_code == 200
