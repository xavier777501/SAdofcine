import api from './api'

const UPLOAD_TIMEOUT_MS = 300000 // 5 min — un import de ~5000 lignes peut prendre 2-3 min

/**
 * Indique si l'historique (Type 1) a déjà été initialisé, pour proposer
 * automatiquement le bon type d'import au pharmacien sans lui demander de choisir.
 */
export async function getEtatImport() {
  const { data } = await api.get('/imports/etat')
  return data
}

export async function previewImport(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/imports/preview', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: UPLOAD_TIMEOUT_MS,
  })
  return data
}

export async function getMapping() {
  const { data } = await api.get('/imports/mapping')
  return data
}

export async function saveMapping(mapping) {
  const payload = {
    mapping: Object.entries(mapping)
      .filter(([, colonneSource]) => Boolean(colonneSource))
      .map(([champCible, colonneSource]) => ({
        champ_cible: champCible,
        colonne_source: colonneSource,
      })),
  }
  const { data } = await api.post('/imports/mapping', payload)
  return data
}

export async function runImport(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/imports/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: UPLOAD_TIMEOUT_MS,
  })
  return data
}

export async function runImportCommande(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/imports/commande', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: UPLOAD_TIMEOUT_MS,
  })
  return data
}

/**
 * Import Type 1, mécanisme glissant : Logpharma ne fournit qu'un export
 * "Listing de Produit à Commander" (même format que le Type 2), pas un
 * fichier "12 mois" tout prêt. Chaque import représente automatiquement le
 * nouveau mois le plus récent — le mois le plus ancien sort de l'historique.
 * Pour l'initialisation, répéter cet import jusqu'à 12 fois, du mois le plus
 * ancien au plus récent.
 */
export async function runImportHistoriqueLogpharma(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/imports/historique-logpharma', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: UPLOAD_TIMEOUT_MS,
  })
  return data
}

/**
 * Import Type 1 "rapide" à partir d'un seul fichier Logpharma couvrant une
 * longue période (ex. l'année entière) en un seul total de sorties. Ne donne
 * qu'un CMM initial — le stock de sécurité et les quantités à commander
 * restent indisponibles tant que les mois ne sont pas complétés un par un.
 */
export async function runImportHistoriqueAnnuel(file) {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/imports/historique-logpharma-annuel', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: UPLOAD_TIMEOUT_MS,
  })
  return data
}

export async function getImportHistory() {
  const { data } = await api.get('/imports/')
  return data
}

export const CHAMPS_LABELS = {
  code: 'Code article / CIP13',
  designation: 'Désignation',
  forme: 'Forme pharmaceutique',
  prix_cession: 'Prix de cession',
  prix_public: 'Prix public',
  stock_actuel: 'Stock actuel',
  circuit: 'Circuit de distribution',
  vente_m1: 'Ventes M-1 (mois le plus récent)',
  vente_m2: 'Ventes M-2',
  vente_m3: 'Ventes M-3',
  vente_m4: 'Ventes M-4',
  vente_m5: 'Ventes M-5',
  vente_m6: 'Ventes M-6',
  vente_m7: 'Ventes M-7',
  vente_m8: 'Ventes M-8',
  vente_m9: 'Ventes M-9',
  vente_m10: 'Ventes M-10',
  vente_m11: 'Ventes M-11',
  vente_m12: 'Ventes M-12',
}

export const CHAMPS_OBLIGATOIRES = ['code', 'designation', 'stock_actuel', 'vente_m1']

const SYNONYMES = {
  code: ['code', 'cip', 'cip13', 'codecip', 'codearticle', 'codeproduit', 'ref', 'reference', 'referencearticle'],
  designation: ['designation', 'libelle', 'libelleproduit', 'nom', 'nomproduit', 'produit', 'article', 'denomination'],
  forme: ['forme', 'formepharmaceutique', 'formegalenique'],
  prix_cession: ['prixcession', 'prixgrossiste', 'prixachat', 'pbr', 'prixht', 'puht'],
  prix_public: ['prixpublic', 'prixvente', 'ppv', 'prixttc', 'puttc'],
  stock_actuel: ['stock', 'stockactuel', 'qtestock', 'quantitestock', 'stockdisponible', 'qte'],
  circuit: ['circuit', 'circuitdistribution', 'typecircuit'],
}

