# Sprint 5 — Tâche frontend : Page Stock

## Prérequis
```
git pull origin main
```
Lancer l'appli : `start.bat`

---

## Ce qu'il faut créer

### 1. `frontend/src/services/references.js`
```js
import api from './api'

export const getReferences = () => api.get('/references').then(r => r.data)

export const updateVed = (id, ved) =>
  api.patch(`/references/${id}/ved`, { ved }).then(r => r.data)

export const updateRisque = (id, jours) =>
  api.patch(`/references/${id}/risque-fournisseur`, { risque_fournisseur_jours: jours }).then(r => r.data)
```

### 2. `frontend/src/pages/Stock.jsx`
Tableau de **toutes** les références avec :
- Colonnes : Code · Désignation · Classe · FSN · VED · Stock · CMM · SS · PC · Statut · Qté à cmd.
- Barre de recherche (filtre client sur code + désignation)
- Filtre par statut (TOUS / RUPTURE / CRITIQUE / COMMANDER / OK)
- Édition inline **VED** (select Vital / Essentiel / Désirable / —) — uniquement si classe A ou B
- Édition inline **risque fournisseur** (champ numérique en jours)
- Couleurs de ligne par statut (même palette que Dashboard : rouge/orange/jaune)

### 3. `frontend/src/App.jsx`
Ajouter la route `/stock` avec `<AppShell><Stock /></AppShell>` (même pattern que `/import`).

### 4. `frontend/src/components/AppShell.jsx`
Ajouter un lien **Stock** dans la barre latérale, entre Dashboard et Importer.

---

## Champs API disponibles
`code, designation, forme, prix_cession, classe, ved, fsn, stock_actuel, cmm, ss, pc, statut, qte_a_commander, risque_fournisseur_jours, couverture_jours, tresorerie_liberee`

> Note : le PATCH VED est refusé (422) si la référence est de classe C — gérer ce cas en désactivant le select.
