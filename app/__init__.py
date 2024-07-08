import os
from flask import Flask, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from flask_wtf.csrf import CSRFProtect
from flask_cors import CORS

# Inicializa las extensiones globales sin una aplicación específica
db = SQLAlchemy()
mail = Mail()
bcrypt = Bcrypt()
login_manager = LoginManager()
login_manager.login_view = 'main.login'  # Ajusta según el endpoint de login
migrate = Migrate()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializa las extensiones con la aplicación creada
    db.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf = CSRFProtect(app)

    # Importa y registra los blueprints
    from app.admin.routes import admin_bp  # Importa el blueprint de administración
    app.register_blueprint(admin_bp)

    # Si tienes un blueprint para las rutas principales, asegúrate de importarlo y registrar aquí
    from app.routes import main_bp, webhook
    app.register_blueprint(main_bp)
    csrf.exempt(webhook)

    # Importación de modelos y otras configuraciones necesarias
    from app import models

    # User loader para Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        from app.models import Usuario
        return Usuario.query.get(int(user_id))

    return app
