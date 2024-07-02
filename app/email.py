from flask_mail import Message
from flask import url_for, current_app, render_template
from app import mail


def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Solicitud para restablecer la contraseña',
                  sender=current_app.config['MAIL_USERNAME'],
                  recipients=[user.correo])

    # Renderiza la plantilla HTML
    html_body = render_template('emails/reset_password_email.html', token=token)

    # Define el cuerpo del mensaje
    msg.body = f'''Para restablecer su contraseña, visite el siguiente enlace:
{url_for('main.reset_token', token=token, _external=True)}
Si no solicitó este cambio, simplemente ignore este correo y no se realizarán cambios.
'''
    msg.html = html_body

    mail.send(msg)
