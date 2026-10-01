# Architecture de l'Assistant Professeur Personnel

Ce document est la « carte » du projet. Il explique à quoi sert chaque partie
de l'application, pourquoi chaque technologie a été choisie, et dans quel ordre
le projet sera construit.

> Rappel : ce projet est aussi un outil d'apprentissage. Chaque partie doit
> rester lisible et compréhensible par un débutant (section 34 du cahier des charges).

---

## 1. Vue d'ensemble

L'application est découpée en modules indépendants. Chaque module a **une seule
responsabilité**. C'est ce qu'on appelle la *séparation des responsabilités* :
si un module change, les autres ne sont pas cassés.

| Module | Rôle | Technologie |
|---|---|---|
| **Interface (frontend)** | Ce que tu vois : la fenêtre de discussion, les boutons, le tableau de bord. | HTML, CSS, JavaScript |
| **Serveur (backend)** | Reçoit les messages de l'interface, les transmet aux bons modules, renvoie les réponses. | Python + FastAPI |
| **Agent pédagogique** | Le « cerveau » du professeur : identifie ton intention, choisit le niveau d'aide (mode socratique), prépare les consignes envoyées à l'IA. | Python |
| **Module IA** | Envoie la demande au modèle d'IA et récupère sa réponse. Isolé pour pouvoir changer de fournisseur plus tard. | API Claude (Anthropic) |
| **Mémoire pédagogique** | Garde ton profil : concepts maîtrisés, fragiles, erreurs fréquentes, progression. | SQLite |
| **Documents / RAG** *(plus tard)* | Recherche dans tes cours, PDF et notes. | Python |
| **Voix** *(plus tard)* | Microphone → texte → professeur → synthèse vocale. | À choisir le moment venu |
| **Connecteurs** *(plus tard)* | Sources externes (documentation web, GitHub, etc.), ajoutées une par une. | À choisir le moment venu |

---

## 2. Trajet d'une question

Voici ce qui se passe quand tu poses une question au professeur :

```
  Toi
   │  tu écris : « Pourquoi mon programme ne fonctionne pas ? »
   ▼
┌──────────────────┐
│  Interface web   │  (HTML/CSS/JS dans ton navigateur)
└────────┬─────────┘
         │  requête HTTP (JSON)
         ▼
┌──────────────────┐
│ Serveur FastAPI  │  (Python)
└────────┬─────────┘
         ▼
┌──────────────────┐      lit / écrit      ┌───────────────────┐
│ Agent pédagogique│ ◄──────────────────► │ Mémoire (SQLite)   │
│ - intention      │                       │ ton profil         │
│ - niveau d'aide  │                       └───────────────────┘
└────────┬─────────┘
         │  consignes + ta question
         ▼
┌──────────────────┐
│    Module IA     │ ──► API Claude (sur Internet)
└────────┬─────────┘
         │  réponse
         ▼
   Serveur ──► Interface ──► Toi
```

Point important : l'IA ne décide pas seule de son comportement. C'est l'**agent
pédagogique** qui lui indique comment répondre (par exemple : « donne seulement
un indice de niveau 2, pas la solution »).

---

## 3. Pourquoi ces choix ?

### Python pour le backend
- **Choisi parce que :** syntaxe lisible pour un débutant, très utilisé en IA et
  pour lire des documents (PDF, texte), cité dans le cahier des charges.
- **Alternative écartée :** JavaScript / Node.js. Avantage : un seul langage
  partout. Inconvénient : l'asynchronisme est plus déroutant au début.

### FastAPI pour le serveur
- **Choisi parce que :** simple, moderne, bien documenté, et il génère
  automatiquement une page qui décrit toutes les routes de l'API.
- **Alternatives :** Flask (plus ancien, aussi simple), Django (plus complet mais
  beaucoup plus lourd pour un débutant).

### HTML / CSS / JavaScript pour l'interface
- **Choisi parce que :** on voit clairement comment le frontend et le backend
  communiquent (section 52). Aucune bibliothèque compliquée au départ.
- **Alternative écartée :** Streamlit. Plus rapide à écrire, mais cache le
  fonctionnement du web et devient limitant ensuite.

### API Claude pour le professeur
- **Choisi parce que :** bon niveau en explication et en code.
- **Prévu :** le module IA est isolé, donc on pourra changer de fournisseur
  sans réécrire le reste de l'application.

### SQLite pour la mémoire
- **Choisi parce que :** une base de données dans un simple fichier, rien à
  installer, et tes données restent **sur ta machine** (section 20).
- **Alternative :** PostgreSQL, plus puissant, mais inutile pour un seul
  utilisateur au départ.

---

## 4. Règles de sécurité (section 33)

- La clé API est rangée dans un fichier `.env`, **jamais** dans le code.
- Le fichier `.env` est listé dans `.gitignore` : il n'est **jamais** envoyé sur GitHub.
- Un fichier `.env.example` (sans vraie clé) montre seulement le format attendu.
- Aucun mot de passe stocké en clair.
- Aucun accès automatique à tes comptes personnels.
- Aucun document envoyé à un service externe sans que ce soit clairement signalé.
- Aucune exécution automatique de code potentiellement dangereux.
- Toute action sensible demande une confirmation.

---

## 5. Plan de construction (section 41)

On ne construit **pas** tout d'un coup. Chaque étape est expliquée, validée par
toi, implémentée, testée, puis documentée.

### Étape 1 — MVP (version de base)
1. Structure du projet et serveur FastAPI minimal.
2. Page web de discussion.
3. Module IA (connexion à Claude).
4. Agent pédagogique : mode socratique et système d'indices (niveaux 1 à 6).
5. Analyse de code (« explique-moi ce code », mode debugging).
6. Mémoire des connaissances (SQLite) avec les 7 états de maîtrise
   (Non rencontré → Découverte → Compréhension fragile → Compréhension correcte
   → Maîtrisé → Maîtrisé en pratique → Autonome).
7. Import de documents (cours, notes).
8. Suivi des progrès.

### Étape 2 — Ajouts progressifs
- Évaluation diagnostique de départ (15 à 20 questions).
- Révision espacée.
- Détection de dépendance à l'IA.
- Mode examen et mode professeur.
- Tableau de bord.
- Recherche web et sources fiables.
- Voix.
- Projets guidés.
- Connecteurs externes.

---

## 6. Règle de contrôle (section 70)

Pendant toute la construction de cette application, l'agent de développement
(Claude Code) **demande la permission avant chaque action** : créer, modifier
ou supprimer un fichier, lancer une commande, installer un paquet, faire une
opération Git, accéder à Internet, toucher à un secret.

Pour chaque demande, il indique : quoi, pourquoi, quels fichiers, la commande
exacte, les risques. Une permission vaut pour **une seule** action.
