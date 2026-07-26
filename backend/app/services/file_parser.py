"""
Parsing des fichiers d'import CSV/Excel/RTF.
Retourne un DataFrame brut + la liste des colonnes disponibles.
"""
import io
import re
from typing import Optional
import pandas as pd


CHAMPS_CIBLES = [
    "code",
    "designation",
    "forme",
    "prix_cession",
    "prix_public",
    "stock_actuel",
    "circuit",
    "vente_m1",
    "vente_m2",
    "vente_m3",
    "vente_m4",
    "vente_m5",
    "vente_m6",
    "vente_m7",
    "vente_m8",
    "vente_m9",
    "vente_m10",
    "vente_m11",
    "vente_m12",
]

CHAMPS_OBLIGATOIRES = {"code", "designation", "stock_actuel", "vente_m1"}


def parse_file(content: bytes, filename: str) -> pd.DataFrame:
    """
    Lit un fichier CSV ou XLSX et retourne un DataFrame brut.
    Lève ValueError si le format est illisible.
    """
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    try:
        if ext == "csv":
            for sep in [";", ",", "\t"]:
                try:
                    df = pd.read_csv(io.BytesIO(content), sep=sep, dtype=str)
                    if len(df.columns) > 1:
                        return df
                except Exception:
                    continue
            raise ValueError("Impossible de lire le CSV (séparateur non reconnu).")

        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(io.BytesIO(content), dtype=str)
            return df

        else:
            raise ValueError(f"Format non supporté : .{ext}. Utilisez .csv ou .xlsx")

    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Fichier illisible : {e}") from e


def get_columns(df: pd.DataFrame) -> list[str]:
    """Retourne la liste des colonnes du DataFrame."""
    return [str(c).strip() for c in df.columns if str(c).strip()]


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str]) -> tuple[list[dict], list[dict]]:
    """
    Applique le mappage {champ_cible: colonne_source} sur le DataFrame.

    Retourne:
        - lignes_ok  : liste de dicts normalisés prêts à insérer en base
        - lignes_err : liste de dicts {ligne, raison} pour le rapport d'erreur
    """
    lignes_ok = []
    lignes_err = []

    # Vérifier que les colonnes mappées existent dans le fichier
    for champ, col in mapping.items():
        if col and col not in df.columns:
            raise ValueError(f"Colonne '{col}' introuvable dans le fichier (champ : {champ}).")

    for idx, row in df.iterrows():
        numero_ligne = int(idx) + 2  # +2 car l'index commence à 0 et la ligne 1 est l'en-tête

        try:
            record: dict = {}

            for champ in CHAMPS_CIBLES:
                col_source = mapping.get(champ)
                if not col_source:
                    record[champ] = None
                    continue
                val = row.get(col_source)
                record[champ] = _coerce(champ, val)

            # Vérification des champs obligatoires
            missing = [c for c in CHAMPS_OBLIGATOIRES if not record.get(c) and record.get(c) != 0]
            if missing:
                raise ValueError(f"Champs obligatoires manquants : {', '.join(missing)}")

            lignes_ok.append(record)

        except Exception as e:
            lignes_err.append({"ligne": numero_ligne, "raison": str(e)})

    return lignes_ok, lignes_err


def _normaliser_entete(valeur) -> str:
    """
    Normalise un en-tête de colonne pour la comparaison : les en-têtes réels
    de Logpharma contiennent des retours à la ligne et des espaces irréguliers
    au milieu des mots (ex: "Prix \nPublic", "FOUR-\nNISEUR") selon la largeur
    de colonne au moment de l'export. On ignore espaces/retours à la
    ligne/tirets et on met en majuscules pour comparer de façon fiable.
    """
    return re.sub(r"[\s\-]+", "", str(valeur)).upper()


