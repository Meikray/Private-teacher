"""Tests des documents de cours (app/documents.py) et de leurs routes."""

import io

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter

from app import documents
from app.main import app

client = TestClient(app)

COURS = (
    "Un pointeur est une variable qui contient l'adresse mémoire d'une autre "
    "variable. On obtient l'adresse avec l'opérateur &."
).encode("utf-8")


def test_importer_puis_rechercher():
    info = documents.importer("cours_c.txt", COURS)
    assert info["nom"] == "cours_c.txt"

    passages = documents.rechercher("Qu'est-ce qu'un pointeur en mémoire ?")
    assert passages[0]["document"] == "cours_c.txt"
    assert "adresse" in passages[0]["passage"]

    contexte = documents.contexte_pour_professeur("pointeur")
    assert "Extrait de « cours_c.txt »" in contexte


def test_recherche_sans_rapport():
    documents.importer("cours_c.txt", COURS)
    assert documents.rechercher("météo Wi-Fi") == []


def test_refuse_une_extension_inconnue():
    with pytest.raises(documents.DocumentInvalide):
        documents.importer("virus.exe", b"MZ...")


def test_refuse_un_document_vide():
    with pytest.raises(documents.DocumentInvalide):
        documents.importer("vide.txt", b"   ")


def test_pdf_sans_texte_est_refuse():
    # Un PDF avec une page blanche : il n'y a aucun texte à extraire.
    pdf = PdfWriter()
    pdf.add_blank_page(width=200, height=200)
    tampon = io.BytesIO()
    pdf.write(tampon)
    with pytest.raises(documents.DocumentInvalide, match="Aucun texte"):
        documents.importer("scan.pdf", tampon.getvalue())


def test_supprimer():
    info = documents.importer("notes.md", COURS)
    assert documents.supprimer(info["id"])
    assert documents.lister() == []
    assert not documents.supprimer(info["id"])


def test_routes_documents():
    reponse = client.post(
        "/api/documents", files={"fichier": ("cours.txt", COURS, "text/plain")}
    )
    assert reponse.status_code == 200
    document_id = reponse.json()["id"]

    liste = client.get("/api/documents").json()["documents"]
    assert [d["nom"] for d in liste] == ["cours.txt"]

    assert client.delete(f"/api/documents/{document_id}").status_code == 200
    assert client.delete(f"/api/documents/{document_id}").status_code == 404


def test_route_refuse_un_mauvais_fichier():
    reponse = client.post(
        "/api/documents", files={"fichier": ("x.exe", b"MZ", "application/octet-stream")}
    )
    assert reponse.status_code == 400
