from app import db, create_app
from sqlalchemy import Column, Integer, LargeBinary, String

class SimpleBinaryTest(db.Model):
    id = Column(Integer, primary_key=True)
    data = Column(LargeBinary)
    name = Column(String(50))

app = create_app()

with app.app_context():
    # Crear la tabla para la prueba
    db.create_all()

    # Lee la imagen
    with open(r'C:\Users\andre\Pictures\Screenshots\Captura de pantalla 2023-04-09 220957.png', 'rb') as file:
        image_data = file.read()

    # Crea una nueva entrada de prueba
    simple_test = SimpleBinaryTest(
        name='Test Entry',
        data=image_data
    )

    # Añade la entrada a la sesión y commit
    db.session.add(simple_test)
    db.session.commit()

    # Verifica que la entrada se haya guardado correctamente
    test_entry = SimpleBinaryTest.query.get(simple_test.id)
    print(f"Test Entry after direct commit: {test_entry}, Data Length: {len(test_entry.data) if test_entry.data else 0}")
