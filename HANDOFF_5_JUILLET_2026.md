# SAD OFFICINE — Handoff Développeur · 5 juillet 2026

**Branche :** main  
**Repo :** xavier777501/SAdofcine  
**Commits poussés :** `19bdf52` · `64d4bc9`

---

## 1. Ce qui a été fait aujourd'hui

### Migration SQLite (abandon de PostgreSQL)
Remplacement de `psycopg2-binary` et `asyncpg` par SQLite.  
`DATABASE_URL=sqlite:///./sad_officine.db` dans `.env`.  
`sqlalchemy.dialects.postgresql.UUID` remplacé par le type cross-DB `sqlalchemy.Uuid`.  
`connect_args={"check_same_thread": False}` ajouté dans `database.py`.  
**Objectif :** application installable sur un seul poste Windows, sans frais d'hébergement.

### Création automatique des tables au démarrage
`Base.metadata.create_all(bind=engine)` dans l'événement `startup` de `main.py`.  
Tous les modèles sont importés avant pour que SQLAlchemy les enregistre.  
Plus besoin de lancer `alembic upgrade head` manuellement.

### Auth premier lancement — flux is-setup / setup / login
- `GET /auth/is-setup` → `{"configured": bool}`
- Si non configuré : `POST /auth/setup` crée l'officine + le pharmacien + retourne un JWT
- L'inscription publique est supprimée : application mono-poste
- Ajout `PATCH /auth/me/password` pour changer les identifiants plus tard

### Correction Swagger — HTTPBearer à la place d'OAuth2PasswordBearer
Swagger affichait un formulaire OAuth2 complexe. Changé en `HTTPBearer` dans `deps.py` :  
Swagger affiche maintenant un simple champ « Value » où coller le JWT.

### Bug corrigé — UUID string → objet uuid.UUID pour la query SQLAlchemy
Le JWT stocke l'ID en string. SQLAlchemy avec `Uuid(as_uuid=True)` attend un objet Python `uuid.UUID`.  
**Erreur :** `'str' object has no attribute 'hex'`  
**Correction :** `User.id == uuid.UUID(user_id)` dans `deps.py`

### Bug corrigé — ResponseValidationError Pydantic v2 sur l'UUID
Schema `ImportLogOut.id: str` refusait l'objet `uuid.UUID` retourné par SQLAlchemy.  
**Correction :** `from uuid import UUID` et `id: UUID` — Pydantic v2 ne coerce pas automatiquement.

### Frontend — page Setup.jsx + flux App.jsx + Login.jsx nettoyé
- `App.jsx` appelle `GET /auth/is-setup` au chargement : redirige vers `/setup` ou `/login`
- `Setup.jsx` : saisie nom d'officine + email + mot de passe (min 8 car.), appelle `POST /auth/setup`
- `Login.jsx` : lien "Pas encore de compte ?" supprimé

### Fichier start.bat créé à la racine du projet
Lance le backend et le frontend en un double-clic.  
Vérifie que le venv existe, que le port 8000 est libre, installe `node_modules` si absent,  
crée `frontend/.env` si absent, ouvre le navigateur sur `http://localhost:5173`.

### Epic B Backend complet — modèles, file_parser, routes imports
- **Nouveaux modèles :** `Reference`, `VenteMensuelle`, `ImportLog`, `ColumnMapping`
- **Service `file_parser.py` :** lecture CSV (détection auto séparateur) et XLSX, gestion formats numériques FR (1.234,56), ventes négatives → 0, champs obligatoires validés ligne par ligne
- **Routes `/api/v1/imports/` :** mapping GET/POST, preview (5 lignes sans écriture DB), import complet (upsert références + remplacement ventes), historique
- **Testé avec 4 692 lignes Excel — 0 erreurs**

### Push GitHub — 2 commits
- `19bdf52` — Epic A (rev): SQLite, auth premier lancement, frontend
- `64d4bc9` — Epic B: Import CSV/XLSX, modèles, parser, routes API
- Fichiers sensibles exclus : `.env`, `sad_officine.db`, `venv/`, `node_modules/`

---

## 2. Pour le développeur frontend — prise en main

> **Important :** le backend doit tourner sur `http://localhost:8000` et le frontend sur `http://localhost:5173`. Ne pas committer le fichier `backend/.env` ni `sad_officine.db`.

### Étape 1 — Prérequis à installer une seule fois

| Outil | Version min | Vérification |
|---|---|---|
| Python | 3.10 | `python --version` |
| Node.js | 18 | `node --version` |
| Git | — | `git --version` |

### Étape 2 — Cloner le dépôt

```powershell
git clone https://github.com/xavier777501/SAdofcine.git sadofficne
cd sadofficne
```

Si tu avais déjà cloné, tire les dernières modifications :

```powershell
git pull origin main
```

### Étape 3 — Créer le fichier `backend/.env`

Ce fichier n'est pas dans le dépôt (exclu par `.gitignore`). Crée-le manuellement dans le dossier `backend/` :

```
APP_NAME=SAD OFFICINE
DATABASE_URL=sqlite:///./sad_officine.db
SECRET_KEY=change-moi-en-production-32-caracteres-min
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
FRONTEND_URL=http://localhost:5173
DEBUG=true
MAX_UPLOAD_SIZE_MB=50
```

> La valeur de `SECRET_KEY` peut être n'importe quelle chaîne longue pour le développement local. Ne jamais la partager ni la committer.

### Étape 4 — Créer le venv Python et installer les dépendances backend

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirement.txt
cd ..
```

### Étape 5 — Lancer l'application

Double-clique sur **start.bat** à la racine du projet.  
Deux fenêtres de terminal s'ouvrent (backend + frontend) et le navigateur s'ouvre automatiquement sur `http://localhost:5173`.

