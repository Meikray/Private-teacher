"""Documents de cours : import, extraction du texte et recherche (section 16).

Fonctionnement (une forme simple de « RAG ») :
1. l'élève importe un fichier (PDF, texte, Markdown, code source) ;
2. on extrait son texte et on le range dans data/documents/ (ignoré par Git) ;
3. à chaque question, on cherche les passages qui partagent le plus de mots
   avec la question, et on les envoie au professeur en indiquant clairement
   qu'ils viennent du cours de l'élève.

La recherche par mots-clés est volontairement simple et compréhensible.
Pour la faire évoluer (recherche « sémantique » par exemple), il suffit de
remplacer la fonction rechercher() : le reste de l'application ne change pas.
"""

import io
import re
import unicodedata
import uuid
from contextlib import closing
from datetime import datetime

from pypdf import PdfReader

from app import memoire

# Taille maximale d'un fichier importé (10 Mo).
TAILLE_MAX = 10 * 1024 * 1024

# Extensions acceptées : PDF + fichiers texte (notes, cours, code).
EXTENSIONS_TEXTE = {
    ".txt", ".md", ".c", ".h", ".cpp", ".hpp", ".ino", ".py", ".js",
    ".html", ".css", ".java", ".rs", ".sql", ".json", ".csv", ".asm", ".s",
}
EXTENSIONS = EXTENSIONS_TEXTE | {".pdf"}

# Longueur d'un passage (en caractères) et nombre de passages envoyés.
TAILLE_PASSAGE = 900
NB_PASSAGES = 3

# Petits mots trop fréquents pour aider la recherche.
MOTS_VIDES = set(
    "le la les un une des de du d l et ou a au aux en dans sur pour par avec "
    "est sont ce cet cette ces que qui quoi quel quelle comment pourquoi je tu "
    "il elle on nous vous ils elles mon ton son ma ta sa mes tes ses pas ne "
    "plus moins se sa y the of to and is in it".split()
)


class DocumentInvalide(Exception):
    """Fichier refusé (extension, taille, contenu illisible)."""


def dossier_documents():
    dossier = memoire.chemin_base().parent / "documents"
    dossier.mkdir(parents=True, exist_ok=True)
    return dossier


def _extension(nom):
    point = nom.rfind(".")
    return nom[point:].lower() if point != -1 else ""


def extraire_texte(nom, contenu):
    """Transforme le contenu brut d'un fichier (bytes) en texte."""
    extension = _extension(nom)
    if extension not in EXTENSIONS:
        raise DocumentInvalide(
            f"Type de fichier non pris en charge ({extension or 'sans extension'})."
        )
    if len(contenu) > TAILLE_MAX:
        raise DocumentInvalide("Fichier trop volumineux (10 Mo maximum).")

    if extension == ".pdf":
        try:
            lecteur = PdfReader(io.BytesIO(contenu))
            pages = [page.extract_text() or "" for page in lecteur.pages]
        except Exception as erreur:  # un PDF abîmé peut lever toutes sortes d'erreurs
            raise DocumentInvalide("Impossible de lire ce PDF.") from erreur
        texte = "\n".join(pages)
    else:
        # errors="replace" : un caractère illisible devient « � » au lieu de planter.
        texte = contenu.decode("utf-8", errors="replace")

    if not texte.strip():
        raise DocumentInvalide(
            "Aucun texte trouvé (un PDF scanné en image ne contient pas de texte)."
        )
    return texte


def importer(nom, contenu):
    """Importe un fichier et renvoie ses informations."""
    texte = extraire_texte(nom, contenu)
    # Nom de fichier aléatoire : on n'utilise jamais le nom fourni pour écrire
    # sur le disque (protection contre les noms piégés comme « ../../x »).
    fichier = f"{uuid.uuid4().hex}.txt"
    (dossier_documents() / fichier).write_text(texte, encoding="utf-8")

    with closing(memoire.connexion()) as con, con:
        curseur = con.execute(
            "INSERT INTO documents (nom, fichier_texte, nb_caracteres, date) VALUES (?, ?, ?, ?)",
            (nom, fichier, len(texte), datetime.now().isoformat(timespec="seconds")),
        )
    return {"id": curseur.lastrowid, "nom": nom, "nb_caracteres": len(texte)}


def lister():
    with closing(memoire.connexion()) as con:
        lignes = con.execute(
            "SELECT id, nom, nb_caracteres, date FROM documents ORDER BY id DESC"
        ).fetchall()
    return [dict(l) for l in lignes]


def supprimer(document_id):
    """Supprime un document (fiche + texte extrait). Renvoie False s'il n'existe pas."""
    with closing(memoire.connexion()) as con, con:
        ligne = con.execute(
            "SELECT fichier_texte FROM documents WHERE id = ?", (document_id,)
        ).fetchone()
        if ligne is None:
            return False
        con.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    (dossier_documents() / ligne["fichier_texte"]).unlink(missing_ok=True)
    return True


def _mots(texte):
    """Découpe un texte en mots simplifiés (minuscules, sans accents)."""
    sans_accents = unicodedata.normalize("NFD", texte.lower())
    sans_accents = "".join(c for c in sans_accents if unicodedata.category(c) != "Mn")
    return [
        mot for mot in re.findall(r"[a-z0-9_]+", sans_accents)
        if len(mot) > 2 and mot not in MOTS_VIDES
    ]


def _passages(texte):
    """Découpe un texte en passages d'environ TAILLE_PASSAGE caractères."""
    return [
        texte[i:i + TAILLE_PASSAGE]
        for i in range(0, len(texte), TAILLE_PASSAGE)
    ]


def rechercher(question, nb=NB_PASSAGES):
    """Renvoie les passages des documents les plus proches de la question.

    Score d'un passage = nombre de mots de la question qu'il contient.
    """
    mots_question = set(_mots(question))
    if not mots_question:
        return []

    with closing(memoire.connexion()) as con:
        documents = con.execute("SELECT nom, fichier_texte FROM documents").fetchall()

    candidats = []
    for document in documents:
        chemin = dossier_documents() / document["fichier_texte"]
        if not chemin.exists():
            continue
        for passage in _passages(chemin.read_text(encoding="utf-8")):
            score = len(mots_question & set(_mots(passage)))
            if score > 0:
                candidats.append((score, document["nom"], passage))

    candidats.sort(key=lambda c: c[0], reverse=True)
    return [{"document": nom, "passage": passage} for _, nom, passage in candidats[:nb]]


def contexte_pour_professeur(question):
    """Texte à joindre à la question : les passages trouvés, bien étiquetés."""
    passages = rechercher(question)
    if not passages:
        return ""
    lignes = [
        "EXTRAITS DES DOCUMENTS DE COURS DE L'ÉLÈVE (importés par lui) :",
        "Distingue clairement ce qui vient de ces extraits et ce que tu ajoutes. "
        "N'attribue jamais à son cours une information absente de ces extraits.",
    ]
    for p in passages:
        lignes.append(f"--- Extrait de « {p['document']} » ---\n{p['passage']}")
    return "\n".join(lignes)
