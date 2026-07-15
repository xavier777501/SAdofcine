"""
Parsing des fichiers d'import CSV/Excel.
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
    "sorties_periode": "SORTIES",
    "prix_cession":    "PRIXCES.",
    "prix_public":     "PRIXPUBLIC",
    "circuit":         "FOURNISEUR",  # orthographe réelle de Logpharma (une seule S)
}


def parse_commande_logpharma(content: bytes) -> list[dict]:
    """
    Parse un export Logpharma "Listing de Produit à Commander".
    Format fixe (3 lignes d'en-tête, 3 dernières lignes = totaux) :
      Ligne 1 : nom officine, Ligne 2 : titre, Ligne 3 : en-têtes
    Retourne une liste de dicts {code, designation, stock_actuel, sorties_periode, prix_cession, prix_public, circuit}.
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

        lignes.append({
            "code": code,
            "designation": str(_valeur(row, "designation") or "").strip() or None,
            "stock_actuel": stock,
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