const DIACRITICS_PATTERN = /[̀-ͯ]/g

function normalize(str) {
  return str
    .toString()
    .normalize('NFD')
    .replace(DIACRITICS_PATTERN, '')
    .toLowerCase()
    .replace(/[^a-z0-9]/g, '')
}

const MOIS_FR = {
  janvier: 1, fevrier: 2, mars: 3, avril: 4, mai: 5, juin: 6,
  juillet: 7, aout: 8, septembre: 9, octobre: 10, novembre: 11, decembre: 12,
}

/**
 * Si le nom de colonne contient un mois calendaire (ex: "Ventes Janvier 2026"),
 * calcule à combien de "mois en arrière" (M-1, M-2...) ce mois correspond,
 * par rapport à aujourd'hui. Permet de retrouver le bon champ vente_mN même si
 * le fichier renomme ses colonnes chaque mois.
 */
function moisEnArriere(colonneOriginale, aujourdHui = new Date()) {
  const norm = normalize(colonneOriginale)
  const nomMois = Object.keys(MOIS_FR).find((m) => norm.includes(m))
  if (!nomMois) return null

  const moisColonne = MOIS_FR[nomMois]
  const anneeMatch = colonneOriginale.match(/(20\d{2})/)
  const moisActuel = aujourdHui.getMonth() + 1
  const anneeActuelle = aujourdHui.getFullYear()

  const anneeColonne = anneeMatch
    ? Number(anneeMatch[1])
    : moisColonne <= moisActuel
      ? anneeActuelle
      : anneeActuelle - 1

  const ecart = (anneeActuelle * 12 + moisActuel) - (anneeColonne * 12 + moisColonne)
  return ecart >= 1 && ecart <= 12 ? ecart : null
}

/**
 * Propose un mappage automatique en comparant les noms de colonnes du fichier
 * aux champs cibles connus (synonymes courants, motifs "M1"/"Mois1", ou noms de
 * mois calendaires convertis en position relative). L'utilisateur reste libre
 * de corriger chaque sélection ensuite.
 */
export function autoMatchMapping(colonnes, champsCibles) {
  const colonnesNormalisees = colonnes.map((col) => ({ original: col, norm: normalize(col) }))
  const used = new Set()
  const mapping = {}

  for (const champ of champsCibles) {
    let match

    if (champ.startsWith('vente_m')) {
      const numero = Number(champ.replace('vente_m', ''))
      const pattern = new RegExp(`^(ventes?|mois|m)0*${numero}$`)

      match = colonnesNormalisees.find((c) => !used.has(c.original) && pattern.test(c.norm))

      if (!match) {
        match = colonnesNormalisees.find(
          (c) => !used.has(c.original) && moisEnArriere(c.original) === numero,
        )
      }
    } else {
      const synonymes = SYNONYMES[champ] || []
      match = colonnesNormalisees.find((c) => !used.has(c.original) && synonymes.includes(c.norm))
    }

    if (match) {
      mapping[champ] = match.original
      used.add(match.original)
    }
  }

  return mapping
}

/**
 * Vérifie qu'un mappage précédemment sauvegardé reste applicable au nouveau
 * fichier : sépare les champs dont la colonne source existe toujours de ceux
 * dont la colonne a disparu (ex: le fichier nomme ses colonnes de vente par
 * mois calendaire, qui change à chaque export).
 */
export function revalidateMapping(mappingSauvegarde, colonnesActuelles) {
  const valide = {}
  const aRevoir = []

  for (const [champ, colonne] of Object.entries(mappingSauvegarde)) {
    if (colonnesActuelles.includes(colonne)) {
      valide[champ] = colonne
    } else {
      aRevoir.push(champ)
    }
  }

  return { valide, aRevoir }
}
