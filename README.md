# Private-teacher

**Assistant Professeur Personnel** : un professeur particulier d'informatique,
de programmation et d'IoT, propulsé par Claude.

Son but n'est pas de faire les exercices à ta place, mais de te rendre
**autonome** : il pose des questions, donne des indices progressifs et vérifie
que tu as vraiment compris.

> Architecture détaillée et guide pour faire évoluer le projet :
> [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

### Ce que tu peux faire

- **Discuter avec le professeur**, qui te guide par questions et indices
  progressifs au lieu de te donner la solution.
- **Choisir un mode** : socratique (par défaut), cours complet, explique-moi ce
  code, débogage, sujet d'exercice, examen (aucune solution), évaluation
  diagnostique, révision, projet guidé, plan d'étude.
- **Explorer ta carte 3D des connaissances** : chaque sphère est une notion,
  colorée selon ton niveau de maîtrise (7 états, du gris au doré). Plus elle
  est haute, plus la notion est avancée. Clique dessus pour l'apprendre ou la
  réviser.
- **Suivre tes progrès** dans le tableau de bord : notions maîtrisées ou
  fragiles, révisions à faire, erreurs fréquentes, et ton palier d'autonomie.
- **Contrôler ta mémoire** : voir, corriger, oublier ou tout réinitialiser.
- **Importer tes cours** (PDF, texte, code) : le professeur s'appuie dessus et
  peut en faire des fiches de révision.
- **Parler et écouter** : dictée au micro et lecture vocale des réponses
  (voix, vitesse et langue réglables).

---

## 1. Ce qu'il te faut

- **Python 3.10 ou plus récent** (vérifie avec `python --version`).
- **Git**, pour récupérer le projet.
- **Une clé API Anthropic** : à créer sur ton compte, sur
  [console.anthropic.com](https://console.anthropic.com), rubrique « API Keys ».

---

## 2. Installation sur ton PC

Les commandes sont à taper dans un terminal (« Invite de commandes » ou
« PowerShell » sous Windows, « Terminal » sous Mac/Linux).

### Étape 1 — Récupérer le projet

```
git clone -b claude/instructions-document-46pgcg https://github.com/Meikray/Private-teacher.git
cd Private-teacher
```

- `git clone` télécharge une copie du projet depuis GitHub.
- `-b claude/instructions-document-46pgcg` choisit la branche où se trouve le travail.
- `cd Private-teacher` entre dans le dossier du projet.

### Étape 2 — Créer l'environnement virtuel

Un environnement virtuel est un dossier isolé (`.venv`) qui contient les
bibliothèques du projet, sans les mélanger avec le reste de ton ordinateur.

| Windows | Mac / Linux |
|---|---|
| `py -m venv .venv` | `python3 -m venv .venv` |
| `.venv\Scripts\activate` | `source .venv/bin/activate` |

La deuxième ligne **active** l'environnement : `(.venv)` apparaît alors au
début de la ligne du terminal. Il faut l'activer à chaque nouveau terminal.

### Étape 3 — Installer les bibliothèques

```
pip install -r requirements.txt
```

`pip` installe toutes les bibliothèques listées dans `requirements.txt`.

### Étape 4 — Mettre ta clé API

| Windows | Mac / Linux |
|---|---|
| `copy .env.example .env` | `cp .env.example .env` |

Ouvre ensuite le fichier `.env` avec un éditeur de texte et remplace
`mets-ta-cle-ici` par ta vraie clé.

> ⚠️ **Ne partage jamais ta clé**, avec personne (pas même dans une
> conversation avec une IA). Le fichier `.env` est déjà exclu de Git : il ne
> sera jamais envoyé sur GitHub.

---

## 3. Lancer l'application

Depuis le dossier du projet, avec l'environnement virtuel activé :

```
uvicorn app.main:app --reload
```

- `uvicorn` démarre le serveur.
- `app.main:app` signifie : dans le fichier `app/main.py`, utilise l'objet `app`.
- `--reload` redémarre automatiquement le serveur quand tu modifies le code.

Ouvre ensuite ton navigateur à l'adresse **http://127.0.0.1:8000**.
(Chrome ou Edge conseillés : ils permettent aussi la dictée au micro.)

Pour arrêter le serveur : `Ctrl + C` dans le terminal.

### En cas de problème

| Message affiché | Ce qu'il faut vérifier |
|---|---|
| « Clé API manquante ou invalide » | Le fichier `.env` existe et contient la bonne clé. |
| « Problème de configuration de Claude » | Le fichier `.env` est bien dans le dossier du projet. |
| « Impossible de joindre Claude » | Ta connexion Internet. |
| « Trop de demandes » | Attends quelques secondes avant de réessayer. |

---

## 4. Lancer les tests

```
pytest -v
```

Les tests utilisent un **faux Claude** et une base de données jetable : ils ne
coûtent rien, n'ont pas besoin de clé API et ne touchent pas à ta mémoire.

---

## 5. Tes données

Tout reste **sur ton ordinateur**, dans le dossier `data/` (jamais envoyé sur
GitHub) :

- `data/professeur.db` : ta mémoire pédagogique (concepts, erreurs, progrès) ;
- `data/documents/` : le texte de tes documents importés.

Ce qui est envoyé à Claude (Anthropic) pour qu'il te réponde : la conversation
en cours, un résumé de ton profil pédagogique, et les passages de tes
documents liés à ta question.

---

## 6. Coût

L'API Claude est **payante**. Le professeur utilise le modèle Claude Opus 5.5 :
compte environ **3 à 6 centimes de dollar par échange** (une question et sa
réponse, y compris l'enregistrement de ta progression). Le coût réel dépend de
la longueur des messages et des documents utilisés. Tu peux suivre ta
consommation sur [console.anthropic.com](https://console.anthropic.com).

La **recherche web** est désactivée par défaut (onglet Réglages) : quand elle
est activée, chaque recherche est facturée en plus.

Le modèle est défini à un seul endroit : la variable `MODELE` dans
[`app/ia.py`](app/ia.py).
