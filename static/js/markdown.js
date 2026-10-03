// Conversion d'un petit sous-ensemble de Markdown en HTML, de façon SÛRE.
//
// Principe de sécurité (section 60, failles XSS) : on « échappe » d'abord
// TOUT le texte (< devient &lt; etc.), puis on ajoute nous-mêmes quelques
// balises connues. Le texte de Claude ne peut donc jamais injecter de HTML.
//
// Pris en charge : blocs de code ```, `code`, **gras**, *italique*,
// titres #, listes - / 1., liens [texte](https://...).

function echapper(texte) {
  return texte
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

// Mise en forme à l'intérieur d'une ligne (texte déjà échappé).
function enLigne(texte) {
  return texte
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*)\*/g, "$1<em>$2</em>")
    // Liens : seulement http(s), ouverts dans un nouvel onglet.
    .replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );
}

export function markdownVersHtml(source) {
  const lignes = echapper(source).split("\n");
  const html = [];
  let liste = null; // "ul", "ol" ou null
  let paragraphe = [];
  let code = null; // lignes du bloc de code en cours

  const fermerParagraphe = () => {
    if (paragraphe.length) {
      html.push("<p>" + enLigne(paragraphe.join("<br>")) + "</p>");
      paragraphe = [];
    }
  };
  const fermerListe = () => {
    if (liste) {
      html.push("</" + liste + ">");
      liste = null;
    }
  };

  for (const ligne of lignes) {
    // Début ou fin d'un bloc de code ```
    if (ligne.trim().startsWith("```")) {
      if (code === null) {
        fermerParagraphe();
        fermerListe();
        code = [];
      } else {
        html.push("<pre><code>" + code.join("\n") + "</code></pre>");
        code = null;
      }
      continue;
    }
    if (code !== null) {
      code.push(ligne);
      continue;
    }

    const titre = ligne.match(/^(#{1,4})\s+(.*)$/);
    const puce = ligne.match(/^\s*[-*]\s+(.*)$/);
    const numero = ligne.match(/^\s*\d+[.)]\s+(.*)$/);

    if (titre) {
      fermerParagraphe();
      fermerListe();
      const niveau = Math.min(titre[1].length + 2, 4); // # -> h3, ## -> h4
      html.push(`<h${niveau}>${enLigne(titre[2])}</h${niveau}>`);
    } else if (puce || numero) {
      fermerParagraphe();
      const type = puce ? "ul" : "ol";
      if (liste !== type) {
        fermerListe();
        html.push("<" + type + ">");
        liste = type;
      }
      html.push("<li>" + enLigne((puce || numero)[1]) + "</li>");
    } else if (ligne.trim() === "") {
      fermerParagraphe();
      fermerListe();
    } else {
      fermerListe();
      paragraphe.push(ligne);
    }
  }

  // Bloc de code non refermé : on l'affiche quand même.
  if (code !== null) {
    html.push("<pre><code>" + code.join("\n") + "</code></pre>");
  }
  fermerParagraphe();
  fermerListe();
  return html.join("");
}

// Version « à lire à voix haute » : sans code ni symboles Markdown.
export function markdownVersParole(source) {
  return source
    .replace(/```[\s\S]*?```/g, " (voir le bloc de code à l'écran) ")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
    .replace(/[*#>]/g, "")
    .replace(/^\s*[-]\s+/gm, "")
    .trim();
}
