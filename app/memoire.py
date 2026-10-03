"""Mémoire pédagogique locale (SQLite).

Ce module garde le profil de l'élève SUR SA MACHINE (sections 20 à 23, 31) :
- l'état de maîtrise de chaque concept (7 états, voir app/parcours.py) ;
- les erreurs fréquentes ;
- les niveaux d'aide utilisés (pour détecter la dépendance à l'IA) ;
- l'activité (messages, exercices) pour le tableau de bord ;
- le profil (objectifs, langage étudié...).

La mémoire reste contrôlable par l'élève : voir, corriger, supprimer,
réinitialiser (fonctions plus bas, exposées par app/main.py).

Le fichier de base de données est data/professeur.db (ignoré par Git).
On peut changer son emplacement avec la variable d'environnement
PROFESSEUR_DB (les tests l'utilisent pour travailler sur une base jetable).
"""

import os
import sqlite3
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

from app.parcours import CONCEPTS, CONCEPTS_PAR_ID, ETATS, nom_etat

RACINE = Path(__file__).parent.parent
CHEMIN_PAR_DEFAUT = RACINE / "data" / "professeur.db"

# Révision espacée (section 22) : nombre de jours avant la prochaine
# révision selon l'état atteint. Plus un concept est maîtrisé, plus on
# attend avant de le revoir. Les états 0 et 1 ne sont pas planifiés.
INTERVALLES_REVISION = {2: 1, 3: 3, 4: 7, 5: 14, 6: 30}

# Clés autorisées dans le profil (on refuse le reste).
CLES_PROFIL = ("objectifs", "langage_etudie", "niveau_estime", "cours_actuels")

SCHEMA = """
CREATE TABLE IF NOT EXISTS concepts (
    id TEXT PRIMARY KEY,
    etat INTEGER NOT NULL,
    remarque TEXT NOT NULL DEFAULT '',
    mis_a_jour TEXT NOT NULL,
    prochaine_revision TEXT
);
CREATE TABLE IF NOT EXISTS erreurs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    concept TEXT NOT NULL,
    description TEXT NOT NULL,
    date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS aides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    niveau INTEGER NOT NULL,
    demande_solution INTEGER NOT NULL,
    exercice TEXT NOT NULL,
    date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS activite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    date TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS profil (
    cle TEXT PRIMARY KEY,
    valeur TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nom TEXT NOT NULL,
    fichier_texte TEXT NOT NULL,
    nb_caracteres INTEGER NOT NULL,
    date TEXT NOT NULL
);
"""


def chemin_base():
    """Emplacement du fichier SQLite (modifiable par PROFESSEUR_DB)."""
    return Path(os.environ.get("PROFESSEUR_DB", CHEMIN_PAR_DEFAUT))


def connexion():
    """Ouvre la base (et la crée au premier appel).

    row_factory = sqlite3.Row permet de lire les colonnes par leur nom :
    ligne["etat"] au lieu de ligne[1].
    """
    chemin = chemin_base()
    chemin.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(chemin)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def _maintenant():
    return datetime.now().isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Concepts
# ---------------------------------------------------------------------------


def lister_concepts():
    """Tous les concepts du parcours, avec leur état actuel.

    Un concept jamais rencontré n'a pas de ligne en base : il est à l'état 0.
    """
    with closing(connexion()) as con:
        lignes = {l["id"]: l for l in con.execute("SELECT * FROM concepts")}

    resultat = []
    for concept in CONCEPTS:
        ligne = lignes.get(concept["id"])
        etat = ligne["etat"] if ligne else 0
        resultat.append({
            **concept,
            "etat": etat,
            "nom_etat": nom_etat(etat),
            "remarque": ligne["remarque"] if ligne else "",
            "mis_a_jour": ligne["mis_a_jour"] if ligne else None,
            "prochaine_revision": ligne["prochaine_revision"] if ligne else None,
        })
    return resultat


def mettre_a_jour_concept(concept_id, etat, remarque=""):
    """Enregistre le nouvel état d'un concept et planifie sa révision.

    Renvoie False si le concept ou l'état est inconnu (rien n'est enregistré).
    """
    if concept_id not in CONCEPTS_PAR_ID or not 0 <= etat < len(ETATS):
        return False

    jours = INTERVALLES_REVISION.get(etat)
    revision = (date.today() + timedelta(days=jours)).isoformat() if jours else None

    with closing(connexion()) as con, con:
        # « INSERT ... ON CONFLICT » : crée la ligne ou la met à jour.
        con.execute(
            """INSERT INTO concepts (id, etat, remarque, mis_a_jour, prochaine_revision)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 etat = excluded.etat,
                 remarque = excluded.remarque,
                 mis_a_jour = excluded.mis_a_jour,
                 prochaine_revision = excluded.prochaine_revision""",
            (concept_id, etat, remarque, _maintenant(), revision),
        )
    return True


