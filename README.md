# SAD OFFICINE — SaaS d'aide à la décision pour la gestion des stocks en pharmacie

## 1. Contexte

SAD OFFICINE est aujourd'hui un fichier Excel utilisé en conditions réelles par des pharmacies d'officine pour décider, chaque jour, quoi commander, en quelle quantité, et à quel rythme. L'objectif de ce projet est de transformer ce moteur de calcul (déjà conçu, testé et validé sur 4 692 références / 12 mois d'historique) en application web SaaS multi-officines, **sans réécrire la logique métier**.

Le fichier `SAD_OFFICINE_REFERENCE_DEVELOPPEUR.xlsx` (onglet `MODÈLE SAD`) est la **source de vérité** pour toutes les formules. En cas de doute sur un calcul, c'est ce fichier qui fait foi, pas le cahier des charges.

## 2. Principe directeur

- SAD OFFICINE est un **compagnon**, jamais un remplaçant du logiciel de gestion d'officine existant (ex. Logpharma). Pas de caisse, pas de facturation, pas de réglementaire.
- Entrée des données par **import manuel de fichier** (CSV/Excel exporté du logiciel existant). Pas de connexion API en V1.
- L'application **recommande**, le pharmacien **décide et commande** lui-même.

## 3. Stack technique retenue

| Couche | Choix |
| --- | --- |
| Backend API | **FastAPI** (Python) |
| ORM / accès BDD | **SQLAlchemy** (+ Alembic pour les migrations) |
| Base de données | PostgreSQL (recommandé pour la prod ; SQLite acceptable en dev) |
| Frontend | **React** (Vite, TypeScript recommandé) |
| Auth | JWT (un compte = une officine, isolation stricte des données) |
| Calcul / parsing fichiers | pandas / openpyxl pour le mapping et le calcul du moteur |
| Export | génération PDF (ex. WeasyPrint/reportlab) et Excel (openpyxl) |

## 4. Les 4 modules fonctionnels

| Module SaaS | Onglet Excel équivalent | Rôle |
| --- | --- | --- |
| Import de données | DONNÉES MENSUELLES | Upload + mappage de colonnes du fichier d'export |
| Réglages | TABLEAU DE BORD | Délais fournisseurs, cycle de commande T, coût/taux de détention |
| Moteur de calcul | MODÈLE SAD | CMM, ABC, SS, PC, EOQ, cycle périodique, FSN/VED, risque fournisseur |
| Tableau de pilotage | TABLEAU DE PILOTAGE | KPIs + liste d'action triée par urgence |

## 5. Moteur de calcul — résumé des formules (V2, juin 2026)

- **CMM** = somme des ventes des 12 derniers mois / 12 (exclure les valeurs négatives)
- **CMMax** = pic de consommation sur 12 mois
- **Classification ABC** : tri par CA annuel décroissant, A jusqu'à 80% du CA cumulé, B de 80 à 95%, C au-delà
- **σ (écart-type mensuel)** : calculé sur les 12 derniers mois de ventes — remplace l'ancien proxy CMMax-CMM
- **Z (facteur de service)** : dépend du statut VED de la référence (voir tableau ci-dessous)
- **SS (stock de sécurité, continu)** = MAX(0, Z × σ × RACINE(DLmax / 30))
- **PC (point de commande)** = (CMM / 30 × DLmoy) + SS — statuts : RUPTURE (stock ≤ 0), CRITIQUE (stock ≤ SS), COMMANDER (stock ≤ PC), sinon OK
- **EOQ (Wilson)** = RACINE(2 × Demande_annuelle × Coût_commande / (Taux_détention × Prix_cession)) — indicateur informatif uniquement
- **Cycle périodique** (décade/mensuel, T en jours, Y = risque fournisseur additionnel) :
  - SS_periodique = MAX(0, Z × σ × RACINE((DLmax + T + Y) / 30))
  - S (niveau de recomplètement) = (CMM / 30 × (DLmoy + T + Y)) + SS_periodique
  - **Qté à commander = MAX(0, ROUND(S − Stock_actuel, 0))** ← c'est cette quantité qui doit être commandée, jamais l'EOQ
- **FSN** (calcul automatique) : nombre de mois avec vente > 0 sur 12 mois → Fast (≥10), Slow (3-9), Non-moving (<3). Si Non-moving : quantité neutralisée à 0, sauf si VED = Vital (alors 1 unité)
- **VED** (saisie manuelle, classes A/B uniquement) : Vital / Essentiel / Désirable / Non renseigné → pilote Z

