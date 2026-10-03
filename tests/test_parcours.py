"""Tests de cohérence du parcours pédagogique (app/parcours.py).

Ils protègent l'évolution du parcours : si on ajoute un concept avec une
faute de frappe dans un prérequis, ou une boucle de prérequis, ils échouent.
"""

from app.parcours import CONCEPTS, CONCEPTS_PAR_ID, DOMAINES, ETATS


def test_sept_etats():
    assert len(ETATS) == 7


def test_identifiants_uniques():
    ids = [c["id"] for c in CONCEPTS]
    assert len(ids) == len(set(ids))


def test_domaines_et_prerequis_existent():
    domaines = {d["id"] for d in DOMAINES}
    for concept in CONCEPTS:
        assert concept["domaine"] in domaines, concept["id"]
        for prerequis in concept["prerequis"]:
            assert prerequis in CONCEPTS_PAR_ID, f"{concept['id']} -> {prerequis}"


def test_pas_de_boucle_de_prerequis():
    # Parcours en profondeur : si on retombe sur un concept « en cours de
    # visite », c'est qu'il existe une boucle (A demande B qui demande A).
    en_cours, termines = set(), set()

    def visiter(concept_id):
        assert concept_id not in en_cours, f"boucle de prérequis via {concept_id}"
        if concept_id in termines:
            return
        en_cours.add(concept_id)
        for prerequis in CONCEPTS_PAR_ID[concept_id]["prerequis"]:
            visiter(prerequis)
        en_cours.remove(concept_id)
        termines.add(concept_id)

    for concept in CONCEPTS:
        visiter(concept["id"])
