"""Tests de la page web (fichiers HTML, CSS et JavaScript)."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

# TestClient est un « faux navigateur » qui interroge le serveur
# sans avoir besoin de le démarrer vraiment.
client = TestClient(app)


def test_page_accueil():
    # L'adresse principale doit renvoyer la page HTML de l'application.
    response = client.get("/")
    assert response.status_code == 200
    assert "Assistant Professeur Personnel" in response.text
    assert "/static/js/main.js" in response.text


@pytest.mark.parametrize("fichier", [
    "style.css",
    "js/main.js",
    "js/api.js",
    "js/chat.js",
    "js/carte.js",
    "js/carte3d.js",
    "js/panneaux.js",
    "js/markdown.js",
    "js/voix.js",
    "js/reglages.js",
])
def test_fichiers_statiques(fichier):
    # Le navigateur doit pouvoir charger chaque fichier de l'interface.
    assert client.get(f"/static/{fichier}").status_code == 200
