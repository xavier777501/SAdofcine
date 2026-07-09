"""
Parsing des fichiers d'import CSV/Excel.
Retourne un DataFrame brut + la liste des colonnes disponibles.
"""
import io
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


def parse_commande_logpharma(content: bytes) -> list[dict]:
    """
    Parse un export Logpharma "Listing de Produit à Commander".
    Format fixe (3 lignes d'en-tête, 3 dernières lignes = totaux) :
      Ligne 1 : nom officine, Ligne 2 : titre, Ligne 3 : en-têtes
    Retourne une liste de dicts {code, designation, stock_actuel, prix_cession, prix_public, circuit}.
    """
    try:
        df = pd.read_excel(io.BytesIO(content), header=2, dtype=str)
    except Exception as e:
        raise ValueError(f"Fichier Logpharma illisible : {e}") from e

    if len(df) < 4:
        raise ValueError("Fichier Logpharma trop court — vérifiez que c'est bien un export 'Listing de Produit à Commander'.")

    # Supprimer les 3 dernières lignes (totaux)
    df = df.iloc[:-3]

    COL_CODE    = "Code Prod"
    COL_DESIG   = "Désignation"
    COL_STOCK   = "Qté Sal."
    COL_PX_CES  = "Prix Ces."
    COL_PX_PUB  = "Prix Public"
    COL_CIRCUIT = "FOURNISSEUR"

    for col in [COL_CODE, COL_DESIG, COL_STOCK]:
        if col not in df.columns:
            raise ValueError(
                f"Colonne '{col}' introuvable dans le fichier. "
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

    lignes: list[dict] = []
    for _, row in df.iterrows():
        code = str(row.get(COL_CODE) or "").strip()
        if not code or code.lower() == "nan":
            continue

        stock = _to_float(row.get(COL_STOCK))
        if stock is None or stock < 0:
            stock = 0.0

        lignes.append({
            "code": code,
            "designation": str(row.get(COL_DESIG) or "").strip() or None,
            "stock_actuel": stock,
            "prix_cession": _to_float(row.get(COL_PX_CES)),
            "prix_public":  _to_float(row.get(COL_PX_PUB)),
            "circuit":      str(row.get(COL_CIRCUIT) or "").strip() or None,
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
