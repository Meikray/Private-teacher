"""Réglages communs à tous les tests (pytest lit ce fichier automatiquement).

La « fixture » ci-dessous s'exécute avant CHAQUE test : elle donne au test
une base de données neuve dans un dossier temporaire. Ainsi, les tests ne
touchent jamais à la vraie mémoire de l'élève (data/professeur.db).
"""

import pytest


@pytest.fixture(autouse=True)
def base_temporaire(tmp_path, monkeypatch):
    # tmp_path : dossier temporaire fourni par pytest, effacé ensuite.
    monkeypatch.setenv("PROFESSEUR_DB", str(tmp_path / "test.db"))
