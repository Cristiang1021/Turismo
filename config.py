import os
from dotenv import load_dotenv
class Config(object):
    SECRET_KEY = 'alo'
    SQLALCHEMY_DATABASE_URI = 'postgresql://postgres:admin@localhost:5432/turismos'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = os.path.join(os.getcwd(), 'app', 'static', 'uploads')
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}



