"""Tests des routes de la mémoire, du parcours et du tableau de bord."""

from fastapi.testclient import TestClient

from app.main import app
from app.modes import MODES

client = TestClient(app)


def test_modes():
    donnees = client.get("/api/modes").json()
    assert donnees["par_defaut"] == "socratique"
    assert [m["id"] for m in donnees["modes"]] == list(MODES)
    # Les consignes internes ne sont pas envoyées à la page.
    assert "consigne" not in donnees["modes"][0]


def test_parcours():
    donnees = client.get("/api/parcours").json()
    assert len(donnees["etats"]) == 7
    assert any(c["id"] == "pointeurs" for c in donnees["concepts"])


def test_modifier_puis_oublier_un_concept():
    assert client.put("/api/concepts/boucle", json={"etat": 4}).status_code == 200
    concepts = {c["id"]: c for c in client.get("/api/parcours").json()["concepts"]}
    assert concepts["boucle"]["etat"] == 4

    assert client.delete("/api/concepts/boucle").status_code == 200
    concepts = {c["id"]: c for c in client.get("/api/parcours").json()["concepts"]}
    assert concepts["boucle"]["etat"] == 0


def test_modifier_un_concept_invalide():
    assert client.put("/api/concepts/inconnu", json={"etat": 2}).status_code == 404
    assert client.put("/api/concepts/boucle", json={"etat": 12}).status_code == 422


def test_profil():
    assert client.put("/api/profil", json={"objectifs": "IoT"}).status_code == 200
    assert client.get("/api/profil").json()["objectifs"] == "IoT"


def test_tableau_de_bord_et_reinitialisation():
    client.put("/api/concepts/gpio", json={"etat": 6})
    tableau = client.get("/api/tableau-de-bord").json()
    assert tableau["repartition"]["Autonome"] == 1

    assert client.post("/api/memoire/reinitialiser").status_code == 200
    tableau = client.get("/api/tableau-de-bord").json()
    assert tableau["repartition"]["Autonome"] == 0
