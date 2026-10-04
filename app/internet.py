"""Accès à Internet pour l'IA locale (outils lire_page_web et rechercher_wikipedia).

Le professeur peut :
- lire une page web ou un PDF à partir d'un lien (par exemple un cours de la
  liste free-programming-books) ;
- chercher une notion sur Wikipédia en français (API publique et gratuite).

SÉCURITÉ : l'IA choisit elle-même les liens, donc on se protège :
- seuls http:// et https:// sont acceptés ;
- les adresses de ton ordinateur et de ton réseau local (127.0.0.1, 192.168.x.x,
  etc.) sont refusées : l'IA ne peut pas fouiller ta machine ou ta box ;
- la taille téléchargée et le temps d'attente sont limités ;
- le texte renvoyé est raccourci pour tenir dans la « mémoire de travail » du modèle.
"""

import html
import io
import ipaddress
import re
import socket
from html.parser import HTMLParser
from urllib.parse import quote, urljoin, urlparse

import httpx
from pypdf import PdfReader

TAILLE_MAX_TELECHARGEMENT = 3 * 1024 * 1024  # 3 Mo
LONGUEUR_MAX_TEXTE = 4000  # caractères renvoyés à l'IA (assez court pour un modèle local)
DELAI = 20  # secondes
MAX_REDIRECTIONS = 5

# Wikimedia demande d'identifier les programmes qui utilisent son API.
# Attention : un en-tête HTTP ne peut contenir que des caractères ASCII
# (pas d'accents), sinon la requête échoue.
EN_TETES = {"User-Agent": "AssistantProfesseurPersonnel/1.0 (projet educatif personnel)"}


class AccesRefuse(Exception):
    """Lien refusé (protocole, adresse locale...)."""


def verifier_url(url):
    """Lève AccesRefuse si l'URL n'est pas une adresse publique http(s)."""
    morceaux = urlparse(url)
    if morceaux.scheme not in ("http", "https") or not morceaux.hostname:
        raise AccesRefuse("Seuls les liens http:// et https:// sont acceptés.")
    try:
        adresses = {info[4][0] for info in socket.getaddrinfo(morceaux.hostname, None)}
    except socket.gaierror:
        raise AccesRefuse(f"Site introuvable : {morceaux.hostname}")
    for adresse in adresses:
        ip = ipaddress.ip_address(adresse.split("%")[0])
        if not ip.is_global:
            raise AccesRefuse("Les adresses locales ou privées sont interdites.")


class _ExtracteurTexte(HTMLParser):
    """Garde le texte visible d'une page HTML (sans scripts ni styles)."""

    IGNORES = {"script", "style", "noscript", "svg", "head"}
    BLOCS = {"p", "div", "br", "li", "h1", "h2", "h3", "h4", "tr", "pre", "section", "article"}

    def __init__(self):
        super().__init__()
        self.morceaux = []
        self.profondeur_ignoree = 0

    def handle_starttag(self, balise, attributs):
        if balise in self.IGNORES:
            self.profondeur_ignoree += 1
        elif balise in self.BLOCS:
            self.morceaux.append("\n")

    def handle_endtag(self, balise):
        if balise in self.IGNORES and self.profondeur_ignoree:
            self.profondeur_ignoree -= 1

    def handle_data(self, donnees):
        if not self.profondeur_ignoree:
            self.morceaux.append(donnees)


def html_vers_texte(source):
    extracteur = _ExtracteurTexte()
    extracteur.feed(source)
    texte = html.unescape("".join(extracteur.morceaux))
    texte = re.sub(r"[ \t]+", " ", texte)
    return re.sub(r"\n\s*\n+", "\n\n", texte).strip()


def _telecharger(url, client):
    """Télécharge une URL en vérifiant chaque redirection. Renvoie (réponse, contenu)."""
    for _ in range(MAX_REDIRECTIONS + 1):
        verifier_url(url)
        with client.stream("GET", url, headers=EN_TETES) as reponse:
            if reponse.is_redirect and "location" in reponse.headers:
                url = urljoin(url, reponse.headers["location"])
                continue
            contenu = b""
            for bloc in reponse.iter_bytes():
                contenu += bloc
                if len(contenu) > TAILLE_MAX_TELECHARGEMENT:
                    break
            return reponse, contenu[:TAILLE_MAX_TELECHARGEMENT], url
    raise AccesRefuse("Trop de redirections.")


