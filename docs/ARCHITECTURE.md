# Architecture de l'Assistant Professeur Personnel

Ce document est la « carte » du projet. Il explique à quoi sert chaque partie
de l'application, pourquoi chaque technologie a été choisie, et **comment
faire évoluer le projet**.

> Rappel : ce projet est aussi un outil d'apprentissage. Chaque partie doit
> rester lisible et compréhensible par un débutant (section 34 du cahier des charges).

---

## 1. Vue d'ensemble

L'application est découpée en modules indépendants. Chaque module a **une seule
responsabilité**. C'est ce qu'on appelle la *séparation des responsabilités* :
si un module change, les autres ne sont pas cassés.

### Serveur (Python, dossier `app/`)

| Fichier | Rôle |
|---|---|
| `main.py` | Les **routes** de l'API (les adresses comme `/chat`). Il ne fait que relier les modules. |
| `ia.py` | Le **seul** fichier qui parle à une IA : Ollama (gratuit, local, par défaut) ou Claude (payant), boucle d'outils. |
| `consignes.py` | Les consignes générales du professeur (le « prompt système »). |
| `modes.py` | Le **registre des modes** : socratique, cours, explication de code, débogage, exercice, examen, diagnostic, révision, projet, plan d'étude. |
| `parcours.py` | La **carte des connaissances** : domaines, concepts, prérequis, 7 états de maîtrise. |
| `memoire.py` | La **mémoire pédagogique** locale (SQLite) : états, erreurs, aides, révisions, profil, tableau de bord. |
| `documents.py` | Les **documents de cours** : import (PDF, texte, code), extraction du texte, recherche de passages. |
| `internet.py` | L'**accès à Internet** de l'IA locale : lire une page ou un PDF, chercher sur Wikipédia, avec protections (sites publics uniquement, tailles limitées). |

### Interface (navigateur, dossier `static/`)

| Fichier | Rôle |
|---|---|
| `index.html` / `style.css` | Structure et apparence (thème sombre et clair automatiques). |
| `js/main.js` | Point d'entrée : démarre chaque partie. |
| `js/chat.js` | La discussion : historique, choix du mode, affichage des réponses. |
| `js/carte.js` | La carte des connaissances : fiche d'un concept, légende, version en liste de secours. |
| `js/carte3d.js` | La **scène 3D** (Three.js) : îlots, sphères, liens de prérequis. |
| `js/panneaux.js` | Tableau de bord, Ma mémoire, Documents, Réglages. |
| `js/voix.js` | Dictée au micro et lecture vocale. |
| `js/markdown.js` | Mise en forme sûre des réponses (protection XSS). |
| `js/api.js` | Requêtes vers le serveur et « bus d'événements » entre modules. |
| `js/reglages.js` | Réglages gardés dans le navigateur. |
| `vendor/three/` | La bibliothèque 3D Three.js 0.160.0 (licence MIT), incluse pour fonctionner hors ligne. |

---

## 2. Trajet d'une question

```
  Toi : « Pourquoi ma boucle ne s'arrête pas ? »
   │
   ▼
┌──────────────────────┐   historique + mode + réglages (JSON)
│ Interface (chat.js)  │ ─────────────────────────────────────┐
└──────────────────────┘                                      ▼
                                                   ┌────────────────────┐
                                                   │ Serveur (main.py)  │
                                                   └─────────┬──────────┘
            ┌────────────────────────────┬──────────────────┤
            ▼                            ▼                  ▼
   consigne du mode (modes.py)   profil (memoire.py)   extraits de cours
                                                       (documents.py)
            └────────────────────────────┴──────────────────┘
                                         │ contexte
                                         ▼
                              ┌─────────────────────┐
                              │  Module IA (ia.py)  │ ──► API Claude
                              └─────────┬───────────┘ ◄── réponse
                                        │
              Claude appelle l'outil « enregistrer_progression »
                                        │
                                        ▼
                              mémoire mise à jour (SQLite)
                                        │
                                        ▼
   Interface : réponse affichée + carte 3D et tableau de bord rafraîchis
```