# Noms de colonnes normalisés tels qu'observés dans le vrai fichier
# LOGPHARMA_EXPORT_TEST_FICTIF.xlsx (voir _normaliser_entete ci-dessus pour
# la raison des variantes avec espaces/tirets/retours à la ligne).
_COLONNES_LOGPHARMA = {
    "code":            "CODEPROD",
    "designation":     "DÉSIGNATION",
    "stock_actuel":    "QTÉSAL.",
    "reserve":         "RÉSERVE",
    "sorties_periode": "SORTIES",
    "prix_cession":    "PRIXCES.",
    "prix_public":     "PRIXPUBLIC",
    "circuit":         "FOURNISEUR",  # orthographe réelle de Logpharma (une seule S)
}

# Colonnes qui, si absentes du fichier (anciens exports, ou colonne "Réserve"
# non activée côté officine), ne doivent jamais faire échouer l'import — au
# contraire de code/désignation/stock_actuel qui restent obligatoires.
_COLONNES_OPTIONNELLES = {"reserve"}


def parse_commande_logpharma(content: bytes) -> list[dict]:
    """
    Parse un export Logpharma "Listing de Produit à Commander".
    Format fixe (3 lignes d'en-tête, 3 dernières lignes = totaux) :
      Ligne 1 : nom officine, Ligne 2 : titre, Ligne 3 : en-têtes
    Retourne une liste de dicts {code, designation, stock_actuel, reserve,
    sorties_periode, prix_cession, prix_public, circuit}. `stock_actuel` est
    ici uniquement la colonne "Qté Sal." — c'est à l'appelant d'ajouter
    `reserve` pour obtenir le stock actuel total (section 4bis, V9).
    """
    try:
        df = pd.read_excel(io.BytesIO(content), header=2, dtype=str)
    except Exception as e:
        raise ValueError(f"Fichier Logpharma illisible : {e}") from e

    if len(df) < 4:
        raise ValueError("Fichier Logpharma trop court — vérifiez que c'est bien un export 'Listing de Produit à Commander'.")

    # Supprimer les 3 dernières lignes (totaux)
    df = df.iloc[:-3]

    # Colonne réelle du fichier ↔ champ cible, via en-têtes normalisés
    colonnes_par_entete_normalise = {_normaliser_entete(col): col for col in df.columns}
    colonne_reelle = {
        champ: colonnes_par_entete_normalise.get(entete_attendu)
        for champ, entete_attendu in _COLONNES_LOGPHARMA.items()
    }

    for champ in ("code", "designation", "stock_actuel"):
        if colonne_reelle.get(champ) is None:
            raise ValueError(
                f"Colonne '{_COLONNES_LOGPHARMA[champ]}' introuvable dans le fichier. "
                "Vérifiez que c'est bien un export Logpharma 'Listing de Produit à Commander'."
            )

    def _to_float(val) -> Optional[float]:
        if val is None:
            return None
        s = str(val).strip().replace(" ", "").replace("\xa0", "")
        if s in ("", "nan", "NaN", "-", "N/A"):
            return None
        try:
            return float(s.replace(",", "."))
        except ValueError:
            return None

    def _valeur(row, champ):
        col = colonne_reelle.get(champ)
        if not col:
            return None
        val = row.get(col)
        if val is None or (isinstance(val, float) and pd.isna(val)):
            return None
        if isinstance(val, str) and val.strip().lower() in ("nan", ""):
            return None
        return val

    lignes: list[dict] = []
    for _, row in df.iterrows():
        code = str(_valeur(row, "code") or "").strip()
        if not code or code.lower() == "nan":
            continue

        stock = _to_float(_valeur(row, "stock_actuel"))
        if stock is None or stock < 0:
            stock = 0.0

        # Section 4bis (V9) : certaines officines gardent une partie du stock
        # en réserve, hors rayon — l'ignorer ferait recommander un produit
        # déjà disponible. Colonne optionnelle : absente => 0, jamais d'erreur.
        reserve = _to_float(_valeur(row, "reserve")) or 0.0
        if reserve < 0:
            reserve = 0.0

        lignes.append({
            "code": code,
            "designation": str(_valeur(row, "designation") or "").strip() or None,
            "stock_actuel": stock,
            "reserve": reserve,
            "sorties_periode": _to_float(_valeur(row, "sorties_periode")) or 0.0,
            "prix_cession": _to_float(_valeur(row, "prix_cession")),
            "prix_public":  _to_float(_valeur(row, "prix_public")),
            "circuit":      str(_valeur(row, "circuit") or "").strip() or None,
        })

    if not lignes:
        raise ValueError("Aucun produit trouvé dans le fichier Logpharma.")

    return lignes