def oublier_concept(concept_id):
    """Supprime ce que la mémoire sait d'un concept (il redevient « Non rencontré »)."""
    with closing(connexion()) as con, con:
        con.execute("DELETE FROM concepts WHERE id = ?", (concept_id,))


def revisions_a_faire(jour=None):
    """Concepts dont la date de révision est arrivée (section 22)."""
    jour = (jour or date.today()).isoformat()
    return [
        c for c in lister_concepts()
        if c["prochaine_revision"] and c["prochaine_revision"] <= jour
    ]


# ---------------------------------------------------------------------------
# Erreurs fréquentes
# ---------------------------------------------------------------------------


def ajouter_erreur(concept, description):
    with closing(connexion()) as con, con:
        con.execute(
            "INSERT INTO erreurs (concept, description, date) VALUES (?, ?, ?)",
            (concept, description, _maintenant()),
        )


def lister_erreurs(limite=50):
    with closing(connexion()) as con:
        lignes = con.execute(
            "SELECT * FROM erreurs ORDER BY id DESC LIMIT ?", (limite,)
        ).fetchall()
    return [dict(l) for l in lignes]


def supprimer_erreur(erreur_id):
    with closing(connexion()) as con, con:
        con.execute("DELETE FROM erreurs WHERE id = ?", (erreur_id,))


# ---------------------------------------------------------------------------
# Aides et dépendance à l'IA (section 23)
# ---------------------------------------------------------------------------


def enregistrer_aide(niveau, demande_solution, exercice):
    """niveau : 0 (aucune aide) à 6 (solution complète)."""
    with closing(connexion()) as con, con:
        con.execute(
            "INSERT INTO aides (niveau, demande_solution, exercice, date) VALUES (?, ?, ?, ?)",
            (niveau, int(demande_solution), exercice, _maintenant()),
        )


def niveau_assistance():
    """Calcule le niveau d'assistance à proposer, d'après les 10 dernières aides.

    Renvoie un dictionnaire : palier (0 à 3), nom du palier, explication, et
    la part de demandes de solution directe. L'idée (section 23) : plus
    l'élève réussit avec peu d'aide, moins le professeur en donne.
    """
    with closing(connexion()) as con:
        lignes = con.execute(
            "SELECT * FROM aides ORDER BY id DESC LIMIT 10"
        ).fetchall()

    paliers = [
        ("Début", "explication + exemple + indice"),
        ("Progression", "question de réflexion + indice"),
        ("Niveau supérieur", "question de réflexion uniquement"),
        ("Autonomie", "problème complet sans aide"),
    ]

    if not lignes:
        palier = 0
        part_solution = 0.0
    else:
        moyenne = sum(l["niveau"] for l in lignes) / len(lignes)
        reussites = sum(1 for l in lignes if l["exercice"] == "reussi_sans_aide")
        part_solution = sum(l["demande_solution"] for l in lignes) / len(lignes)
        # Moins l'élève a besoin d'aide, plus le palier monte.
        if moyenne <= 1 and reussites >= 3:
            palier = 3
        elif moyenne <= 2:
            palier = 2
        elif moyenne <= 3.5:
            palier = 1
        else:
            palier = 0

    nom, explication = paliers[palier]
    return {
        "palier": palier,
        "nom": nom,
        "explication": explication,
        "part_demandes_solution": round(part_solution, 2),
    }


# ---------------------------------------------------------------------------
# Activité, profil, statistiques
# ---------------------------------------------------------------------------


def enregistrer_activite(type_activite):
    """type_activite : par exemple "message" ou "exercice"."""
    with closing(connexion()) as con, con:
        con.execute(
            "INSERT INTO activite (type, date) VALUES (?, ?)",
            (type_activite, _maintenant()),
        )


def lire_profil():
    with closing(connexion()) as con:
        lignes = con.execute("SELECT * FROM profil").fetchall()
    profil = {cle: "" for cle in CLES_PROFIL}
    profil.update({l["cle"]: l["valeur"] for l in lignes})
    return profil


def modifier_profil(valeurs):
    """Met à jour le profil. Les clés inconnues sont ignorées."""
    with closing(connexion()) as con, con:
        for cle, valeur in valeurs.items():
            if cle in CLES_PROFIL:
                con.execute(
                    """INSERT INTO profil (cle, valeur) VALUES (?, ?)
                       ON CONFLICT(cle) DO UPDATE SET valeur = excluded.valeur""",
                    (cle, valeur),
                )