| Statut VED | Niveau de service | Z par défaut |
| --- | --- | --- |
| Vital | 99% | 2,33 |
| Essentiel | 95% | 1,645 |
| Désirable | 90% | 1,28 |
| Non renseigné (défaut) | 95% | 1,645 |

FSN, VED, CMM, EOQ, σ, Z restent **en coulisses** : le pharmacien ne voit que des résultats actionnables et un texte de décision en langage clair (ex. *"Produit vital en rupture — commander en urgence"*).

## 6. Exigences non fonctionnelles clés

- Isolation stricte des données entre comptes (officines parfois concurrentes du même réseau)
- Mappage de colonnes configurable à l'import — ne jamais figer un format de fichier
- Pas d'intégration API avec le logiciel de gestion en V1
- Interface compréhensible par un pharmacien non technique, aucun jargon logistique visible

## 7. Périmètre du MVP

- Import de fichier avec mappage de colonnes
- Moteur de calcul complet (CMM, ABC, SS, PC, EOQ, cycle périodique, FSN/VED)
- Tableau de pilotage avec export PDF/Excel
- Page Réglages
- Un compte = une officine, isolation stricte des données

### Hors MVP (évolutions futures)

- Comptes multi-utilisateurs par officine
- Alertes SMS/WhatsApp
- Historique et graphiques d'évolution
- Intégration directe avec le logiciel de gestion
- Tableau de bord consolidé multi-officines

---

## 8. Backlog — User Stories détaillées

Les stories sont regroupées par epic et triées par priorité de développement (P0 = bloquant MVP).

### Epic A — Authentification & comptes (P0) ✅ VALIDÉE

**US-A1 — Création de compte officine**
> En tant que pharmacien, je veux créer un compte pour mon officine, afin de pouvoir importer mes données et utiliser l'application de façon isolée des autres pharmacies.
- Critères d'acceptation :
  - Formulaire d'inscription (email, mot de passe, nom de l'officine)
  - Un compte = une officine, identifiant officine généré et utilisé comme clé d'isolation sur toutes les tables métier
  - Mot de passe hashé (bcrypt/argon2), email unique
- Tâches techniques : modèle `Officine`, modèle `User`, endpoint `POST /auth/register`, validation Pydantic

**US-A2 — Connexion / déconnexion**
> En tant que pharmacien, je veux me connecter avec mon email/mot de passe afin d'accéder à mes données.
- Critères : JWT émis à la connexion, expiration configurable, endpoint `POST /auth/login`, refresh token optionnel
- Tâches techniques : middleware FastAPI de vérification JWT, dépendance `get_current_officine` injectée dans chaque route métier

**US-A3 — Isolation stricte des données**
> En tant que pharmacien, je veux être sûr qu'aucune autre officine ne peut voir mes données, même indirectement (agrégats, comparatifs).
- Critères : toute requête SQL est filtrée par `officine_id` ; tests automatisés vérifiant qu'un token A ne peut jamais lire les données de B
- Tâches techniques : `officine_id` en clé étrangère obligatoire sur toutes les tables (`reference`, `import`, `parametre`), revue systématique des requêtes SQLAlchemy

### Epic B — Import de données (P0) ✅ VALIDÉE

**US-B1 — Upload de fichier d'export**
> En tant que pharmacien, je veux uploader mon fichier CSV/Excel d'export afin d'alimenter l'application sans ressaisie.
- Critères : accepte .csv et .xlsx, taille max configurable, message d'erreur clair si format illisible
- Tâches techniques : endpoint `POST /imports`, stockage temporaire du fichier, parsing pandas/openpyxl

**US-B2 — Mappage de colonnes configurable**
> En tant que pharmacien, je veux indiquer une fois quelle colonne de mon fichier correspond à Code, Désignation, Prix, Stock, ventes mensuelles, etc., car chaque export Logpharma peut varier selon la version installée.
- Critères : interface de mappage (liste déroulante par colonne cible), mappage sauvegardé par officine et réutilisé aux imports suivants, modification possible
- Tâches techniques : modèle `ColumnMapping` (officine_id, champ_cible, colonne_source), endpoint `POST /imports/mapping`, aperçu des 5 premières lignes avant validation

**US-B3 — Mise à jour des données à chaque réimport**
> En tant que pharmacien, je veux que mes calculs se mettent à jour automatiquement à chaque réimport mensuel, afin de toujours avoir des recommandations à jour.
- Critères : le stock actuel et l'historique de ventes sont mis à jour ; le moteur de calcul est relancé automatiquement après import
- Tâches techniques : job de recalcul déclenché en fin d'import (synchrone MVP, queue asynchrone en V2), historisation des 12 derniers mois de ventes par référence