def _coerce(champ: str, valeur):
    """Convertit une valeur brute vers le bon type selon le champ cible."""
    if valeur is None or (isinstance(valeur, float) and pd.isna(valeur)):
        return None
    if isinstance(valeur, str) and valeur.strip() in ("", "nan", "NaN", "-", "N/A"):
        return None

    champs_numeriques = {
        "prix_cession", "prix_public", "stock_actuel",
        "vente_m1", "vente_m2", "vente_m3", "vente_m4",
        "vente_m5", "vente_m6", "vente_m7", "vente_m8",
        "vente_m9", "vente_m10", "vente_m11", "vente_m12",
    }

    if champ in champs_numeriques:
        try:
            # Nettoyer les formats locaux : 1.234,56 → 1234.56
            s = str(valeur).replace(" ", "").replace("\xa0", "")
            if "," in s and "." in s:
                s = s.replace(".", "").replace(",", ".")
            elif "," in s:
                s = s.replace(",", ".")
            val = float(s)
            # Les ventes négatives (retours) → 0
            if champ.startswith("vente_") and val < 0:
                val = 0.0
            return val
        except (ValueError, TypeError):
            raise ValueError(f"Valeur non numérique pour '{champ}' : {valeur!r}")

    return str(valeur).strip()


# ─────────────────────────────────────────────────────────────────────────────
# Import Type 3 — bon de livraison / réception fournisseur (section 4quater)
#
# Logpharma génère ce document au format RTF (habillé en .doc/.docx à
# l'enregistrement), pas en Word natif (OOXML) — donc pas de python-docx ici,
# un parseur RTF texte suffit et évite une dépendance supplémentaire.
# Structure validée sur un fichier réel fourni par le client : un en-tête
# (nom officine, "FACT. DU FOURNIS. : X", "FACTURE OU B.L. N° X du DATE"),
# un tableau à 12 colonnes (N° Ligne, Code, Désignation, Qté livrée,
# Stock Init, Stock Fin., Prix Ces., Prix Pub, Montant Ligne, Lieu, Heure,
# Marge — "Peix Ces." dans le fichier réel, faute de frappe du modèle
# Logpharma lui-même, comme "FOURNISEUR" pour le Type 2), puis un pied de
# page "Nombre de lignes : N".
# ─────────────────────────────────────────────────────────────────────────────

def _decoder_bytes_rtf(content: bytes) -> str:
    """RTF Windows classique : UTF-8 si le fichier a été réenregistré ainsi,
    sinon repli sur cp1252 (codepage ANSI par défaut de Logpharma/Windows)."""
    for encodage in ("utf-8", "cp1252"):
        try:
            return content.decode(encodage)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", errors="replace")


def _decoder_echappement_rtf(texte: str) -> str:
    """Décode les échappements hexadécimaux standards du RTF (\\'e9 = é en
    cp1252) — le fichier de test fourni n'en contient pas (accents en UTF-8
    direct), mais un vrai export Logpharma pourrait suivre la convention RTF
    classique ; on gère les deux sans supposer laquelle sera utilisée."""
    def _remplacer(m):
        return bytes([int(m.group(1), 16)]).decode("cp1252", errors="replace")
    return re.sub(r"\\'([0-9a-fA-F]{2})", _remplacer, texte)


