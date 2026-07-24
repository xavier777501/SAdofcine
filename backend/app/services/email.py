import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to_email: str, subject: str, body: str) -> None:
    """
    Envoi générique d'un e-mail texte simple. Si aucun SMTP n'est configuré
    (dev local), le contenu est simplement journalisé au lieu d'être envoyé,
    pour permettre de tester les flux sans serveur mail.
    """
    if not settings.SMTP_HOST:
        logger.warning("SMTP non configuré — e-mail (mode dev) pour %s : %s\n%s", to_email, subject, body)
        return

    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = settings.SMTP_FROM
    message["To"] = to_email
    message.set_content(body)

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
        server.starttls()
        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(message)


def send_password_reset_email(to_email: str, code: str) -> None:
    """Envoie le code de vérification pour réinitialiser le mot de passe."""
    subject = "Votre code de réinitialisation StockAid"
    body = (
        "Bonjour,\n\n"
        "Voici votre code de vérification pour réinitialiser votre mot de passe StockAid :\n\n"
        f"    {code}\n\n"
        f"Ce code est valable {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email : "
        "votre mot de passe actuel reste inchangé.\n"
    )
    send_email(to_email, subject, body)


def send_notification_quotidienne_email(to_email: str, nb_references: int, ventes_perdues_fcfa: float) -> None:
    """
    Section 7.2 : reprend le contenu de l'encart 7.0 en une phrase, pour
    relancer le pharmacien sans qu'il ait besoin d'ouvrir StockAid.
    """
    subject = f"StockAid — {nb_references} référence(s) stratégique(s) en rupture ou critique"
    montant = f"{ventes_perdues_fcfa:,.0f}".replace(",", " ")
    body = (
        "Bonjour,\n\n"
        f"{nb_references} référence(s) classe A ou B sont actuellement en RUPTURE ou CRITIQUE, "
        f"pour une estimation de {montant} FCFA de ventes perdues sur cette période.\n\n"
        "Ouvrez StockAid pour voir le détail et préparer votre commande.\n"
    )
    send_email(to_email, subject, body)
