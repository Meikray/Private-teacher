# Private-teacher

**Assistant Professeur Personnel** : un professeur particulier d'informatique,
de programmation et d'IoT, **gratuit** : l'IA tourne sur ton ordinateur grâce à
[Ollama](https://ollama.com). Tu peux aussi utiliser Claude (payant, plus
performant) si tu le souhaites.

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
- **Accéder à Internet** (interrupteur 🌐 Internet) : le professeur peut ouvrir
  les liens que tu lui donnes (cours, documentation, PDF) et chercher sur
  Wikipédia, puis cite ses sources.

---

## 1. Ce qu'il te faut

- **Python 3.10 ou plus récent** (vérifie avec `python --version`).
- **Git**, pour récupérer le projet.
- **Ollama**, l'IA gratuite qui tourne sur ton ordinateur :
  - Windows / Mac : télécharge-le sur [ollama.com/download](https://ollama.com/download) ;
  - Linux : `curl -fsSL https://ollama.com/install.sh | sh`.
- Un ordinateur avec **8 Go de mémoire vive** au moins (le modèle conseillé,
  `qwen2.5:7b`, pèse environ 4,7 Go ; pour un PC modeste, voir la section 6).

Aucun compte ni aucune clé API n'est nécessaire en mode gratuit.

---

## 2. Le plus simple : le lanceur en un double-clic

Après avoir récupéré le projet (étape 1 ci-dessous) :

- **Windows** : double-clique sur **`lancer_windows.bat`**.
- **Mac / Linux** : dans un terminal, tape `./lancer_mac_linux.sh`.

Le lanceur fait tout seul : il crée l'environnement virtuel, installe les
bibliothèques, démarre Ollama, télécharge le modèle d'IA (la première fois
seulement, plusieurs Go : sois patient), démarre le serveur et ouvre ton
navigateur sur http://127.0.0.1:8000. Pour arrêter : ferme la fenêtre (ou
`Ctrl + C`).

Les étapes ci-dessous détaillent ce que fait le lanceur, si tu préfères tout
faire à la main.

## 2 bis. Installation à la main

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

### Étape 4 — Configurer et télécharger le modèle d'IA

| Windows | Mac / Linux |
|---|---|
| `copy .env.example .env` | `cp .env.example .env` |

Puis télécharge le modèle d'IA gratuit (une seule fois) :

```
ollama pull qwen2.5:7b
```

Si tu utilises Claude à la place (payant), mets `FOURNISSEUR=anthropic` dans
`.env` et remplace `mets-ta-cle-ici` par ta clé API.

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
| Le professeur est **très lent** | Normal sans carte graphique. Essaie le modèle léger : `MODELE_OLLAMA=qwen2.5:3b` dans `.env`, puis relance. Désactive 🌐 Internet si tu n'en as pas besoin. |
| « pas assez de mémoire » / le PC rame | Ferme les autres applications, ou passe à `qwen2.5:3b`. |
| « L'IA locale ne répond pas » | Ollama est lancé (application ouverte, ou `ollama serve`). |
| « Le modèle … n'est pas installé » | Tape la commande `ollama pull …` indiquée. |
| « Clé API manquante ou invalide » (Claude) | Le fichier `.env` contient la bonne clé. |
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

**En mode gratuit (Ollama), tes conversations ne quittent pas ton
ordinateur** : l'IA tourne chez toi. Seule exception : quand l'interrupteur
🌐 Internet est activé, les sites que le professeur consulte (et Wikipédia)
reçoivent ses demandes de pages. Pour la protection de ton PC, il ne peut lire
que des sites publics (jamais ton ordinateur ni ton réseau local).

Si tu choisis Claude, ce qui est envoyé à Anthropic pour qu'il te réponde : la
conversation en cours, un résumé de ton profil pédagogique, et les passages de
tes documents liés à ta question.

---

## 6. Coût et choix de l'IA

Deux possibilités, à choisir dans le fichier `.env` (ligne `FOURNISSEUR=`) :

| | `FOURNISSEUR=ollama` (par défaut) | `FOURNISSEUR=anthropic` |
|---|---|---|
| Prix | **Gratuit** | Payant : environ 3 à 6 centimes par échange |
| Compte / clé | Aucun | Clé API sur [console.anthropic.com](https://console.anthropic.com) |
| Vie privée | Tout reste sur ton ordinateur | Conversation envoyée à Anthropic |
| Qualité | Correcte (dépend du modèle et de ton PC) | Excellente (Claude Opus 5.5) |
| Accès à Internet (🌐) | Gratuit : lecture de liens et recherche Wikipédia | Recherche web, facturée en plus |
| Connexion | Seulement pour le modèle et l'option 🌐 | Nécessaire |

**Choisir le modèle gratuit** (ligne `MODELE_OLLAMA=` dans `.env`) :

- `qwen2.5:7b` : conseillé (environ 4,7 Go, 8 Go de mémoire vive) ;
- `qwen2.5:3b` : pour un PC modeste (environ 2 Go), moins précis ;
- `qwen2.5:14b` : meilleur, pour un PC puissant (environ 9 Go, 16 Go de mémoire).

Après avoir changé de modèle, relance simplement le lanceur : il le télécharge.

Avec un modèle local, le professeur est plus lent et un peu moins fin que
Claude ; l'enregistrement automatique de ta progression peut aussi être moins
régulier (tu peux toujours corriger ta mémoire dans l'onglet « Ma mémoire »).
