# Design Bootstrap

Fondation de design réutilisable — née sur StockAid, pensée pour être copiée
telle quelle dans n'importe quel futur projet (React + Tailwind v4 ou non).

## Contenu

```
design-system/
  tokens.css          couleurs, ombres, rayons, typographie, transitions
  interactions.css     feedback tactile + transitions de page/thème animées
  theme.js             gestion clair/sombre (localStorage + attribut sur <html>)
  components/
    Button.jsx          bouton dégradé + ombre colorée au survol
    Card.jsx             carte à ombre premium, variante accent/hoverable
    Input.jsx            champ de formulaire, anneau de focus lumineux
    Badge.jsx             pastille de statut
    Alert.jsx              bannière d'information/erreur avec icône
    ThemeToggle.jsx          bouton soleil/lune, transition circulaire
```

## Installation dans un nouveau projet (React + Vite + Tailwind v4)

1. Copiez le dossier `design-system/` à la racine de `frontend/src/` (ou
   ailleurs, adaptez les imports relatifs dans les composants).
2. Dans votre `index.css` :

   ```css
   @import "tailwindcss";
   @import "./design-system/tokens.css";
   @import "./design-system/interactions.css";

   /* Mode sombre piloté par attribut/classe plutôt que par la seule
      préférence système (nécessaire pour que ThemeToggle fonctionne) */
   @custom-variant dark (&:where([data-theme='dark'], [data-theme='dark'] *, .dark, .dark *));
   ```

3. Dans votre point d'entrée (`main.jsx`), avant le premier rendu :

   ```js
   import { initTheme } from './design-system/theme'
   initTheme()
   ```

4. Utilisez les composants :

   ```jsx
   import Button from './design-system/components/Button'
   import Card from './design-system/components/Card'

   <Card accent="brand" hoverable>
     <Button variant="primary">Valider</Button>
   </Card>
   ```

## Sans Tailwind (HTML/CSS pur)

`tokens.css` et `interactions.css` ne dépendent d'aucun framework — importez-les
seuls et utilisez les variables directement :

```css
.mon-bouton {
  background: var(--color-brand-gradient);
  box-shadow: var(--shadow-sm);
  border-radius: var(--radius-md);
}
.mon-bouton:hover {
  box-shadow: var(--shadow-brand);
}
```

## Philosophie

- **Jamais de couleur décorative pure** : rouge/orange/jaune restent réservés
  aux statuts (rupture/critique/à commander), bleu aux actions secondaires,
  le dégradé de marque aux actions principales.
- **Profondeur, pas de bruit** : les ombres sont à deux couches (large + serrée)
  pour un rendu doux, jamais une ombre dure à un seul niveau.
- **Le mouvement a un sens** : les transitions de page glissent dans la
  direction de navigation (avant/arrière), le bouton de thème révèle le
  nouveau thème en cercle depuis l'endroit cliqué — jamais d'animation
  gratuite.
- **Mode sombre pensé dès le départ**, pas rajouté après coup : chaque
  token a sa variante sombre dans `tokens.css`.

## Pour l'appliquer à StockAid

Le thème actuel de StockAid (`frontend/src/index.css` + composants dans
`frontend/src/components/`) peut migrer vers ce bootstrap progressivement :
remplacer `SubmitButton` par `Button` (variant="primary"), `FormField` par
`Input`, ajouter `Card`/`Badge`/`Alert` sur le Dashboard et l'écran d'Import.
Rien ne casse entre-temps : les deux systèmes peuvent cohabiter le temps de
la migration, les noms de tokens (`--color-brand`, etc.) sont identiques.