> **Premier lancement :** la page Setup apparaît. Saisis un nom d'officine, un email et un mot de passe. Ces identifiants seront utilisés pour toutes les connexions futures.

Si tu préfères lancer manuellement (deux terminaux séparés) :

```powershell
# Terminal 1 — Backend
cd backend
venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 — Frontend
cd frontend
npm install
npm run dev
```

### Étape 6 — Vérifier que tout fonctionne

- Frontend : `http://localhost:5173` → doit afficher Login ou Setup
- API Docs (Swagger) : `http://localhost:8000/docs` → utile pour tester les endpoints

---

## 3. Tâche Epic B — Page d'import de fichiers

Le backend est entièrement opérationnel et testé. Ta tâche est de créer la page `frontend/src/pages/Import.jsx` et de l'intégrer dans le dashboard.

**Flux :** Upload fichier → Mapper les colonnes → Lancer l'import → Rapport de résultat

### Endpoints API disponibles

> Tous les appels nécessitent le header `Authorization: Bearer <token>`.  
> Le token est stocké dans `localStorage` clé `access_token`.

| Méthode | Endpoint | Usage | Corps / réponse clés |
|---|---|---|---|
| POST | `/api/v1/imports/preview` | Upload du fichier, retourne les colonnes et un aperçu de 5 lignes. Rien n'est écrit en base. | FormData `file`. Réponse : `{ colonnes: string[], apercu: object[], nom_fichier }` |
| GET | `/api/v1/imports/mapping` | Récupère le mappage sauvegardé pour cette officine + la liste des champs cibles attendus. | Réponse : `{ champs_cibles: string[], mapping: { [champ]: colonne } }` |
| POST | `/api/v1/imports/mapping` | Sauvegarde le mappage sélectionné par l'utilisateur. | Body : `{ mapping: [{ champ_cible, colonne_source }] }` |
| POST | `/api/v1/imports/` | Import complet : upsert des références, remplacement des ventes. Peut durer quelques secondes sur un gros fichier. | FormData `file`. Réponse : `ImportLog { id, nom_fichier, statut, nb_lignes_ok, nb_lignes_erreur, created_at }` |
| GET | `/api/v1/imports/` | Historique des 20 derniers imports de l'officine. | Tableau de `ImportLog` |

### Étape 1 — Upload du fichier

Zone de dépôt (drag-and-drop) ou bouton "Choisir un fichier". Accepte `.xlsx`, `.xls`, `.csv` (jusqu'à 50 Mo).  
Appelle `POST /preview` dès que le fichier est sélectionné.

- Si succès : passer à l'étape 2 avec `colonnes` et `nom_fichier`
- Si erreur 422 : afficher le message `detail` retourné par l'API

### Étape 2 — Mappage des colonnes

Pour chaque champ cible du système, l'utilisateur choisit la colonne correspondante dans son fichier via un `<select>`.  
Charger le mappage existant avec `GET /mapping` pour pré-remplir les selects si un mappage a déjà été sauvegardé.

**Champs cibles à mapper :**

| Champ | Obligatoire | Description |
|---|---|---|
| `code` | **OUI** | Code article / CIP13 — identifiant unique de la référence |
| `designation` | **OUI** | Nom du médicament ou du produit |
| `stock_actuel` | **OUI** | Quantité en stock au moment de l'export |
| `vente_m1` | **OUI** | Ventes du mois le plus récent (M-1) |
| `forme` | non | Forme pharmaceutique (comprimé, sirop, etc.) |
| `prix_cession` | non | Prix grossiste hors taxes |
| `prix_public` | non | Prix public toutes taxes |
| `circuit` | non | Circuit de distribution (ex. OTC, prescription) |
| `vente_m2` … `vente_m12` | non | Ventes des 11 mois précédents |

Un bouton "Sauvegarder le mappage" appelle `POST /mapping` avant de passer à l'étape 3.  
Ce mappage est ensuite réutilisé automatiquement au prochain import.

### Étape 3 — Lancer l'import et afficher le résultat

Re-poster le même fichier en `POST /api/v1/imports/` (le backend relira le mappage sauvegardé).  
Afficher un indicateur de chargement (l'import peut durer quelques secondes).

- **Succès :** afficher une carte de résultat : nom du fichier, nb lignes OK (en vert), nb lignes erreur (en orange)
- **Erreurs de ligne :** si `nb_lignes_erreur > 0`, proposer un bouton "Voir les erreurs" qui affiche `erreurs_detail` dans un panneau déroulant
- **Erreur globale :** si le backend retourne 400 (pas de mappage) ou 422, afficher le message `detail` bien visible

### Historique des imports (sous la page)

Tableau des 20 derniers imports récupérés via `GET /api/v1/imports/`.

| Colonne | Détail |
|---|---|
| Date/heure | `created_at` formaté |
| Nom du fichier | `nom_fichier` |
| Statut | Badge vert si `succes`, badge orange/rouge si `erreur` |
| Lignes OK | `nb_lignes_ok` |
| Lignes erreur | `nb_lignes_erreur` |

### Arborescence à créer / modifier

```
frontend/src/
├── pages/
│   ├── Import.jsx          ← à créer (page principale)
│   └── ...
├── services/
│   ├── auth.js             ← déjà existant
│   └── imports.js          ← à créer (fonctions fetch pour l'API imports)
└── App.jsx                 ← ajouter la route /import (protégée)
```

> **Attention :** Ne pas créer de fichier `.env` dans le dépôt et ne pas committer `sad_officine.db`. Ces deux fichiers sont dans `.gitignore`.

---

*SAD OFFICINE · Séance 5 juillet 2026 · Prochaine étape : Epic C — paramètres fournisseurs & cycle de commande*
