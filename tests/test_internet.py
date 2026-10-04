"""Tests de l'accès à Internet (app/internet.py), sans vrai réseau.

socket.getaddrinfo (la « résolution » d'un nom de site en adresse IP) est
remplacé par une fausse version, et httpx.MockTransport remplace le réseau.
"""

import io
import socket

import httpx
import pytest
from pypdf import PdfWriter

from app import internet

# Fausse résolution DNS : nom de site -> adresse IP.
ADRESSES = {
    "exemple.org": "93.184.216.34",
    "fr.wikipedia.org": "185.15.58.224",
    "piege.org": "127.0.0.1",
    "box.maison": "192.168.1.1",
}


@pytest.fixture(autouse=True)
def faux_dns(monkeypatch):
    def resoudre(nom, *args, **kwargs):
        if nom not in ADRESSES:
            raise socket.gaierror("inconnu")
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ADRESSES[nom], 0))]

    monkeypatch.setattr(socket, "getaddrinfo", resoudre)


def client_qui_repond(fonction):
    return httpx.Client(transport=httpx.MockTransport(fonction))


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:8000/api/profil",
    "http://localhost/",
    "http://piege.org/",
    "http://box.maison/",
    "file:///etc/passwd",
    "ftp://exemple.org/",
])
def test_refuse_les_adresses_dangereuses(url):
    # Aucune requête ne doit partir : le client lèverait une erreur s'il était appelé.
    def interdit(requete):
        raise AssertionError("requête envoyée alors qu'elle devait être bloquée")

    resultat = internet.lire_page(url, client=client_qui_repond(interdit))
    assert resultat.startswith("Accès refusé") or "introuvable" in resultat


def test_lit_une_page_html():
    page = (
        "<html><head><title>x</title><style>p{}</style></head><body>"
        "<script>alert(1)</script><h1>Les pointeurs</h1><p>Un pointeur contient une adresse.</p>"
        "</body></html>"
    )
    client = client_qui_repond(lambda r: httpx.Response(200, html=page))
    texte = internet.lire_page("https://exemple.org/cours", client=client)
    assert texte.startswith("Source : https://exemple.org/cours")
    assert "Un pointeur contient une adresse." in texte
    assert "alert" not in texte and "p{}" not in texte


def test_redirection_vers_une_adresse_locale_bloquee():
    def repondre(requete):
        if requete.url.host == "exemple.org":
            return httpx.Response(302, headers={"location": "http://piege.org/secret"})
        raise AssertionError("la redirection n'aurait pas dû être suivie")

    texte = internet.lire_page("https://exemple.org/", client=client_qui_repond(repondre))
    assert texte.startswith("Accès refusé")


def test_lit_un_pdf():
    pdf = PdfWriter()
    pdf.add_blank_page(width=200, height=200)
    tampon = io.BytesIO()
    pdf.write(tampon)
    client = client_qui_repond(lambda r: httpx.Response(
        200, content=tampon.getvalue(), headers={"content-type": "application/pdf"}
    ))
    # Page blanche : le PDF est lu, mais il n'a pas de texte.
    assert internet.lire_page("https://exemple.org/c.pdf", client=client) == \
        "La page ne contient pas de texte lisible."


def test_page_introuvable():
    client = client_qui_repond(lambda r: httpx.Response(404, text="non"))
    assert "erreur 404" in internet.lire_page("https://exemple.org/vieux", client=client)


def test_texte_raccourci():
    client = client_qui_repond(lambda r: httpx.Response(200, text="a" * 20000))
    texte = internet.lire_page("https://exemple.org/long.txt", client=client)
    assert texte.endswith("[… texte raccourci …]")
    assert len(texte) < internet.LONGUEUR_MAX_TEXTE + 200


def test_recherche_wikipedia():
    donnees = {"query": {"search": [
        {"title": "Pointeur (programmation)", "snippet": "Un <span>pointeur</span> est"},
    ]}}

    def repondre(requete):
        assert requete.url.params["srsearch"] == "pointeur"
        assert "User-Agent" in requete.headers
        return httpx.Response(200, json=donnees)

    texte = internet.rechercher_wikipedia("pointeur", client=client_qui_repond(repondre))
    assert "Pointeur (programmation) : Un pointeur est" in texte
    assert "https://fr.wikipedia.org/wiki/Pointeur_%28programmation%29" in texte
