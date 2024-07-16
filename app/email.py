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

def send_recommendation_email(email, activities):
    msg = Message('Recomendaciones de Actividades',
                  sender='noreply@example.com',
                  recipients=[email])
    msg.html = render_template('emails/recommendation_email.html', activities=activities)
    try:
        mail.send(msg)
        print("Correo enviado correctamente.")
    except Exception as e:
        print(f"Error al enviar el correo: {str(e)}")
