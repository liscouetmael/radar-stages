# Radar Stages

Site perso de recherche de stage, réglé pour la physique (quantique, physique fondamentale, astrophysique, nucléaire, simulation numérique). Tu déposes ton CV et tu ajoutes des mots-clés si tu veux. Le site classe alors par pertinence les offres collectées chaque jour sur les sites carrières (CEA, CERN, IRSN, ArianeGroup, Thales, Airbus, start-up du quantique…) et sur des agrégateurs d'offres.

## Fonctionnement

```
GitHub Actions (tous les jours)              GitHub Pages (site statique)
┌────────────────────────────────┐           ┌─────────────────────────────────┐
│ scraper/  (Python)             │           │ docs/index.html + app.js        │
│  • CEA, IRSN, CERN, Assystem…  │           │  • lecture du CV dans le        │
│  • ArianeGroup, Airbus, Thales,│  écrit    │    navigateur (PDF/DOCX/TXT)    │
│    Quandela, Alice & Bob…      │ ───────►  │  • mots-clés + pertinence       │
│  • France Travail, Adzuna,     │ offers.json│ • filtres : étranger, pays,    │
│    (mots-clés de config.yaml)  │           │    secteur, césure, date, durée │
│  • enrichissement automatique  │           │  • favoris, liens HelloWork /   │
│    (pays, césure, éligibilité) │           │    JobTeaser / WTTJ / LinkedIn  │
└────────────────────────────────┘           └─────────────────────────────────┘
```

- **Ton CV ne quitte jamais ton navigateur.** Le site en extrait des mots-clés en local. Ils sont gardés dans ton navigateur (`localStorage`) pour ta prochaine visite.
- **Calcul de la pertinence** : on calcule un score de type BM25. Un mot-clé trouvé dans le titre compte trois fois plus que dans la description. Un mot-clé rare compte plus qu'un mot-clé courant. Un mot-clé ajouté à la main compte double.
- **Stages à l'étranger** : chaque offre hors de France reçoit un statut, avec l'extrait de l'offre qui justifie la décision :
  - ✅ **ouvert** : l'offre mentionne explicitement une convention de stage, Erasmus, le sponsoring de visa, les « international students », etc.
  - 🟡 **probable** : l'offre demande un statut étudiant sans exiger une école locale, et le stage est dans l'UE, l'EEE ou en Suisse.
  - ⛔ **exclu** : l'offre exige d'être « enrolled in a US university », « authorized to work without sponsorship », « immatrikuliert an einer deutschen Hochschule »…
  - ❔ **non précisé**.
  
  Par défaut, le mode « Étranger » n'affiche que les offres **explicitement ouvertes**. Tu peux élargir aux offres « probables ».
- **Césure** : l'offre est classée « césure mentionnée », « fin d'études » ou « pas de césure » selon son texte.

## Mise en ligne sur GitHub (une seule fois)

1. Crée un dépôt sur GitHub, par exemple `radar-stages`, puis pousse ce dossier :
   ```bash
   git remote add origin https://github.com/<ton-pseudo>/radar-stages.git
   git push -u origin main
   ```
2. **Settings → Pages** : choisis *Deploy from a branch*, branche `main`, dossier `/docs`.
3. **Settings → Actions → General → Workflow permissions** : choisis *Read and write permissions*. Le robot en a besoin pour publier les offres.
4. (Recommandé) **Settings → Secrets and variables → Actions** : ajoute les clés gratuites. Elles multiplient le nombre d'offres :
   | Secret | Où l'obtenir |
   |---|---|
   | `FT_CLIENT_ID`, `FT_CLIENT_SECRET` | [francetravail.io](https://francetravail.io) → créer une application → API « Offres d'emploi v2 ». Cette API reprend aussi des offres de sites partenaires. |
   | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` | [developer.adzuna.com](https://developer.adzuna.com). Couvre une dizaine de pays : UK, US, Allemagne, Pays-Bas… |
5. Onglet **Actions → Collecte des offres → Run workflow** pour lancer une première collecte. Ensuite, la collecte tourne tous les matins.

Le site sera accessible sur `https://<ton-pseudo>.github.io/radar-stages/`.

## Ajouter des entreprises ou des mots-clés

Tout se règle dans [`scraper/config.yaml`](scraper/config.yaml) :

- `search_terms` : les mots-clés métier envoyés aux moteurs de recherche (France Travail, Adzuna). Exemples : `["data", "finance", "mécanique"]`.
- `companies` : la liste des sites carrières. Pour trouver l'identifiant d'une entreprise, regarde l'URL de sa page « carrières » :

  | Si l'URL ressemble à… | Section | Champ |
  |---|---|---|
  | `xxx.wd3.myworkdayjobs.com/Site` | `workday` | `tenant: xxx, wd: wd3, site: Site` |
  | `boards.greenhouse.io/xxx` ou `job-boards.greenhouse.io/xxx` | `greenhouse` | `slug: xxx` |
  | `jobs.lever.co/xxx` | `lever` | `slug: xxx` |
  | `jobs.ashbyhq.com/xxx` | `ashby` | `slug: xxx` |
  | `jobs.smartrecruiters.com/xxx` / `careers.smartrecruiters.com/xxx` | `smartrecruiters` | `slug: xxx` |
  | `apply.workable.com/xxx` | `workable` | `slug: xxx` |
  | `xxx.talent-soft.com` ou site « offre-de-emploi/liste-offres.aspx » (CEA) | `talentsoft` | `base: https://…` |

## Lancer en local

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows  (macOS/Linux : source .venv/bin/activate)
pip install -r requirements.txt
python -m scraper.main            # écrit docs/data/offers.json
python -m pytest -q tests         # tests des règles de détection
python -m http.server -d docs 8000   # puis ouvrir http://localhost:8000
```

## Pourquoi HelloWork et JobTeaser ne sont pas collectés directement

- **HelloWork** interdit aux robots ses pages de recherche (voir son `robots.txt`). Ses offres arrivent quand même en partie via l'API France Travail.
- **JobTeaser** demande une connexion avec ton compte école.
- **LinkedIn, Indeed et Welcome to the Jungle** interdisent la collecte automatique dans leurs conditions d'utilisation.

Le site affiche donc des **liens de recherche déjà préparés** vers ces plateformes, avec tes mots-clés.

## Limites

- La détection (césure, éligibilité, secteur, durée) repose sur des règles de mots-clés. Elle se trompe parfois. **Lis toujours l'offre d'origine** : l'extrait qui justifie chaque décision est affiché pour que tu puisses vérifier vite.
- Adzuna ne fournit qu'un extrait de chaque description. Les statuts « césure » et « éligibilité » de ces offres sont donc souvent « non précisé ».
