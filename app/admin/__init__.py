# admin/__init__.py

from flask import Blueprint

admin_bp = Blueprint('admin', __name__, template_folder='../templates/admin', url_prefix='/admin')




# No olvides importar tus rutas después de definir el blueprint para evitar problemas de dependencias circulares
from . import routes
