"""
Sections 6.3 (réappro continu) et 6.5 (commande périodique) du cahier des
charges : ce sont deux modes de réappro mutuellement exclusifs, pilotés par
le réglage cycle_commande_jours (0 = continu, 10/30 = décade/mensuel). La
quantité à commander affichée doit correspondre au mode choisi — pas toujours
à la quantité "cycle", même quand le pharmacien a réglé le mode continu.
"""
import pytest
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, Base, engine
from app.core.security import get_password_hash
from app.models.officine import Officine
from app.models.user import User
from app.models.reference import Reference
from app.models.vente_mensuelle import VenteMensuelle
from app.services.calcul_officine import (
    calculer_toutes_references,
    recalculer_apres_commande,
    get_or_create_parametres,
)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session():
    with Session(engine) as session:
        yield session


@pytest.fixture
def officine(db_session):
    o = Officine(nom="Pharmacie Test")
    db_session.add(o)
    db_session.commit()
    db_session.refresh(o)
    return o


def _creer_reference_avec_ventes(db_session, officine_id, stock_actuel=2):
    ref = Reference(
        officine_id=officine_id,
        code="REF1",
        designation="Doliprane 500mg",
        classe="A",
        ved="Essentiel",
        prix_cession=1000,
        stock_actuel=stock_actuel,
    )
    db_session.add(ref)
    db_session.flush()
    # Ventes variables pour garantir sigma > 0 (donc SS > 0, PC > 0).
    ventes = [8, 12, 10, 15, 9, 11, 14, 8, 10, 13, 9, 12]
    for i, qte in enumerate(ventes, start=1):
        db_session.add(VenteMensuelle(reference_id=ref.id, mois_index=i, quantite=qte))
    db_session.commit()
    db_session.refresh(ref)
    return ref


class TestModeContinu:
    def test_calcul_toutes_references_respecte_le_mode_continu(self, db_session, officine):
        ref = _creer_reference_avec_ventes(db_session, officine.id)
        params = get_or_create_parametres(officine.id, db_session)
        params.cycle_commande_jours = 0  # mode continu
        db_session.commit()

        calculer_toutes_references(officine.id, db_session)
        db_session.commit()
        db_session.refresh(ref)

        assert ref.qte_commander_continu is not None
        # En mode continu, la quantité affichée doit être celle du réappro
        # continu (PC + CMM - stock), pas celle du cycle périodique (S - stock).
        assert ref.qte_a_commander == ref.qte_commander_continu

    def test_calcul_toutes_references_respecte_le_mode_decade(self, db_session, officine):
        ref = _creer_reference_avec_ventes(db_session, officine.id)
        params = get_or_create_parametres(officine.id, db_session)
        params.cycle_commande_jours = 10  # décade
        db_session.commit()

        calculer_toutes_references(officine.id, db_session)
        db_session.commit()
        db_session.refresh(ref)

        # En mode décade, la quantité continue reste calculée (diagnostic)
        # mais n'est plus celle utilisée : les deux modes donnent des
        # quantités différentes pour ce jeu de données (stock sous PC).
        assert ref.qte_commander_continu is not None
        assert ref.qte_a_commander != ref.qte_commander_continu

    def test_meme_reference_change_de_quantite_selon_le_mode(self, db_session, officine):
        """Même stock, même historique : seule la quantité affichée doit changer avec le mode."""
        ref = _creer_reference_avec_ventes(db_session, officine.id)
        params = get_or_create_parametres(officine.id, db_session)

        params.cycle_commande_jours = 0
        db_session.commit()
        calculer_toutes_references(officine.id, db_session)
        db_session.commit()
        db_session.refresh(ref)
        qte_mode_continu = ref.qte_a_commander

        params.cycle_commande_jours = 30
        db_session.commit()
        calculer_toutes_references(officine.id, db_session)
        db_session.commit()
        db_session.refresh(ref)
        qte_mode_mensuel = ref.qte_a_commander

        assert qte_mode_continu != qte_mode_mensuel

    def test_recalcul_apres_commande_respecte_le_mode_continu(self, db_session, officine):
        ref = _creer_reference_avec_ventes(db_session, officine.id)
        params = get_or_create_parametres(officine.id, db_session)
        params.cycle_commande_jours = 0
        db_session.commit()

        # Premier calcul complet (import historique), puis un import de
        # commande (Type 2) qui ne touche que le stock et déclenche le
        # recalcul léger — doit rester cohérent avec le mode continu.
        calculer_toutes_references(officine.id, db_session)
        db_session.commit()

        ref.stock_actuel = 3
        db_session.commit()

        recalculer_apres_commande(officine.id, db_session)
        db_session.commit()
        db_session.refresh(ref)

        assert ref.qte_a_commander == ref.qte_commander_continu
