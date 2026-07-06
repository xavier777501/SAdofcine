from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID


class MappingItem(BaseModel):
    champ_cible: str
    colonne_source: str


class MappingSave(BaseModel):
    mapping: list[MappingItem]


class ImportLogOut(BaseModel):
    id: UUID
    nom_fichier: str
    statut: str
    nb_lignes_total: Optional[int]
    nb_lignes_ok: Optional[int]
    nb_lignes_erreur: Optional[int]
    erreurs_detail: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
