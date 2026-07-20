from sqlalchemy import Column, Float, Integer, Boolean, ForeignKey, Uuid
from app.models.base import BaseModel


class ParametreOfficine(BaseModel):
    """
    Paramètres globaux de l'officine utilisés par le moteur SAD.
    Créés automatiquement avec des valeurs par défaut au premier import.
    Modifiables via Epic C (page Réglages).
    """
    __tablename__ = "parametres_officine"

    officine_id = Column(
        Uuid(as_uuid=True),
        ForeignKey("officines.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    # Délais fournisseurs (jours) — affinés par circuit en Epic C
    dl_moy_jours = Column(Integer, nullable=False, default=7)
    dl_max_jours = Column(Integer, nullable=False, default=15)

    # Cycle de commande T (jours) : 10=décade, 30=mensuel — seuls rythmes avec
    # une formule de quantité définie au cahier des charges (section 6.5).
    cycle_commande_jours = Column(Integer, nullable=False, default=10)

    # Paramètres EOQ
    cout_commande = Column(Float, nullable=False, default=5000.0)   # FCFA par commande
    taux_detention = Column(Float, nullable=False, default=0.20)    # 20 % annuel

    # Niveaux de service visés par statut VED (0-1), pilotent le facteur Z
    # via INV.NORMALE.STANDARD — section 6.6 du cahier des charges.
    # Valeurs par défaut : Vital 99 %, Essentiel 95 %, Désirable 90 %, Non renseigné 95 %.
    niveau_service_vital          = Column(Float, nullable=False, default=0.99)
    niveau_service_essentiel      = Column(Float, nullable=False, default=0.95)
    niveau_service_desirable      = Column(Float, nullable=False, default=0.90)
    niveau_service_non_renseigne  = Column(Float, nullable=False, default=0.95)

    # Plafond budgétaire de commande (FCFA), optionnel — section 6.7 du cahier
    # des charges. None/vide = pas de restriction, toutes les références
    # recommandées sont affichées sans limite.
    plafond_commande_fcfa = Column(Float, nullable=True, default=None)

    # Mode de commande "ciblée sur l'import" (section 4ter du cahier des
    # charges) : quand actif, la liste d'action et le plafond ne portent que
    # sur les références présentes dans le dernier import de commande (Type
    # 2), au lieu de l'historique complet. L'encart 7.0 n'est jamais concerné.
    mode_commande_ciblee = Column(Boolean, nullable=False, default=False)
