"""Test de la route /health du serveur."""

from fastapi.testclient import TestClient

from app.main import app

# TestClient est un « faux navigateur » : il interroge le serveur
# sans avoir besoin de le démarrer vraiment.
client = TestClient(app)


def test_health():
    # Simule une visite de l'adresse /health.
    response = client.get("/health")

    # assert = « je vérifie que… ». Si c'est faux, le test échoue.
    # 200 est le code HTTP qui signifie « tout va bien ».
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
