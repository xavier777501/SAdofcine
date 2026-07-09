import logging
import smtplib
from email.message import EmailMessage

from app.core.config import settings

logger = logging.getLogger(__name__)


def send_password_reset_email(to_email: str, code: str) -> None:
    """
    Envoie le code de vérification pour réinitialiser le mot de passe.
    Si aucun SMTP n'est configuré (dev local), le code est simplement journalisé
    au lieu d'être envoyé, pour permettre de tester le flux sans serveur mail.
    """
    subject = "Votre code de réinitialisation StockAid"
    body = (
        "Bonjour,\n\n"
        "Voici votre code de vérification pour réinitialiser votre mot de passe StockAid :\n\n"
        f"    {code}\n\n"
        f"Ce code est valable {settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES} minutes.\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email : "
        "votre mot de passe actuel reste inchangé.\n"
    )

    if not settings.SMTP_HOST:
        logger.warning(
            "SMTP non configuré — code de réinitialisation (mode dev) pour %s : %s",
            to_email, code,
        )
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
