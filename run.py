from app import create_app, db
from flask_migrate import Migrate, upgrade


app = create_app()


# Asocia Flask-Migrate con la app y la base de datos
migrate = Migrate(app, db)

# Crear las tablas en la base de datos
with app.app_context():
    upgrade()



if __name__ == "__main__":
    app.run(debug=True, port=3000)


