import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings
from core.logger import logger


async def send_email(to_email: str, subject: str, body_html: str) -> bool:
    if not settings.SMTP_HOST:
        logger.warning(f"SMTP no configurado. No se envió email a {to_email}: {subject}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body_html, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

        logger.info(f"Email enviado a {to_email}: {subject}")
        return True
    except Exception as e:
        logger.error(f"Error al enviar email a {to_email}: {str(e)}")
        return False


async def notify_account_locked(to_email: str, username: str, lock_minutes: int) -> bool:
    subject = "Alerta de Seguridad - Cuenta Bloqueada Temporalmente"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Actividad Sospechosa Detectada</h2>
        <p>Hola <strong>{username}</strong>,</p>
        <p>Se ha detectado múltiples intentos fallidos de inicio de sesión en tu cuenta.</p>
        <p>Por seguridad, tu cuenta ha sido <strong>bloqueada temporalmente</strong> durante <strong>{lock_minutes} minutos</strong>.</p>
        <p>Pasado ese tiempo, podrás intentar iniciar sesión nuevamente de forma automática.</p>
        <p>Si no reconoces esta actividad, contacta al administrador del sistema.</p>
        <hr>
        <p style="color: #666; font-size: 12px;">Este es un mensaje automático de seguridad. Por favor no respondas a este correo.</p>
    </body>
    </html>
    """
    return await send_email(to_email, subject, body)


async def notify_password_reset(to_email: str, username: str, reset_token: str) -> bool:
    subject = "Restablecimiento de Contraseña"
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2>Restablecimiento de Contraseña</h2>
        <p>Hola <strong>{username}</strong>,</p>
        <p>Has solicitado restablecer tu contraseña. Haz clic en el siguiente enlace o usa el token para completar el proceso:</p>
        <p><a href="{reset_url}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Restablecer Contraseña</a></p>
        <p><strong>Token:</strong> {reset_token}</p>
        <p>Este enlace y token expirarán en <strong>10 minutos</strong> y son de un solo uso.</p>
        <p>Si no solicitaste este cambio, ignora este mensaje.</p>
        <hr>
        <p style="color: #666; font-size: 12px;">Este es un mensaje automático de seguridad. Por favor no respondas a este correo.</p>
    </body>
    </html>
    """
    return await send_email(to_email, subject, body)