**US-B4 — Gestion des erreurs d'import**
> En tant que pharmacien, je veux être averti clairement si des lignes de mon fichier sont invalides, afin de pouvoir corriger mon export.
- Critères : rapport d'import (lignes importées / lignes en erreur + raison), l'import ne bloque pas sur quelques lignes invalides
- Tâches techniques : validation Pydantic par ligne, log des erreurs renvoyé au frontend

### Epic C — Réglages (P0) ✅ VALIDÉE (simplifiée)

> US-C1 implémentée en version simplifiée : délais fournisseurs globaux à l'officine
> (`ParametreOfficine`), pas encore par circuit (`ParametreCircuit` reste à faire si
> le besoin par circuit se confirme). US-C4 (niveaux de service par VED) non fait —
> Z reste codé en dur dans `moteur_sad.py` (`Z_PAR_VED`).


**US-C1 — Paramétrage des délais fournisseurs par circuit**
> En tant que pharmacien, je veux renseigner mes délais fournisseurs (moyen/max) par circuit (local/import), afin que le moteur calcule un stock de sécurité réaliste.
- Critères : un délai moyen et max par circuit, modifiable à tout moment, recalcul automatique du moteur après modification
- Tâches techniques : modèle `ParametreCircuit` (officine_id, circuit, delai_moyen, delai_max)

**US-C2 — Choix du cycle de commande**
> En tant que pharmacien, je veux choisir mon cycle de commande (continu, décade = 10j, mensuel = 30j), afin que l'application utilise la bonne formule (point de commande ou niveau de recomplètement).
- Critères : sélecteur global ou par circuit, valeur T stockée et utilisée dans les formules section 6.5
- Tâches techniques : champ `cycle_commande_jours` sur `ParametreCircuit` ou au niveau officine

**US-C3 — Coût de commande et taux de détention**
> En tant que pharmacien, je veux renseigner mon coût de commande et mon taux de détention, afin que l'EOQ soit calculé correctement.
- Critères : champs numériques en Réglages, valeurs par défaut suggérées, recalcul automatique
- Tâches techniques : modèle `ParametreOfficine`

**US-C4 — Modification des niveaux de service par statut VED**
> En tant que pharmacien, je veux pouvoir ajuster le niveau de service (%) associé à chaque statut VED (Vital/Essentiel/Désirable), afin d'adapter la prudence du réapprovisionnement à ma réalité.
- Critères : modification du % recalcule automatiquement Z (via INV.NORMALE.STANDARD) et relance le moteur sur toutes les références concernées
- Tâches techniques : implémentation de la fonction inverse de la loi normale standard (ex. `scipy.stats.norm.ppf`), modèle `ParametreVED` (officine_id, statut, niveau_service, z_calcule)

### Epic D — Moteur de calcul (P0) ✅ VALIDÉE (US-D1 à D10, 67/67 tests moteur)

> `moteur_sad.py` + `calcul_officine.py` implémentent US-D1 à D8, déclenchés
> automatiquement après chaque import (`POST /api/v1/calcul/lancer`) et testés
> (`test_moteur_sad.py`, 67/67). US-D9 et US-D10 ajoutés (`routes/references.py`) :
> `PATCH /references/{id}/ved` (limité aux classes A/B, sinon 422) et
> `PATCH /references/{id}/risque-fournisseur` (entier ≥ 0), chacun relançant le
> moteur sur toute l'officine après modification. `GET /references` ajouté aussi,
> pour lister/tester — ce n'est qu'une liste brute (pas de KPIs agrégés, pas de
> texte de décision), donc Epic E (US-E1 à E4) reste entièrement à faire.
> Testé manuellement de bout en bout (rejet classe C, rejet valeur VED invalide,
> acceptation classe A/B, interaction correcte avec la neutralisation US-D8 :
> une référence Non-moving + VED=Vital passe bien à qté=1).

**US-D1 — Calcul CMM et CMMax**
> En tant que système, je dois calculer la CMM et le CMMax de chaque référence à partir des 12 derniers mois de ventes, en excluant les valeurs négatives.
- Critères : résultat identique au fichier Excel de référence à 0,01 près sur l'échantillon de test fourni
- Tâches techniques : fonction pure testée unitairement, jeu de tests basé sur des lignes réelles du fichier `MODÈLE SAD`

