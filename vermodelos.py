import openai

# Configurar la clave de API de OpenAI
openai.api_key = "sk-proj-gEhFsVoB6XDOYhGsr0TNT3BlbkFJEmY7nMAoRFsgpjuA5cHE"

# Listar modelos disponibles
models = openai.Model.list()

# Imprimir los nombres de los modelos
for model in models['data']:
    print(model['id'])