def _cellules_rtf(segment: str) -> list[str]:
    """Découpe un segment de ligne de tableau RTF (entre deux \\row) en texte
    de cellule, en retirant tous les mots de contrôle RTF."""
    morceaux = re.split(r"\\(?:nest)?cell(?![a-zA-Z])", segment)
    cellules = []
    for morceau in morceaux:
        texte = re.sub(r"\\par(?![a-zA-Z])", " ", morceau)
        # \cellx1234 = position de bordure, jamais du contenu — à distinguer
        # de \cell (fin de cellule) traité juste au-dessus.
        texte = re.sub(r"\\cellx\d+", " ", texte)
        texte = re.sub(r"\{[^{}]*\}", "", texte)
        texte = re.sub(r"\\[a-zA-Z]+-?\d*\s?", " ", texte)
        texte = re.sub(r"[{}]", "", texte)
        texte = re.sub(r"\s+", " ", texte).strip()
        if texte:
            cellules.append(texte)
    return cellules


def _to_float_fr(val: Optional[str]) -> Optional[float]:
    if val is None:
        return None
    s = str(val).strip().replace(" ", "").replace("\xa0", "")
    if s in ("", "nan", "NaN", "-", "N/A"):
        return None
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def parse_reception_logpharma(content: bytes) -> dict:
    """
    Parse un bon de livraison/réception fournisseur Logpharma (Type 3,
    section 4quater). Retourne :
      {"fournisseur": str | None, "bl_numero": str | None, "bl_date": str | None,
       "lignes": [{"code", "designation", "qte_livree", "stock_init",
                   "stock_fin", "prix_cession", "prix_public"}]}
    Ne calcule rien d'autre : c'est à l'appelant de remplacer stock_actuel
    par stock_fin, sans jamais toucher CMM/sigma/ABC/FSN/VED (section 4quater).
    """
    try:
        texte = _decoder_bytes_rtf(content)
    except Exception as e:
        raise ValueError(f"Fichier illisible : {e}") from e

    texte = _decoder_echappement_rtf(texte)
    texte_sans_nested = re.sub(r"\{\\\*\\nesttableprops.*?\\nestrow\}", "", texte, flags=re.DOTALL)

    fournisseur = None
    m = re.search(r"FOURNIS\.\s*:\s*([^\\{}]+?)\\nestcell", texte_sans_nested)
    if m:
        fournisseur = m.group(1).strip() or None

    bl_numero = bl_date = None
    m2 = re.search(r"FACTURE OU B\.L\.\s*N°\s*([^\s]+)\s*du\s*([^\\{}]+?)\\nestcell", texte_sans_nested)
    if m2:
        bl_numero = m2.group(1).strip() or None
        bl_date = m2.group(2).strip() or None

    segments = re.split(r"\\row", texte_sans_nested)
    lignes_cellules = [_cellules_rtf(s) for s in segments]

    entete_idx = next(
        (i for i, c in enumerate(lignes_cellules) if any("Ligne" in x for x in c) and "Code" in c),
        None,
    )
    if entete_idx is None:
        raise ValueError(
            "En-tête du tableau introuvable — vérifiez que c'est bien un bon de "
            "livraison/réception Logpharma (format RTF)."
        )

    lignes: list[dict] = []
    for cellules in lignes_cellules[entete_idx + 1:]:
        if any("Nombre de lignes" in c for c in cellules):
            break
        # 12 colonnes attendues ; on tolère des lignes légèrement écourtées
        # tant que les 8 premières colonnes (jusqu'à Prix Pub) sont présentes.
        if len(cellules) < 8:
            continue
        code = cellules[1].strip()
        if not code or code.lower() == "nan":
            continue
        lignes.append({
            "code": code,
            "designation": cellules[2].strip() or None,
            "qte_livree": _to_float_fr(cellules[3]),
            "stock_init": _to_float_fr(cellules[4]),
            "stock_fin": _to_float_fr(cellules[5]),
            "prix_cession": _to_float_fr(cellules[6]),
            "prix_public": _to_float_fr(cellules[7]),
        })

    if not lignes:
        raise ValueError("Aucune ligne de livraison trouvée dans le fichier.")

    return {
        "fournisseur": fournisseur,
        "bl_numero": bl_numero,
        "bl_date": bl_date,
        "lignes": lignes,
    }