**US-D2 — Classification ABC**
> En tant que système, je dois classer chaque référence en A/B/C selon son poids dans le CA annuel cumulé.
- Critères : tri décroissant par CA, seuils 80%/95% respectés
- Tâches techniques : fonction de classification appliquée à l'ensemble des références d'une officine après chaque import

**US-D3 — Calcul de σ (écart-type mensuel)**
> En tant que système, je dois calculer l'écart-type des ventes mensuelles sur 12 mois pour chaque référence, comme base du nouveau calcul du stock de sécurité.
- Critères : formule conforme à la V2 (remplace l'ancien proxy CMMax-CMM), validée sur le fichier de référence
- Tâches techniques : fonction statistique testée sur échantillon réel

**US-D4 — Calcul du stock de sécurité (SS) et du point de commande (PC), mode continu**
> En tant que système, je dois calculer SS = MAX(0, Z×σ×RACINE(DLmax/30)) et PC = (CMM/30×DLmoy)+SS, et déterminer le statut (RUPTURE/CRITIQUE/COMMANDER/OK).
- Critères : Z dépend du statut VED de la référence (US-C4) ; conformité avec le fichier Excel V2
- Tâches techniques : fonction de calcul + détermination du statut selon les seuils stock ≤ 0 / ≤ SS / ≤ PC

**US-D5 — Calcul EOQ (Wilson)**
> En tant que système, je dois calculer la quantité économique de commande à titre indicatif.
- Critères : EOQ = RACINE(2×Demande_annuelle×Coût_commande/(Taux_détention×Prix_cession)) ; clairement marqué comme indicatif, ne pilote jamais la quantité commandée en cycle périodique
- Tâches techniques : fonction de calcul

**US-D6 — Calcul du cycle périodique (SS, S, quantité à commander)**
> En tant que système, je dois calculer, pour le mode décade/mensuel, le SS périodique, le niveau de recomplètement S, et la quantité à commander = MAX(0, ROUND(S - Stock_actuel, 0)).
- Critères : intègre T (cycle) et Y (risque fournisseur additionnel par référence) ; conforme au fichier de référence
- Tâches techniques : fonction de calcul, prise en compte du champ `risque_fournisseur_jours` par référence

**US-D7 — Classification FSN automatique**
> En tant que système, je dois classer chaque référence en Fast/Slow/Non-moving selon le nombre de mois avec vente > 0 sur 12 mois, à chaque réimport.
- Critères : Fast ≥10 mois, Slow 3-9, Non-moving <3
- Tâches techniques : fonction de calcul appliquée après chaque import

**US-D8 — Neutralisation de la recommandation pour les références Non-moving**
> En tant que système, je dois neutraliser la quantité à commander (continu ET cycle) pour les références Non-moving, sauf si elles sont VED = Vital (auquel cas 1 unité).
- Critères : conforme à la règle métier section 6.6 ; ces références n'apparaissent pas dans le tableau de pilotage (sauf cas Vital)
- Tâches techniques : règle appliquée en sortie du moteur de calcul, avant constitution de la liste d'action

**US-D9 — Saisie du statut VED par référence**
> En tant que pharmacien, je veux pouvoir attribuer un statut VED (Vital/Essentiel/Désirable) à une référence de classe A ou B, afin que le niveau de service et donc le stock de sécurité soient ajustés.
- Critères : saisie limitée aux classes A et B ; statut "Non renseigné" par défaut tant que rien n'est saisi ; modification déclenche un recalcul du SS pour la référence concernée
- Tâches techniques : endpoint `PATCH /references/{id}/ved`, recalcul ciblé

**US-D10 — Saisie du risque fournisseur additionnel par référence**
> En tant que pharmacien, je veux pouvoir ajouter un nombre de jours de risque fournisseur supplémentaire sur une référence précise (ex. rupture récurrente chez le grossiste), afin que le stock de sécurité en tienne compte.
- Critères : champ numérique par référence, défaut 0, modifiable à tout moment, recalcul automatique
- Tâches techniques : endpoint `PATCH /references/{id}/risque-fournisseur`

### Epic E — Tableau de pilotage (P0)

**US-E1 — Affichage des 5 indicateurs clés**
> En tant que pharmacien, je veux voir en un coup d'œil le nombre de références en rupture, en critique, à commander, la valeur totale FCFA de la prochaine commande, et la trésorerie libérée potentielle.
- Critères : 5 indicateurs recalculés à chaque accès au tableau de bord / après chaque import
- Tâches techniques : endpoint `GET /dashboard/kpis`, agrégation côté backend

**US-E2 — Liste d'action triée par urgence**
> En tant que pharmacien, je veux voir une liste de mes références à traiter, triée RUPTURE puis CRITIQUE puis COMMANDER, avec code, désignation, classe ABC, stock actuel, statut, quantité à commander et valeur FCFA.
- Critères : les références au statut OK n'apparaissent pas ; les références Non-moving non Vitales n'apparaissent pas (US-D8) ; code couleur rouge/orange/jaune
- Tâches techniques : endpoint `GET /dashboard/liste-action` avec tri et filtre, composant React tableau avec code couleur conditionnel

**US-E3 — Texte de décision en langage clair**
> En tant que pharmacien non technique, je veux voir un texte clair expliquant pourquoi une référence doit être traitée (ex. "Produit vital en rupture — commander en urgence"), sans jargon logistique.
- Critères : génération du texte selon une matrice statut + VED + FSN ; aucun terme technique (CMM, EOQ, σ, Z, FSN, VED) visible dans l'UI pharmacien
- Tâches techniques : fonction de génération de texte côté backend, basée sur la colonne "Décision FSN" du fichier de référence

**US-E4 — Export PDF / Excel de la liste d'action**
> En tant que pharmacien, je veux exporter la liste d'action en PDF ou Excel, afin de l'envoyer à mon grossiste ou de l'imprimer.
- Critères : export reprend les colonnes affichées à l'écran, format propre et imprimable
- Tâches techniques : endpoint `GET /dashboard/export?format=pdf|xlsx`, génération via WeasyPrint/reportlab et openpyxl

### Epic F — Fiche référence (P1)

**US-F1 — Consultation détaillée d'une référence**
> En tant que pharmacien, je veux consulter le détail d'une référence (historique de ventes, statut, paramètres appliqués), afin de comprendre une recommandation avant d'agir.
- Critères : page dédiée affichant les données métier en langage clair
- Tâches techniques : endpoint `GET /references/{id}`, composant React fiche détail

### Epic G — Qualité, tests, infra (transverse, P0)

**US-G1 — Tests de non-régression du moteur de calcul**
> En tant qu'équipe de développement, je veux un jeu de tests automatisés basé sur des lignes réelles du fichier Excel de référence, afin de garantir que le moteur reproduit fidèlement les formules validées.
- Critères : au moins 20 références du fichier `MODÈLE SAD` utilisées comme cas de test, tolérance 0,01 sur les résultats numériques
- Tâches techniques : pytest, fixtures basées sur extraction du xlsx

**US-G2 — Migrations de base de données**
> En tant que développeur, je veux gérer les évolutions du schéma de données via des migrations versionnées.
- Tâches techniques : Alembic configuré dès le départ

**US-G3 — Documentation API**
> En tant que développeur frontend, je veux une documentation interactive de l'API afin d'intégrer rapidement le frontend React.
- Critères : Swagger/OpenAPI auto-généré par FastAPI, accessible en dev
- Tâches techniques : configuration native FastAPI (`/docs`)

---

## 9. Ordre de développement suggéré (sprints)

1. **Sprint 0** — ✅ Setup projet (FastAPI + SQLAlchemy + Alembic + SQLite, React + Vite) + Epic A (auth/comptes)
2. **Sprint 1** — ✅ Epic B (import + mappage de colonnes) + modèle de données complet (section 5 du cahier des charges)
3. **Sprint 2** — ✅ Epic D complet (US-D1 à D10) + Epic G1 (67 tests de non-régression) + `GET /references` pour lister/tester
4. **Sprint 3** — ✅ Epic C fait (simplifié — délais globaux, pas par circuit ; niveaux de service VED toujours codés en dur)
5. **Sprint 4** — ⬜ Epic E (tableau de pilotage + export) — `GET /references` existe déjà comme brique de base, mais KPIs agrégés, tri/filtre dédié et texte de décision (US-E1 à E3) restent à faire
6. **Sprint 5** — ⬜ Epic F (fiche référence) + polish UI/UX non-technique + tests end-to-end

---

## 10. Source de vérité

Avant toute implémentation ou validation du moteur de calcul, **toujours vérifier la formule réelle dans `SAD_OFFICINE_REFERENCE_DEVELOPPEUR.xlsx`, onglet `MODÈLE SAD`** — c'est le document qui fait foi en cas de doute, pas ce README ni le cahier des charges.