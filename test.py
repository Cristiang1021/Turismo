import os
import openai
from dotenv import load_dotenv

# Cargar las variables de entorno del archivo .env
load_dotenv()

# Obtener la clave API de las variables de entorno
openai.api_key = os.getenv("OPENAI_API_KEY")

# Puedes listar los modelos disponibles y ver cuál estás utilizando
def list_models():
    models = openai.Model.list()
    for model in models['data']:
        print(model['id'])

if __name__ == "__main__":
    list_models()
