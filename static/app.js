// Comportement de la page de discussion (les « muscles »).
// Rôle : envoyer la conversation au serveur et afficher la réponse du professeur.

// On récupère les éléments de la page dont on a besoin.
const conversation = document.getElementById("conversation");
const formulaire = document.getElementById("formulaire");
const champMessage = document.getElementById("message");
const boutonEnvoyer = document.getElementById("bouton-envoyer");

// L'API Claude ne retient rien entre deux messages : c'est la page qui garde
// toute la conversation et l'envoie en entier à chaque fois.
// Chaque élément ressemble à : { role: "user" ou "assistant", content: "..." }
const historique = [];

// Ajoute un message dans la zone de conversation et renvoie la bulle créée.
// auteur : "eleve", "professeur" ou "erreur" (sert à choisir le style CSS).
function afficherMessage(texte, auteur) {
  const bulle = document.createElement("div");
  bulle.className = "message " + auteur;
  // textContent (et non innerHTML) : le texte est affiché tel quel,
  // sans être interprété comme du HTML. Cela évite les failles XSS (section 60).
  bulle.textContent = texte;
  conversation.appendChild(bulle);
  // Fait défiler la conversation jusqu'au dernier message.
  conversation.scrollTop = conversation.scrollHeight;
  return bulle;
}

// Envoie toute la conversation au serveur et renvoie la réponse du professeur.
// « async » : la fonction peut attendre la réponse du serveur sans bloquer la page.
async function envoyerAuServeur() {
  const reponse = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ historique: historique }),
  });

  // reponse.ok est faux si le serveur renvoie une erreur.
  if (!reponse.ok) {
    // Le serveur explique l'erreur dans le champ "detail" (s'il y en a un).
    let explication = "Erreur du serveur (code " + reponse.status + ").";
    try {
      const erreur = await reponse.json();
      if (typeof erreur.detail === "string") {
        explication = erreur.detail;
      }
    } catch {
      // La réponse n'était pas du JSON : on garde le message générique.
    }
    throw new Error(explication);
  }

  const donnees = await reponse.json();
  return donnees.reponse;
}

// Ce qui se passe quand tu cliques sur « Envoyer ».
formulaire.addEventListener("submit", async (evenement) => {
  // Empêche le comportement par défaut du formulaire (recharger la page).
  evenement.preventDefault();

  const texte = champMessage.value.trim();
  if (texte === "") {
    return;
  }

  afficherMessage(texte, "eleve");
  historique.push({ role: "user", content: texte });
  champMessage.value = "";
  boutonEnvoyer.disabled = true;

  // Bulle temporaire pendant que Claude prépare sa réponse.
  const attente = afficherMessage("Le professeur réfléchit…", "professeur");

  try {
    const reponse = await envoyerAuServeur();
    attente.remove();
    afficherMessage(reponse, "professeur");
    historique.push({ role: "assistant", content: reponse });
  } catch (erreur) {
    attente.remove();
    // On retire ton dernier message de l'historique : tu pourras le renvoyer
    // sans créer de doublon.
    historique.pop();
    afficherMessage(erreur.message, "erreur");
  } finally {
    // « finally » s'exécute dans tous les cas, succès ou erreur.
    boutonEnvoyer.disabled = false;
    champMessage.focus();
  }
});
