// Comportement de la page de discussion (les « muscles »).
// Rôle : envoyer ton message au serveur et afficher la réponse.

// On récupère les éléments de la page dont on a besoin.
const conversation = document.getElementById("conversation");
const formulaire = document.getElementById("formulaire");
const champMessage = document.getElementById("message");
const boutonEnvoyer = document.getElementById("bouton-envoyer");

// Ajoute un message dans la zone de conversation.
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
}

// Envoie le message au serveur et renvoie la réponse.
// « async » : la fonction peut attendre la réponse du serveur sans bloquer la page.
async function envoyerAuServeur(texte) {
  const reponse = await fetch("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: texte }),
  });

  // reponse.ok est faux si le serveur renvoie une erreur (ex. 404 : route inconnue).
  if (!reponse.ok) {
    throw new Error("Le serveur ne répond pas encore (code " + reponse.status + ").");
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
  champMessage.value = "";
  boutonEnvoyer.disabled = true;

  try {
    const reponse = await envoyerAuServeur(texte);
    afficherMessage(reponse, "professeur");
  } catch (erreur) {
    afficherMessage(erreur.message, "erreur");
  } finally {
    // « finally » s'exécute dans tous les cas, succès ou erreur.
    boutonEnvoyer.disabled = false;
    champMessage.focus();
  }
});
