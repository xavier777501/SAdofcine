# SAD OFFICINE — Handoff Frontend → Backend (pour Xavier)

**Date :** 6 juillet 2026
**De :** Jawad (frontend)
**Sujet :** Contrat d'API attendu pour Epic C/D/E

---

## 1. Contrat d'API attendu — `GET /api/v1/pilotage`

Filtré par `officine_id` comme les autres routes (via `get_current_officine`).

```json
{
  "kpis": {
    "nb_rupture": 3,
    "nb_critique": 5,
    "nb_commander": 8,
    "valeur_prochaine_commande": 1245000,
    "tresorerie_liberee": 380000
  },
  "references": [
    {
      "code": "A0231",
      "designation": "Paracétamol 1g cp",
      "classe": "A",
      "stock_actuel": 0,
      "statut": "RUPTURE",
      "qte_a_commander": 120,
      "valeur": 96000,
      "ved": "VITAL",
      "decision": "Produit vital en rupture — commander en urgence"
    }
  ]
}
```

Points importants :
- `statut` ∈ `RUPTURE` / `CRITIQUE` / `COMMANDER` uniquement — les références `OK` et les `Non-moving` non-Vitales ne doivent **pas** être incluses dans `references` (US-D8 / section 7 du cahier des charges).
- `references` peut être renvoyé dans n'importe quel ordre, le frontend se chargera du tri par urgence (RUPTURE → CRITIQUE → COMMANDER).
- `decision` : texte en langage clair (US-E3, basé sur la colonne "Décision FSN" du fichier Excel), sans jargon logistique.
- `valeur` = quantité à commander × prix de cession (à confirmer avec le fichier Excel de référence).

## 2. Dépendances à ne pas oublier (Epic C avant/avec Epic D)

Le moteur de calcul (Epic D) a besoin des réglages (Epic C) en entrée : délais fournisseurs par circuit, cycle de commande T, coût de commande, taux de détention, niveaux de service par statut VED. Le README (section 8, Epic C) a déjà le détail des modèles/endpoints à prévoir.