def lire_page(url, client=None):
    """Renvoie le texte d'une page web ou d'un PDF (raccourci), ou un message d'erreur."""
    client = client or httpx.Client(timeout=DELAI, follow_redirects=False)
    try:
        reponse, contenu, url_finale = _telecharger(url.strip(), client)
    except AccesRefuse as erreur:
        return f"Accès refusé : {erreur}"
    except httpx.HTTPError:
        return f"Impossible d'ouvrir {url} (site injoignable ou trop lent)."

    if reponse.status_code >= 400:
        return f"Le site a répondu par une erreur {reponse.status_code} : la page n'existe peut-être plus."

    type_contenu = reponse.headers.get("content-type", "")
    if "pdf" in type_contenu or url_finale.lower().endswith(".pdf"):
        try:
            lecteur = PdfReader(io.BytesIO(contenu))
            texte = "\n".join((page.extract_text() or "") for page in lecteur.pages[:30])
        except Exception:
            return "Ce PDF n'a pas pu être lu (fichier trop gros, abîmé ou scanné)."
    elif "html" in type_contenu or not type_contenu:
        texte = html_vers_texte(contenu.decode(reponse.encoding or "utf-8", errors="replace"))
    elif type_contenu.startswith("text/"):
        texte = contenu.decode(reponse.encoding or "utf-8", errors="replace")
    else:
        return f"Type de contenu non pris en charge ({type_contenu})."

    texte = texte.strip()
    if not texte:
        return "La page ne contient pas de texte lisible."
    if len(texte) > LONGUEUR_MAX_TEXTE:
        texte = texte[:LONGUEUR_MAX_TEXTE] + "\n[… texte raccourci …]"
    return f"Source : {url_finale}\n\n{texte}"


def rechercher_wikipedia(requete, client=None):
    """Cherche sur Wikipédia en français et renvoie les meilleurs résultats."""
    client = client or httpx.Client(timeout=DELAI)
    try:
        reponse = client.get(
            "https://fr.wikipedia.org/w/api.php",
            params={
                "action": "query", "list": "search", "srsearch": requete,
                "srlimit": 5, "format": "json", "utf8": 1,
            },
            headers=EN_TETES,
        )
        resultats = reponse.json()["query"]["search"]
    except (httpx.HTTPError, ValueError, KeyError):
        return "La recherche sur Wikipédia n'a pas fonctionné (pas d'Internet ?)."

    if not resultats:
        return f"Aucun résultat sur Wikipédia pour « {requete} »."
    lignes = [f"Résultats Wikipédia pour « {requete} » :"]
    for r in resultats:
        extrait = html_vers_texte(r.get("snippet", ""))
        lien = "https://fr.wikipedia.org/wiki/" + quote(r["title"].replace(" ", "_"))
        lignes.append(f"- {r['title']} : {extrait} ({lien})")
    lignes.append("Utilise lire_page_web avec un de ces liens pour lire l'article.")
    return "\n".join(lignes)


# Les deux outils, au format attendu par Ollama.
OUTILS_INTERNET = [
    {
        "type": "function",
        "function": {
            "name": "lire_page_web",
            "description": (
                "Lit le contenu d'une page web ou d'un PDF à partir de son lien "
                "(http/https). Utilise-le pour consulter un cours, une documentation "
                "officielle ou un article. Cite toujours le lien utilisé dans ta réponse."
            ),
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "Le lien complet."}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rechercher_wikipedia",
            "description": (
                "Cherche une notion sur Wikipédia en français et renvoie des titres, "
                "des extraits et des liens."
            ),
            "parameters": {
                "type": "object",
                "properties": {"requete": {"type": "string", "description": "Les mots à chercher."}},
                "required": ["requete"],
            },
        },
    },
]

NOMS_OUTILS_INTERNET = {outil["function"]["name"] for outil in OUTILS_INTERNET}

CONSIGNE_INTERNET = (
    "ACCÈS À INTERNET : tu peux lire une page web ou un PDF avec l'outil "
    "lire_page_web, et chercher une notion avec rechercher_wikipedia. Utilise-les "
    "quand l'élève te donne un lien, quand tu veux vérifier une information ou "
    "quand tu recommandes un cours. Cite toujours le lien de la source. Si une "
    "page est inaccessible, dis-le et propose une alternative."
)


def executer(nom, arguments):
    """Exécute un outil Internet et renvoie son résultat (texte)."""
    if nom == "lire_page_web":
        return lire_page(str(arguments.get("url", "")))
    if nom == "rechercher_wikipedia":
        return rechercher_wikipedia(str(arguments.get("requete", "")))
    return "Outil inconnu."
