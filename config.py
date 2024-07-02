import os
import secrets
from dotenv import load_dotenv

load_dotenv()

class Config(object):

    SECRET_KEY = os.environ.get('SECRET_KEY') or 'default_secret_key'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:admin@localhost:5432/turismos'
    #SQLALCHEMY_DATABASE_URI = 'postgresql://turismo_xc5q_user:hICCI36xWvs6i68mNbk7rt9xtTBeItfy@dpg-coptj3tjm4es73abgusg-a.ohio-postgres.render.com/turismo_xc5q'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS') == 'True'
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL') == 'True'
    MAIL_USERNAME = os.environ.get('EMAIL_USER')
    MAIL_PASSWORD = os.environ.get('EMAIL_PASS')





