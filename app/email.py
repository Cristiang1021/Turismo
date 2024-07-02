from flask_mail import Message
from flask import url_for, render_template
from app import mail

def send_reset_email(user):
    token = user.get_reset_token()
    msg = Message('Solicitud para restablecer la contraseña',
                  sender='noreply@example.com',
                  recipients=[user.correo])
    url = url_for('main.reset_token', token=token, _external=True)
    msg.html = render_template('emails/reset_password_email.html', url=url)
    mail.send(msg)