Points importants :

- L'IA ne décide pas seule de son comportement : les **consignes** et le
  **mode** lui disent comment répondre (par exemple « donne seulement un indice »).
- La page garde l'**historique** et l'envoie en entier, car l'API Claude ne
  retient rien entre deux messages.
- La **mémoire** est mise à jour par Claude lui-même, grâce à un **outil**
  (`enregistrer_progression`) : quand il observe que tu as compris ou que tu
  bloques, il l'enregistre.

---

## 3. Pourquoi ces choix ?

### Python + FastAPI pour le serveur
- **Choisi parce que :** lisible pour un débutant, très utilisé en IA, et
  FastAPI vérifie automatiquement la forme des données reçues.
- **Alternatives :** Node.js (un seul langage, mais l'asynchronisme est plus
  déroutant), Flask (plus ancien), Django (plus lourd).

### HTML / CSS / JavaScript (sans framework) pour l'interface
- **Choisi parce que :** on voit clairement comment le frontend et le backend
  communiquent (section 52), sans couche cachée.
- **Alternatives :** React ou Vue (puissants, mais beaucoup de notions en plus
  pour un débutant), Streamlit (cache le fonctionnement du web).

### Three.js pour la 3D
- **Choisi parce que :** c'est la bibliothèque 3D la plus utilisée et la mieux
  documentée pour le navigateur (WebGL).
- **Copiée dans le projet** (`static/vendor/three`) plutôt que chargée depuis
  Internet : l'application fonctionne hors ligne et ne contacte aucun serveur
  extérieur.

### Ollama (gratuit) ou Claude (payant) pour le professeur
- **Ollama par défaut**, pour que l'application soit **accessible sans payer** :
  un modèle ouvert (`qwen2.5:7b`) tourne sur l'ordinateur de l'élève, via
  l'API HTTP locale d'Ollama (`/api/chat`), avec le même outil de progression.
  Avantages : gratuit, sans compte, rien ne quitte la machine. Limites :
  moins fin que Claude, demande un PC correct (8 Go de mémoire vive).
- **Claude Opus 5.5 en option** (`FOURNISSEUR=anthropic`) pour la meilleure
  qualité pédagogique : effort `medium`, option de secours `fallbacks="default"`,
  recherche web possible.
- Les deux sont isolés dans `ia.py` : le reste de l'application ne sait pas
  quelle IA répond.

### SQLite pour la mémoire
- **Choisi parce que :** une base de données dans un simple fichier, rien à
  installer, et tes données restent **sur ta machine** (section 20).

### Recherche par mots-clés pour les documents
- **Choisie parce que :** simple à comprendre, aucun service extérieur.
- **Évolution possible :** une recherche « sémantique » (par le sens), en
  remplaçant uniquement la fonction `rechercher()` de `documents.py`.

---

## 4. Sécurité et vie privée (section 33)

- La clé API est dans `.env`, **jamais** dans le code ni sur GitHub (`.gitignore`).
- Toutes tes données personnelles restent sur ton ordinateur, dans `data/`
  (ignoré par Git) : mémoire (`professeur.db`) et documents.
- En mode gratuit (Ollama), **les conversations ne quittent pas l'ordinateur**.
  Avec l'interrupteur 🌐 Internet, l'IA peut lire des pages publiques :
  `internet.py` refuse les protocoles autres que http(s) et toute adresse
  locale ou privée (y compris après une redirection), limite la taille
  téléchargée (3 Mo) et le texte transmis au modèle.
- Avec Claude, ce qui est envoyé à Anthropic : la conversation, ton profil
  pédagogique résumé, et les passages de tes documents liés à ta question.
  C'est signalé dans l'onglet Documents.
- La **dictée** au micro est désactivée par défaut : dans Chrome/Edge, l'audio
  est transcrit par le service du navigateur. C'est signalé dans les Réglages.