def tableau_de_bord():
    """Toutes les informations du tableau de bord (section 31)."""
    concepts = lister_concepts()
    with closing(connexion()) as con:
        nb_messages = con.execute(
            "SELECT COUNT(*) FROM activite WHERE type = 'message'"
        ).fetchone()[0]
        nb_exercices = con.execute(
            "SELECT COUNT(*) FROM aides WHERE exercice != 'aucun'"
        ).fetchone()[0]
        nb_reussis_seul = con.execute(
            "SELECT COUNT(*) FROM aides WHERE exercice = 'reussi_sans_aide'"
        ).fetchone()[0]
        jours_actifs = con.execute(
            "SELECT COUNT(DISTINCT substr(date, 1, 10)) FROM activite"
        ).fetchone()[0]

    repartition = {nom: 0 for nom in ETATS}
    for c in concepts:
        repartition[c["nom_etat"]] += 1

    return {
        "repartition": repartition,
        "maitrises": [c for c in concepts if c["etat"] >= 4],
        "fragiles": [c for c in concepts if c["etat"] in (1, 2)],
        "revisions": revisions_a_faire(),
        "erreurs_recentes": lister_erreurs(limite=10),
        "nb_messages": nb_messages,
        "nb_exercices": nb_exercices,
        "nb_reussis_seul": nb_reussis_seul,
        "jours_actifs": jours_actifs,
        "assistance": niveau_assistance(),
        "profil": lire_profil(),
    }


def resume_pour_professeur():
    """Texte court décrivant l'élève, envoyé au professeur avec chaque question.

    Il permet d'adapter les explications sans tout renvoyer : seulement les
    concepts déjà rencontrés, les erreurs récentes et le niveau d'assistance.
    """
    concepts = [c for c in lister_concepts() if c["etat"] > 0]
    profil = lire_profil()
    assistance = niveau_assistance()
    revisions = revisions_a_faire()
    erreurs = lister_erreurs(limite=5)

    lignes = ["PROFIL PÉDAGOGIQUE DE L'ÉLÈVE (mémoire locale) :"]
    for cle, valeur in profil.items():
        if valeur:
            lignes.append(f"- {cle} : {valeur}")
    if concepts:
        lignes.append("- Concepts rencontrés : " + "; ".join(
            f"{c['nom']} ({c['nom_etat']})" for c in concepts
        ))
    else:
        lignes.append("- Aucun concept enregistré pour l'instant (première utilisation probable).")
    if erreurs:
        lignes.append("- Erreurs récentes : " + "; ".join(
            f"{e['concept']} : {e['description']}" for e in erreurs
        ))
    if revisions:
        lignes.append("- Révisions dues : " + ", ".join(c["nom"] for c in revisions))
    lignes.append(
        f"- Niveau d'assistance recommandé : {assistance['nom']} "
        f"({assistance['explication']})."
    )
    if assistance["part_demandes_solution"] >= 0.5:
        lignes.append(
            "- Attention : l'élève demande souvent la solution directement. "
            "Réduis progressivement l'assistance et encourage-le à essayer."
        )
    return "\n".join(lignes)


def appliquer_progression(entree):
    """Enregistre ce que le professeur a observé (appel de l'outil de progression).

    entree : dictionnaire envoyé par Claude, de la forme
        {"concepts": [{"id", "etat", "remarque"}], "erreurs": [{"concept", "description"}],
         "niveau_aide": 0-6, "exercice": "...", "demande_solution_directe": bool}
    Renvoie les identifiants des concepts mis à jour et ceux qui ont été ignorés.
    """
    mis_a_jour, ignores = [], []
    for concept in entree.get("concepts", []):
        if mettre_a_jour_concept(concept["id"], concept["etat"], concept.get("remarque", "")):
            mis_a_jour.append(concept["id"])
        else:
            ignores.append(concept["id"])
    for erreur in entree.get("erreurs", []):
        ajouter_erreur(erreur["concept"], erreur["description"])
    enregistrer_aide(
        entree.get("niveau_aide", 0),
        entree.get("demande_solution_directe", False),
        entree.get("exercice", "aucun"),
    )
    return {"mis_a_jour": mis_a_jour, "ignores": ignores}


def reinitialiser():
    """Efface toute la mémoire pédagogique (section 20 : « réinitialiser mon profil »).

    Les documents importés ne sont pas effacés ici (voir app/documents.py).
    """
    with closing(connexion()) as con, con:
        for table in ("concepts", "erreurs", "aides", "activite", "profil"):
            con.execute(f"DELETE FROM {table}")
