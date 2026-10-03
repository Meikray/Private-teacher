// Voix : parler au professeur (dictée) et l'écouter (lecture vocale).
// Section 19 : microphone -> reconnaissance vocale -> assistant ;
//              assistant -> synthèse vocale -> haut-parleur.
//
// On utilise les fonctions vocales intégrées au navigateur :
// - SpeechRecognition (dictée) : dans Chrome/Edge, l'audio est envoyé aux
//   serveurs du navigateur (Google ou Microsoft) pour être transcrit. C'est
//   pourquoi la dictée est désactivée par défaut et signalée (section 33).
// - speechSynthesis (lecture) : fonctionne sur ta machine.

import { markdownVersParole } from "./markdown.js";
import { lireReglages } from "./reglages.js";

const Reconnaissance = window.SpeechRecognition || window.webkitSpeechRecognition;

export const dicteeDisponible = Boolean(Reconnaissance);
export const lectureDisponible = "speechSynthesis" in window;

let reconnaissance = null;

// Démarre la dictée. Le texte reconnu est transmis à surTexte(texte).
// surFin() est appelée quand la dictée s'arrête.
export function demarrerDictee(surTexte, surFin) {
  if (!dicteeDisponible) return false;
  reconnaissance = new Reconnaissance();
  reconnaissance.lang = lireReglages().langue;
  reconnaissance.interimResults = false;
  reconnaissance.continuous = false;
  reconnaissance.onresult = (evenement) => {
    const texte = Array.from(evenement.results)
      .map((resultat) => resultat[0].transcript)
      .join(" ");
    surTexte(texte);
  };
  reconnaissance.onend = surFin;
  reconnaissance.onerror = surFin;
  reconnaissance.start();
  return true;
}

export function arreterDictee() {
  if (reconnaissance) reconnaissance.stop();
}

// Liste des voix disponibles pour la langue choisie.
export function voixDisponibles() {
  if (!lectureDisponible) return [];
  const langue = lireReglages().langue.slice(0, 2);
  return speechSynthesis.getVoices().filter((v) => v.lang.startsWith(langue));
}

// Lit un texte à voix haute, phrase par phrase : de petites pauses entre
// les phrases rendent l'écoute plus naturelle (comme un professeur).
export function lire(texteMarkdown) {
  if (!lectureDisponible) return;
  arreterLecture();
  const reglages = lireReglages();
  const voix = speechSynthesis.getVoices().find((v) => v.name === reglages.voix);
  const phrases = markdownVersParole(texteMarkdown).match(/[^.!?\n]+[.!?]?/g) || [];

  for (const phrase of phrases) {
    if (!phrase.trim()) continue;
    const enonce = new SpeechSynthesisUtterance(phrase.trim());
    enonce.lang = reglages.langue;
    enonce.rate = Number(reglages.vitesse);
    if (voix) enonce.voice = voix;
    speechSynthesis.speak(enonce);
  }
}

export function arreterLecture() {
  if (lectureDisponible) speechSynthesis.cancel();
}
