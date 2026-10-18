/* Mini-lib de montage : tout est fonction du temps t (secondes). Aucun timer, aucune animation temps réel. */
const $ = (s, el = document) => el.querySelector(s);
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const easeOut = x => 1 - Math.pow(1 - clamp(x), 3);          // entrées : ease-out
const easeIn = x => Math.pow(clamp(x), 2);                    // sorties
const LAYER = new URLSearchParams(location.search).get('layer') || 'front';

/* Fenêtre d'une scène : entrée rapide, maintien, sortie propre. Renvoie {p, vis} avec p = 0..1 d'entrée,
   o = 0..1 d'opacité de sortie. in/out dans la plage 0.2-0.35 s du style. */
function phase(t, start, end, inD = 0.28, outD = 0.22) {
  if (t < start || t > end) return { vis: false, p: 0, o: 0 };
  const p = easeOut((t - start) / inD);
  const o = 1 - easeIn((t - (end - outD)) / outD);
  return { vis: true, p, o: clamp(o) };
}
/* Push-in doux (<= 6 %) : appliqué par composite.py via push.json, pas ici. */

function gradientText(el, g) {
  el.style.background = `linear-gradient(100deg, ${g.join(', ')})`;
  el.style.webkitBackgroundClip = 'text'; el.style.backgroundClip = 'text';
  el.style.color = 'transparent';
}
async function loadFonts(style, base = '../assets/fonts/') {
  const f = style.fonts, faces = [];
  for (const k of Object.keys(f)) {
    const ff = new FontFace(f[k].family, `url(${base}${f[k].file})`, { style: f[k].style || 'normal', weight: String(f[k].weight || 400) });
    faces.push(ff.load().then(x => document.fonts.add(x)));
  }
  await Promise.all(faces);
}

/* Réduit la taille de police jusqu'à ce que le texte tienne dans maxW (zone utile hors safe area). Évite tout débord. */
function fitWidth(node, px, maxW, min = 40) {
  node.style.display = 'inline-block'; node.style.whiteSpace = 'nowrap'; let size = px; node.style.fontSize = size + 'px';
  while (node.scrollWidth > maxW && size > min) { size -= 6; node.style.fontSize = size + 'px'; }
  return size;
}
