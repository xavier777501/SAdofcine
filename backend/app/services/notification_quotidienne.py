"""
Notification quotidienne — section 7.2 du cahier des charges V9.

StockAid ne tourne que lorsqu'on l'ouvre (pas de serveur permanent) : un
envoi garanti à heure fixe même app fermée n'est pas possible. L'envoi est
donc opportuniste — déclenché au premier chargement du tableau de bord dans
la journée, une fois l'heure configurée passée, et jamais plus d'une fois
par jour.
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.officine import Officine
from app.models.parametre_officine import ParametreOfficine
from app.models.user import User
from app.services.alertes_strategiques import calculer_alertes_strategiques
from app.services.email import send_notification_quotidienne_email


def verifier_et_envoyer_notification_quotidienne(
    officine: Officine,
    params: ParametreOfficine,
    db: Session,
    maintenant: datetime | None = None,
) -> None:
    if not params.notification_active:
        return

    maintenant = maintenant or datetime.now()
    aujourdhui = maintenant.date()

    if params.notification_derniere_envoyee_le == aujourdhui:
        return

    heure_configuree = params.notification_heure or "08:00"
    try:
        heure_h, heure_m = (int(x) for x in heure_configuree.split(":"))
    except (ValueError, AttributeError):
        heure_h, heure_m = 8, 0
    if (maintenant.hour, maintenant.minute) < (heure_h, heure_m):
        return

    alertes = calculer_alertes_strategiques(officine.id, db)

    # Cahier des charges : "si X = 0, le message peut être omis ce jour-là" —
    # on marque quand même la date pour ne pas recalculer à chaque rechargement.
    if alertes["nb_references"] > 0:
        destinataire = params.notification_email
        if not destinataire:
            user = db.query(User).filter(User.officine_id == officine.id).first()
            destinataire = user.email if user else None
        if destinataire:
            send_notification_quotidienne_email(
                destinataire, alertes["nb_references"], alertes["ventes_perdues_totales_fcfa"],
            )

    params.notification_derniere_envoyee_le = aujourdhui
    db.commit()