- La **recherche web** est désactivée par défaut (coût supplémentaire).
- Le serveur n'écoute que ton ordinateur (`127.0.0.1`).
- Les réponses de Claude sont affichées sans pouvoir injecter de HTML
  (`markdown.js` échappe tout le texte avant de le mettre en forme).
- Les rôles des messages sont limités à `user` / `assistant` : la page ne peut
  pas modifier les consignes du professeur.
- Les fichiers importés sont limités (10 Mo, extensions connues) et enregistrés
  sous un nom aléatoire.
- Aucun code n'est exécuté automatiquement.

---

## 5. Faire évoluer le projet

Le projet est conçu pour grandir **sans tout réécrire**. Voici où agir :

| Je veux… | Fichier à modifier |
|---|---|
| Ajouter un concept ou un domaine (il apparaît dans la carte 3D) | `app/parcours.py` (les tests vérifient prérequis et boucles) |
| Ajouter un mode du professeur (il apparaît dans la liste) | `app/modes.py` |
| Changer le comportement général du professeur | `app/consignes.py` |
| Changer d'IA (gratuite / Claude) ou de modèle local | `.env` (`FOURNISSEUR`, `MODELE_OLLAMA`) |
| Changer de modèle Claude ou d'effort | `app/ia.py` (`MODELE`, `EFFORT`) |
| Ajouter un autre fournisseur d'IA | `app/ia.py` (une fonction `_demander_a_…`, appelée par `demander_au_professeur`) |
| Donner un nouvel outil à Claude | `app/ia.py` (définition) + `app/main.py` (`executer_outil`) |
| Améliorer la recherche dans les documents | `app/documents.py` (`rechercher`) |
| Ajouter une information au tableau de bord | `app/memoire.py` (`tableau_de_bord`) + `static/js/panneaux.js` |
| Modifier l'apparence 3D | `static/js/carte3d.js` |
| Ajouter un panneau | `static/index.html` (onglet) + `static/js/panneaux.js` |
| Ajouter un connecteur externe (GitHub, Drive…) | Nouveau module `app/connecteurs/…` appelé comme un outil depuis `ia.py` |

Les modules de l'interface communiquent par des **événements**
(`emettre` / `ecouter` dans `api.js`) : par exemple, la carte 3D émet
`demander` et la discussion l'écoute. On peut donc ajouter un module qui
réagit à `memoire-modifiee` sans toucher aux autres.

---

## 6. État d'avancement (section 41)

### Version de base (MVP) — terminée
- ✅ Chat pédagogique (page web + serveur + Claude)
- ✅ Mode socratique et niveaux d'aide 1 à 6
- ✅ Analyse de code (modes « Explique-moi ce code » et « Débogage »)
- ✅ Système d'indices et détection de la dépendance à l'IA (paliers d'assistance)
- ✅ Import de documents (PDF, texte, code) et recherche de passages
- ✅ Mémoire des connaissances (SQLite, 7 états), contrôlable par l'élève
- ✅ Suivi des progrès

### Ajouts — réalisés
- ✅ Évaluation diagnostique à la première visite
- ✅ Révision espacée (dates de révision selon l'état)
- ✅ Modes examen, cours complet, sujet d'exercice, projet guidé, plan d'étude
- ✅ Tableau de bord
- ✅ Carte 3D interactive des connaissances
- ✅ Recherche web (optionnelle) avec priorité aux sources officielles
- ✅ Voix (dictée et lecture, réglables)

### Pistes pour la suite
- Connecteurs externes (GitHub, Google Drive…) avec authentification adaptée.
- Recherche sémantique dans les documents.
- Historique des conversations sauvegardé localement.
- Temps d'étude mesuré par session.

---

## 7. Règle de contrôle (section 70)

Pendant la construction, l'agent de développement (Claude Code) a demandé la
permission avant chaque action, jusqu'à ce que l'élève lui donne explicitement
l'autorisation de terminer le projet en autonomie, avec une seule destination
de publication : le dépôt GitHub `Meikray/Private-teacher`.
