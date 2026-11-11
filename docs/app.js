/* Radar Stages — tout se passe dans le navigateur.
 * 1. charge data/offers.json (généré chaque jour par le collecteur)
 * 2. lit le CV (PDF/DOCX/TXT) et en extrait des mots-clés
 * 3. classe les offres par pertinence (type BM25) et applique les filtres
 */
"use strict";

const PDFJS = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
const PDFJS_WORKER = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
const MAMMOTH = "https://cdnjs.cloudflare.com/ajax/libs/mammoth/1.6.0/mammoth.browser.min.js";
const PAGE_SIZE = 30;
const LS = { kw: "rs.keywords", cv: "rs.cvName", fav: "rs.favorites", filters: "rs.filters" };

// ---------------------------------------------------------------- utils
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const norm = (s) => String(s ?? "").normalize("NFKD").replace(/[̀-ͯ]/g, "")
  .toLowerCase().replace(/\s+/g, " ").trim();
const reEsc = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
function store(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (_) {} }
function load(k, d) { try { const v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (_) { return d; } }
const regionName = (() => {
  let dn = null;
  try { dn = new Intl.DisplayNames(["fr"], { type: "region" }); } catch (_) {}
  return (cc) => { if (!cc) return "Pays inconnu"; try { return dn ? dn.of(cc) : cc; } catch (_) { return cc; } };
})();
function daysAgo(iso) {
  if (!iso) return null;
  return Math.floor((Date.now() - new Date(iso + "T00:00:00").getTime()) / 864e5);
}
function relDate(iso) {
  const d = daysAgo(iso);
  if (d === null) return "date inconnue";
  if (d <= 0) return "aujourd'hui";
  if (d === 1) return "hier";
  if (d < 30) return `il y a ${d} j`;
  if (d < 365) return `il y a ${Math.round(d / 30)} mois`;
  return "il y a plus d'un an";
}

// Mots vides FR / EN / DE (+ vocabulaire omniprésent dans les CV et les offres)
const STOP = new Set(`a au aux avec ce ces dans de des du elle en et eux il je la le les leur lui ma mais me meme mes moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une vos votre vous c d j l m n s t y ete etre avoir fait faire plus tres bien sans sous chez entre depuis tout tous toute toutes autre autres comme aussi ainsi dont cette cet leurs ici
the and for with from that this you your are our have has was were will would can could should into about over under more most such than then them they their there these those which while who whom what when where why how all any each few other some only own same too very just also not but out off per via its it's we us i me my he she his her him an as at be by do if in is it of on or so to up no yes
der die das und ist im mit fur von zu den dem des ein eine einer eines einem sie wir ihr bei auf als auch oder wie nach aus sind wird werden uber unser unsere
stage stages stagiaire intern internship internships praktikum h/f m/w/d f/h hf mwd job poste offre mission missions profil equipe team company entreprise annee annees year years mois months experience experiences work working travail etudiant etudiante student students ecole school universite university janvier fevrier mars avril mai juin juillet aout septembre octobre novembre decembre january february march april may june july august september october november december cv tel email mail adresse linkedin github www com fr http https nom prenom age ne nee permis francais anglais english french langues languages niveau level centres interets interests loisirs hobbies references competence competences skills specialite specialisation formation formations diplome education courant bilingue natif native notions scolaire fluent anglais allemand espagnol italien chinois portugais german spanish italian chinese ingenieur engineer etudes studies cursus actuellement currently professionnelle professionnel personnel personal projets projet project projects gestion analyse management chez within ans age contact objectif objective resume`.split(/\s+/));

// Compétences fréquentes : bonus si présentes dans le CV
const SKILLS = new Set(`python|java|javascript|typescript|sql|nosql|c++|c#|matlab|simulink|excel|vba|powerbi|power bi|tableau|sap|salesforce|git|docker|kubernetes|aws|azure|gcp|linux|react|angular|node|django|flask|spark|hadoop|pandas|numpy|tensorflow|pytorch|machine learning|deep learning|data science|data analysis|data analyst|big data|intelligence artificielle|ia|ai|nlp|catia|solidworks|autocad|ansys|abaqus|comsol|labview|arduino|fpga|vhdl|verilog|embedded|systemes embarques|robotique|robotics|automatique|mecanique|thermique|electronique|electrotechnique|genie civil|supply chain|logistique|achats|procurement|lean|six sigma|qualite|quality|project management|gestion projet|agile|scrum|marketing|marketing digital|seo|communication|finance|audit|controle gestion|comptabilite|accounting|m&a|private equity|trading|risk management|banque|ifrs|consulting|conseil|strategie|strategy|ressources humaines|juridique|droit|cybersecurite|cybersecurity|reseaux|networks|cloud|devops|figma|ux|ui|design|photoshop|illustrator|physique|physics|physique quantique|quantum|quantique|qubit|qubits|informatique quantique|quantum computing|optique quantique|photonique|photonics|optique|optics|laser|lasers|supraconducteur|superconducting|cryogenie|cryogenics|matiere condensee|condensed matter|physique fondamentale|physique des particules|particle physics|physique theorique|theoretical physics|cosmologie|cosmology|astrophysique|astrophysics|astronomie|astronomy|instrumentation|detecteur|detecteurs|detector|detectors|spectroscopie|spectroscopy|nucleaire|nuclear|neutronique|neutronics|physique nucleaire|nuclear physics|radioprotection|surete nucleaire|reacteur|reactor|fusion|plasma|plasmas|tokamak|thermohydraulique|simulation|simulation numerique|numerical simulation|modelisation|modeling|modelling|calcul scientifique|scientific computing|methodes numeriques|numerical methods|elements finis|finite element|volumes finis|monte carlo|cfd|mecanique des fluides|fluid dynamics|hpc|calcul haute performance|high performance computing|mpi|openmp|cuda|gpu|fortran|julia|qiskit|cirq|geant4|root|openfoam|lammps|gromacs|mathematica|latex|statistique|statistics|traitement du signal|signal processing|analyse de donnees|equations aux derivees partielles|edp|pde|relativite|relativity`.split("|"));
// Mots-clés proposés au premier passage (domaine de recherche configuré)
const DEFAULT_KEYWORDS = ["physique", "quantique", "astrophysique", "nucléaire", "simulation numérique",
  "physics", "quantum", "astrophysics", "nuclear", "simulation"].map((t) => ({ t, manual: true }));

// ---------------------------------------------------------------- state
const state = {
  data: null, offers: [], df: new Map(), N: 0,
  keywords: load(LS.kw, null) ?? DEFAULT_KEYWORDS, // [{t, manual}]
  favs: new Set(load(LS.fav, [])),
  zone: "all", shown: PAGE_SIZE, kwCache: new Map(),
};

// ---------------------------------------------------------------- tokenisation
function tokens(text) {
  return norm(text).split(/[^a-z0-9+#]+/).filter((w) => w.length > 1 && !/^\d+$/.test(w));
}
const SEG_SPLIT = /[,;:.!?()[\]{}|•·●▪■◦–—\/\n\r\t]+/;
function grams(text) {
  const out = [];
  // les bigrammes ne traversent pas la ponctuation ("Python, SQL" ≠ "python sql")
  for (const seg of String(text ?? "").split(SEG_SPLIT)) {
    const t = tokens(seg);
    for (let i = 0; i < t.length; i++) {
      if (STOP.has(t[i])) continue;
      out.push(t[i]);
      if (i + 1 < t.length && !STOP.has(t[i + 1])) out.push(t[i] + " " + t[i + 1]);
    }
  }
  return out;
}

// ---------------------------------------------------------------- data
async function loadData() {
  const res = await fetch("data/offers.json", { cache: "no-cache" });
  if (!res.ok) throw new Error("HTTP " + res.status);
  const data = await res.json();
  state.data = data;
  state.offers = data.offers.map((o) => ({
    ...o,
    _title: " " + norm(o.title) + " ",
    _body: " " + norm(o.company + " " + o.description) + " ",
    _all: norm(`${o.title} ${o.company} ${o.location} ${regionName(o.country)} ${o.description}`),
  }));
  state.N = state.offers.length;
  // fréquence documentaire des uni/bigrammes (sert à choisir les mots-clés du CV)
  for (const o of state.offers) {
    for (const g of new Set(grams(o.title + " " + o.description))) state.df.set(g, (state.df.get(g) || 0) + 1);
  }
  const gen = new Date(data.generated_at);
  $("#meta").textContent = `${state.N} offres · mises à jour le ${gen.toLocaleDateString("fr-FR", { day: "numeric", month: "long" })} à ${gen.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}`;
}

// ---------------------------------------------------------------- CV
function loadScript(src) {
  return new Promise((ok, ko) => {
    if (document.querySelector(`script[src="${src}"]`)) return ok();
    const s = document.createElement("script");
    s.src = src; s.onload = ok; s.onerror = () => ko(new Error("Impossible de charger " + src));
    document.head.appendChild(s);
  });
}
async function readCV(file) {
  const ext = file.name.split(".").pop().toLowerCase();
  if (ext === "pdf") {
    await loadScript(PDFJS);
    window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER;
    const pdf = await window.pdfjsLib.getDocument({ data: await file.arrayBuffer() }).promise;
    let text = "";
    for (let p = 1; p <= pdf.numPages; p++) {
      const page = await pdf.getPage(p);
      const c = await page.getTextContent();
      text += c.items.map((i) => i.str + (i.hasEOL ? "\n" : " ")).join("") + "\n";
    }
    return text;
  }
  if (ext === "docx") {
    await loadScript(MAMMOTH);
    const r = await window.mammoth.extractRawText({ arrayBuffer: await file.arrayBuffer() });
    return r.value;
  }
  return await file.text();
}

function extractKeywords(cvText, max = 18) {
  const tf = new Map();
  for (const g of grams(cvText)) tf.set(g, (tf.get(g) || 0) + 1);
  const N = state.N || 1, scored = [];
  for (const [g, f] of tf) {
    const df = state.df.get(g) || 0;
    const isSkill = SKILLS.has(g);
    if (g.length < 3 && !isSkill) continue;
    if (!isSkill && (df < 2 || df / N > 0.25)) continue; // inconnu des offres ou trop banal
    if (isSkill && df === 0) continue;
    let s = (1 + Math.log(f)) * Math.log(1 + N / (df + 1));
    if (g.includes(" ")) s *= 1.4;
    if (isSkill) s *= 2;
    scored.push([g, s]);
  }
  scored.sort((a, b) => b[1] - a[1]);
  const picked = [];
  for (const [g] of scored) {
    // évite les doublons "data" + "data analysis" quand le bigramme est déjà retenu
    if (picked.some((p) => p.includes(" ") && p.split(" ").includes(g))) continue;
    picked.push(g);
    if (picked.length >= max) break;
  }
  return picked;
}

// ---------------------------------------------------------------- scoring
function kwInfo(term) {
  if (state.kwCache.has(term)) return state.kwCache.get(term);
  const t = norm(term);
  const re = new RegExp("(?:^|[^a-z0-9])" + reEsc(t) + "(?=$|[^a-z0-9])", "g");
  let df = 0;
  for (const o of state.offers) { re.lastIndex = 0; if (re.test(o._title) || (re.lastIndex = 0, re.test(o._body))) df++; }
  const info = { re, idf: Math.log(1 + (state.N - df + 0.5) / (df + 0.5)), df };
  state.kwCache.set(term, info);
  return info;
}
const count = (re, s) => { re.lastIndex = 0; let n = 0; while (re.exec(s)) n++; return n; };

function scoreAll() {
  const kws = state.keywords.map((k) => ({ ...k, ...kwInfo(k.t), w: k.manual ? 2 : 1 }));
  let best = 0;
  for (const o of state.offers) {
    let s = 0; const hit = [];
    for (const k of kws) {
      const ft = count(k.re, o._title), fb = count(k.re, o._body);
      if (!ft && !fb) continue;
      hit.push(k.t);
      s += k.w * k.idf * (3 * ft / (ft + 0.6) + fb / (fb + 1.2));
    }
    o._score = s; o._hits = hit;
    if (s > best) best = s;
  }
  for (const o of state.offers) o._pct = best ? Math.round((100 * o._score) / best) : 0;
}

// ---------------------------------------------------------------- filters
function readFilters() {
  return {
    q: norm($("#q").value).split(" ").filter(Boolean),
    zone: state.zone,
    elig: $("#elig").value,
    country: $("#country").value,
    cesure: $("#cesure").value,
    age: +$("#age").value || 0,
    duration: $("#duration").value,
    source: $("#source").value,
    sectors: [...document.querySelectorAll("#sectors input:checked")].map((i) => i.value),
    fav: $("#favOnly").checked,
    matchOnly: $("#matchOnly").checked,
    sort: $("#sort").value,
  };
}
function passes(o, f, skip) {
  if (f.zone === "home" && o.abroad) return false;
  if (f.zone === "abroad") {
    if (!o.abroad) return false;
    if (skip !== "elig") {
      if (f.elig === "ok" && o.foreign !== "ok") return false;
      if (f.elig === "probable" && !(o.foreign === "ok" || o.foreign === "probable")) return false;
      if (f.elig === "notko" && o.foreign === "ko") return false;
    }
  }
  if (skip !== "country" && f.country && o.country !== f.country) return false;
  if (f.cesure === "yes" && o.cesure !== "yes") return false;
  if (f.cesure === "notend" && (o.cesure === "no" || o.cesure === "fin_etudes")) return false;
  if (f.age) { const d = daysAgo(o.posted); if (d === null || d > f.age) return false; }
  if (f.duration) {
    const m = o.duration_months;
    if (!m) return false;
    if (f.duration === "short" && m > 3) return false;
    if (f.duration === "mid" && (m < 4 || m > 5)) return false;
    if (f.duration === "six" && m !== 6) return false;
    if (f.duration === "long" && m <= 6) return false;
  }
  if (skip !== "source" && f.source && o.source !== f.source) return false;
  if (skip !== "sector" && f.sectors.length && !f.sectors.includes(o.sector)) return false;
  if (f.fav && !state.favs.has(o.id)) return false;
  if (f.matchOnly && state.keywords.length && !(o._hits && o._hits.length)) return false;
  if (f.q.length && !f.q.every((w) => o._all.includes(w))) return false;
  return true;
}

// ---------------------------------------------------------------- render
function countBy(list, key) {
  const m = new Map();
  for (const o of list) m.set(o[key], (m.get(o[key]) || 0) + 1);
  return [...m.entries()].sort((a, b) => b[1] - a[1]);
}

function renderFacets(f) {
  // pays
  const cSel = $("#country"), cur = cSel.value;
  const cList = countBy(state.offers.filter((o) => passes(o, f, "country")), "country").filter(([c]) => c);
  cSel.innerHTML = `<option value="">Tous les pays</option>` + cList.map(([c, n]) =>
    `<option value="${esc(c)}"${c === cur ? " selected" : ""}>${esc(regionName(c))} (${n})</option>`).join("");
  if (cur && !cList.some(([c]) => c === cur)) cSel.insertAdjacentHTML("beforeend", `<option value="${esc(cur)}" selected>${esc(regionName(cur))} (0)</option>`);
  // secteurs
  const sList = countBy(state.offers.filter((o) => passes(o, f, "sector")), "sector");
  const all = new Set([...sList.map(([s]) => s), ...f.sectors]);
  const n = new Map(sList);
  $("#sectors").innerHTML = [...all].sort((a, b) => (n.get(b) || 0) - (n.get(a) || 0)).map((s) =>
    `<label class="check"><input type="checkbox" value="${esc(s)}"${f.sectors.includes(s) ? " checked" : ""}> ${esc(s)}<span class="n">${n.get(s) || 0}</span></label>`).join("");
  // sources
  const srcSel = $("#source"), curS = srcSel.value;
  srcSel.innerHTML = `<option value="">Toutes</option>` + countBy(state.offers.filter((o) => passes(o, f, "source")), "source")
    .map(([s, k]) => `<option value="${esc(s)}"${s === curS ? " selected" : ""}>${esc(s)} (${k})</option>`).join("");
  // niveaux d'éligibilité (avec compteurs)
  if (f.zone === "abroad") {
    const base = state.offers.filter((o) => passes(o, f, "elig"));
    const c = (pred) => base.filter(pred).length;
    const opts = $("#elig").options;
    opts[0].textContent = `Oui, explicitement (${c((o) => o.foreign === "ok")})`;
    opts[1].textContent = `Oui ou probable — UE / Suisse (${c((o) => o.foreign === "ok" || o.foreign === "probable")})`;
    opts[2].textContent = `Tout sauf les exclus (${c((o) => o.foreign !== "ko")})`;
  }
}

const ACCENTS = { a: "[aàâä]", e: "[eéèêë]", i: "[iîï]", o: "[oôö]", u: "[uùûü]", c: "[cç]", n: "[nñ]" };
function highlight(text, terms) {
  let html = esc(text);
  for (const t of new Set(terms.filter(Boolean))) {
    const pat = [...esc(t)].map((ch) => ACCENTS[ch] || reEsc(ch)).join("");
    const re = new RegExp("(^|[^\\p{L}\\p{N}])(" + pat + ")(?=$|[^\\p{L}\\p{N}])", "giu");
    html = html.replace(re, "$1<mark>$2</mark>");
  }
  return html;
}

const CESURE = { yes: ["Césure acceptée", "ok"], no: ["Pas de césure", "ko"], fin_etudes: ["Fin d'études", "warn"] };
const FOREIGN = {
  ok: ["Ouvert aux écoles étrangères", "ok"], probable: ["Probablement ouvert", "warn"],
  ko: ["Réservé aux écoles locales", "ko"], unknown: ["Éligibilité non précisée", ""],
};

function card(o) {
  const b = [];
  b.push(`<span class="badge accent">${esc(o.sector)}</span>`);
  if (o.abroad && FOREIGN[o.foreign]) { const [l, c] = FOREIGN[o.foreign]; b.push(`<span class="badge ${c}" title="${esc(o.foreign_evidence)}">${l}</span>`); }
  if (CESURE[o.cesure]) { const [l, c] = CESURE[o.cesure]; b.push(`<span class="badge ${c}" title="${esc(o.cesure_evidence)}">${l}</span>`); }
  if (o.duration_months) b.push(`<span class="badge">${o.duration_months} mois</span>`);
  if (o.remote) b.push(`<span class="badge">Télétravail</span>`);
  b.push(`<span class="badge">${esc(o.source)}</span>`);

  const ev = [];
  if (o.abroad && o.foreign_evidence) ev.push(`<p class="evidence"><strong>Éligibilité :</strong> « ${esc(o.foreign_evidence)} »</p>`);
  if (o.cesure_evidence) ev.push(`<p class="evidence"><strong>Césure :</strong> « ${esc(o.cesure_evidence)} »</p>`);

  const score = state.keywords.length ? `<div class="score"><span class="meter"><i style="width:${o._pct}%"></i></span>
      <span>Pertinence ${o._pct}%</span>${o._hits.length ? `<span class="matched">· ${o._hits.slice(0, 8).map(esc).join(", ")}</span>` : ""}</div>` : "";

  const terms = [...o._hits, ...readFilters().q];
  return `<article class="card">
    <div class="card-top">
      <div class="card-main">
        <h3><a href="${esc(o.url)}" target="_blank" rel="noopener">${esc(o.title)}</a></h3>
        <div class="sub"><b>${esc(o.company)}</b> · ${esc(o.location || "")}${o.country ? ` (${esc(regionName(o.country))})` : ""} · ${o.posted_estimated ? "repérée " : ""}${relDate(o.posted)}</div>
      </div>
      <button class="fav${state.favs.has(o.id) ? " on" : ""}" data-fav="${esc(o.id)}" title="Favori" aria-label="Ajouter aux favoris">${state.favs.has(o.id) ? "★" : "☆"}</button>
    </div>
    <div class="badges">${b.join("")}</div>
    ${score}
    <details><summary>Voir la description</summary>${ev.join("")}
      <div class="desc">${highlight(o.description, terms)}</div>
      <p><a href="${esc(o.url)}" target="_blank" rel="noopener">Ouvrir l'offre d'origine →</a></p>
    </details>
  </article>`;
}

function render(resetPage = true) {
  if (!state.data) return;
  if (resetPage) state.shown = PAGE_SIZE;
  const f = readFilters();
  $("#eligField").hidden = f.zone !== "abroad";
  renderFacets(f);
  const list = state.offers.filter((o) => passes(o, f));
  const hasKw = state.keywords.length > 0;
  const byDate = (a, b) => (b.posted || "").localeCompare(a.posted || "");
  const sorters = {
    relevance: (a, b) => (hasKw ? b._score - a._score : 0) || byDate(a, b),
    date: byDate,
    duration: (a, b) => (b.duration_months || 0) - (a.duration_months || 0) || byDate(a, b),
    company: (a, b) => a.company.localeCompare(b.company, "fr") || byDate(a, b),
  };
  list.sort(sorters[f.sort]);
  $("#count").textContent = `${list.length} offre${list.length > 1 ? "s" : ""}` +
    (f.sort === "relevance" && !hasKw ? " · ajoute ton CV ou des mots-clés pour trier par pertinence" : "");
  $("#results").innerHTML = list.length
    ? list.slice(0, state.shown).map(card).join("")
    : `<div class="empty">Aucune offre ne correspond à ces filtres.${f.zone === "abroad" && f.elig === "ok" ? "<br>Essaie « Oui ou probable » dans le filtre d'éligibilité." : ""}</div>`;
  $("#more").hidden = list.length <= state.shown;
  renderExternal(f);
  store(LS.filters, { ...f, q: $("#q").value });
}

function renderChips() {
  $("#chips").innerHTML = state.keywords.map((k, i) =>
    `<span class="chip${k.manual ? " manual" : ""}">${esc(k.t)}<button type="button" data-rm="${i}" aria-label="Retirer ${esc(k.t)}">×</button></span>`).join("");
  store(LS.kw, state.keywords);
}

function renderExternal(f) {
  const terms = (f.q.length ? $("#q").value : state.keywords.filter((k) => k.manual).concat(state.keywords).slice(0, 2).map((k) => k.t).join(" ")).trim();
  const q = encodeURIComponent(terms);
  const qs = encodeURIComponent(("stage " + terms).trim());
  const links = [
    ["HelloWork", `https://www.hellowork.com/fr-fr/emploi/recherche.html?k=${q}&c=Stage`],
    ["JobTeaser", `https://www.jobteaser.com/fr/job-offers?query=${q}&contract=internship`],
    ["Welcome to the Jungle", `https://www.welcometothejungle.com/fr/jobs?query=${q}&refinementList%5Bcontract_type%5D%5B%5D=internship`],
    ["LinkedIn", `https://www.linkedin.com/jobs/search/?keywords=${q}&f_E=1`],
    ["Indeed", `https://fr.indeed.com/jobs?q=${qs}`],
  ];
  if (f.zone !== "home") {
    links.push(["Erasmus Intern", `https://erasmusintern.org/traineeships?search_api_views_fulltext=${q}`]);
    links.push(["EURES", `https://eures.europa.eu/jobs-and-learning/search-jobs_fr?keyword=${q}`]);
  }
  const a = ([n, u]) => `<a href="${esc(u)}" target="_blank" rel="noopener">${esc(n)} ↗</a>`;
  $("#external").innerHTML = links.map(a).join("");
  $("#orgs").innerHTML = ORGS.map(a).join("");
}
// Organismes dont le site carrière ne peut pas être collecté automatiquement
const ORGS = [
  ["ESA", "https://jobs.esa.int"],
  ["ESO", "https://www.eso.org/public/jobs/"],
  ["ITER", "https://www.iter.org/jobs"],
  ["CNES", "https://recrutement.cnes.fr/fr/annonces"],
  ["ONERA", "https://www.onera.fr/fr/rejoindre-onera"],
  ["EDF", "https://www.edf.fr/edf-recrute"],
  ["Framatome", "https://www.framatome.com/fr/carrieres/"],
  ["Orano", "https://www.orano.group/fr/carrieres"],
];

// ---------------------------------------------------------------- events
function setKeywords(list) {
  state.keywords = list;
  renderChips(); scoreAll(); render();
}

function bind() {
  const file = $("#cvFile"), drop = $("#drop");
  const handle = async (f) => {
    if (!f) return;
    $("#dropLabel").innerHTML = `Lecture de <strong>${esc(f.name)}</strong>…`;
    try {
      const text = await readCV(f);
      const kws = extractKeywords(text);
      if (!kws.length) throw new Error("aucun texte exploitable (CV scanné en image ?)");
      const manual = state.keywords.filter((k) => k.manual);
      setKeywords([...manual, ...kws.filter((t) => !manual.some((m) => m.t === t)).map((t) => ({ t, manual: false }))]);
      store(LS.cv, f.name);
      $("#dropLabel").innerHTML = `<strong>${esc(f.name)}</strong> analysé · ${kws.length} mots-clés`;
      $("#sort").value = "relevance"; render();
    } catch (e) {
      $("#dropLabel").innerHTML = `<strong>Erreur :</strong> ${esc(e.message)}`;
    }
  };
  file.addEventListener("change", () => handle(file.files[0]));
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", (e) => { e.preventDefault(); drop.classList.remove("over"); handle(e.dataTransfer.files[0]); });

  $("#addKw").addEventListener("submit", (e) => {
    e.preventDefault();
    const vals = $("#kwInput").value.split(/[,;]/).map((s) => s.trim().toLowerCase()).filter(Boolean);
    if (!vals.length) return;
    const rest = state.keywords.filter((k) => !vals.includes(k.t));
    setKeywords([...vals.map((t) => ({ t, manual: true })), ...rest]);
    $("#kwInput").value = "";
  });
  $("#chips").addEventListener("click", (e) => {
    const i = e.target.dataset.rm; if (i === undefined) return;
    setKeywords(state.keywords.filter((_, j) => j !== +i));
  });
  $("#clearKw").addEventListener("click", () => { setKeywords([]); store(LS.cv, null); $("#dropLabel").innerHTML = "<strong>Dépose ton CV</strong> ou clique (PDF, DOCX, TXT)"; });

  $("#zone").addEventListener("click", (e) => {
    const v = e.target.dataset.v; if (!v) return;
    state.zone = v;
    for (const b of $("#zone").children) b.classList.toggle("on", b.dataset.v === v);
    $("#country").value = "";
    render();
  });
  for (const id of ["#elig", "#country", "#cesure", "#age", "#duration", "#source", "#sort", "#favOnly", "#matchOnly"]) $(id).addEventListener("change", () => render());
  $("#sectors").addEventListener("change", () => render());
  let t; $("#q").addEventListener("input", () => { clearTimeout(t); t = setTimeout(render, 180); });
  $("#more").addEventListener("click", () => { state.shown += PAGE_SIZE; render(false); });
  $("#results").addEventListener("click", (e) => {
    const id = e.target.dataset.fav; if (!id) return;
    state.favs.has(id) ? state.favs.delete(id) : state.favs.add(id);
    store(LS.fav, [...state.favs]);
    e.target.classList.toggle("on"); e.target.textContent = state.favs.has(id) ? "★" : "☆";
  });
  $("#reset").addEventListener("click", () => {
    $("#q").value = ""; for (const id of ["#country", "#cesure", "#age", "#duration", "#source"]) $(id).value = "";
    $("#elig").value = "ok"; $("#favOnly").checked = false; $("#matchOnly").checked = true; state.zone = "all";
    for (const b of $("#zone").children) b.classList.toggle("on", b.dataset.v === "all");
    document.querySelectorAll("#sectors input").forEach((i) => (i.checked = false));
    render();
  });
}

function restoreFilters() {
  const f = load(LS.filters, null); if (!f) return;
  $("#q").value = f.q || "";
  for (const k of ["elig", "cesure", "duration", "sort"]) if (f[k]) $("#" + k).value = f[k];
  if (f.age) $("#age").value = String(f.age);
  $("#favOnly").checked = !!f.fav;
  if (f.matchOnly !== undefined) $("#matchOnly").checked = !!f.matchOnly;
  if (f.zone) { state.zone = f.zone; for (const b of $("#zone").children) b.classList.toggle("on", b.dataset.v === f.zone); }
  if (f.sectors?.length) $("#sectors").innerHTML = f.sectors.map((s) => `<input type="checkbox" value="${esc(s)}" checked hidden>`).join("");
  if (f.country) $("#country").innerHTML = `<option value="${esc(f.country)}" selected></option>`;
  if (f.source) $("#source").innerHTML = `<option value="${esc(f.source)}" selected></option>`;
}

(async function init() {
  bind();
  restoreFilters();
  renderChips();
  const cv = load(LS.cv, null);
  if (cv && state.keywords.length) $("#dropLabel").innerHTML = `<strong>${esc(cv)}</strong> (profil enregistré) · cliquer pour remplacer`;
  try {
    await loadData();
    scoreAll();
    render();
  } catch (e) {
    $("#meta").textContent = "Impossible de charger les offres.";
    $("#results").innerHTML = `<div class="empty">Le fichier <code>data/offers.json</code> est introuvable (${esc(e.message)}).<br>Lance le collecteur : <code>python -m scraper.main</code></div>`;
  }
})();
