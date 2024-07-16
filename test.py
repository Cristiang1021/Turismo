import os
from flask import Flask
from flask_mail import Mail, Message
from dotenv import load_dotenv

# Cargar variables del archivo .env
load_dotenv()

app = Flask(__name__)

# Configuración del servidor de correo
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT') or 587)
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS') == 'True'
app.config['MAIL_USE_SSL'] = os.environ.get('MAIL_USE_SSL') == 'True'
app.config['MAIL_USERNAME'] = os.environ.get('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.environ.get('EMAIL_PASS')

mail = Mail(app)

@app.route('/send_test_email')
def send_test_email():
    msg = Message('Test Email',
                  sender='noreply@example.com',
                  recipients=['cristiang1046@gmail.com'])  # Reemplaza con el correo del destinatario
    msg.body = 'This is a test email sent from Flask'
    try:
        mail.send(msg)
        return "Correo enviado correctamente."
    except Exception as e:
        return f"Error al enviar el correo: {str(e)}"

if __name__ == '__main__':
    app.run(debug=True, port='3001')
