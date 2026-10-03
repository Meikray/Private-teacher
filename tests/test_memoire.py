"""Tests de la mémoire pédagogique (app/memoire.py).

Chaque test travaille sur une base jetable (voir tests/conftest.py).
"""

from datetime import date, timedelta

from app import memoire


def etat_de(concept_id):
    return {c["id"]: c for c in memoire.lister_concepts()}[concept_id]


def test_un_concept_neuf_est_non_rencontre():
    concept = etat_de("pointeurs")
    assert concept["etat"] == 0
    assert concept["nom_etat"] == "Non rencontré"


def test_mettre_a_jour_et_planifier_la_revision():
    assert memoire.mettre_a_jour_concept("boucle", 3, "comprend for")
    concept = etat_de("boucle")
    assert concept["etat"] == 3
    assert concept["remarque"] == "comprend for"
    # État 3 -> révision dans 3 jours.
    assert concept["prochaine_revision"] == (date.today() + timedelta(days=3)).isoformat()


def test_refuse_un_concept_ou_un_etat_inconnu():
    assert not memoire.mettre_a_jour_concept("concept_qui_n_existe_pas", 2)
    assert not memoire.mettre_a_jour_concept("boucle", 9)


def test_oublier_un_concept():
    memoire.mettre_a_jour_concept("boucle", 4)
    memoire.oublier_concept("boucle")
    assert etat_de("boucle")["etat"] == 0


def test_revisions_a_faire():
    memoire.mettre_a_jour_concept("variable", 2)  # révision demain
    assert memoire.revisions_a_faire() == []
    demain = date.today() + timedelta(days=1)
    assert [c["id"] for c in memoire.revisions_a_faire(demain)] == ["variable"]


def test_erreurs():
    memoire.ajouter_erreur("pointeurs", "confond * et &")
    erreurs = memoire.lister_erreurs()
    assert erreurs[0]["description"] == "confond * et &"
    assert erreurs[0]["nom_concept"] == "Pointeurs"
    memoire.supprimer_erreur(erreurs[0]["id"])
    assert memoire.lister_erreurs() == []


def test_niveau_assistance_monte_avec_l_autonomie():
    assert memoire.niveau_assistance()["palier"] == 0
    # Trop peu d'observations : on ne réduit pas encore l'aide.
    for _ in range(2):
        memoire.enregistrer_aide(0, False, "reussi_sans_aide")
    assert memoire.niveau_assistance()["palier"] == 0
    for _ in range(3):
        memoire.enregistrer_aide(0, False, "reussi_sans_aide")
    assert memoire.niveau_assistance()["palier"] == 3


def test_detecte_les_demandes_de_solution():
    for _ in range(4):
        memoire.enregistrer_aide(6, True, "aucun")
    assert memoire.niveau_assistance()["part_demandes_solution"] == 1.0
    assert "demande souvent la solution" in memoire.resume_pour_professeur()


def test_profil_n_accepte_que_les_cles_connues():
    memoire.modifier_profil({"objectifs": "réussir l'IoT", "pirate": "x"})
    profil = memoire.lire_profil()
    assert profil["objectifs"] == "réussir l'IoT"
    assert "pirate" not in profil


def test_appliquer_progression():
    resultat = memoire.appliquer_progression({
        "concepts": [
            {"id": "gpio", "etat": 2, "remarque": ""},
            {"id": "inconnu", "etat": 2, "remarque": ""},
        ],
        "erreurs": [{"concept": "gpio", "description": "oublie pinMode"}],
        "niveau_aide": 3,
        "exercice": "reussi_avec_aide",
        "demande_solution_directe": False,
    })
    assert resultat == {"mis_a_jour": ["gpio"], "ignores": ["inconnu"]}
    assert memoire.tableau_de_bord()["nb_exercices"] == 1


def test_tableau_de_bord_et_reinitialisation():
    memoire.mettre_a_jour_concept("gpio", 5)
    memoire.enregistrer_activite("message")
    tableau = memoire.tableau_de_bord()
    assert tableau["repartition"]["Maîtrisé en pratique"] == 1
    assert tableau["nb_messages"] == 1
    assert [c["id"] for c in tableau["maitrises"]] == ["gpio"]

    memoire.reinitialiser()
    tableau = memoire.tableau_de_bord()
    assert tableau["nb_messages"] == 0
    assert tableau["maitrises"] == []
