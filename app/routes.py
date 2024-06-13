import io
import logging
import os

import requests
from flask import Blueprint, render_template, flash, redirect, url_for, request, send_from_directory, jsonify, send_file
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf import csrf, CSRFProtect
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

import openai
import fitz  # PyMuPDF
from io import BytesIO

from . import db
from .forms import LoginForm, RegistrationForm, RecomendacionForm, RecomendacionForm
from .models import Usuario, ActividadTuristica, Categoria, ImagenActividad, RespuestasFormulario

main_bp = Blueprint('main', __name__)
openai.api_key = os.getenv('OPENAI_API_KEY')


def calcular_similitud(actividad, respuestas):
    similitud = 0

    if actividad.categoria.nombre.strip() == respuestas.pregunta1.strip():
        similitud += 1
    if actividad.nivel_dificultad.strip() == respuestas.pregunta2.strip():
        similitud += 1
    if actividad.nivel_fisico_requerido.strip() == respuestas.pregunta3.strip():
        similitud += 1
    if actividad.tiempo_promedio_duracion.strip() == respuestas.pregunta4.strip():
        similitud += 1
    if actividad.requerimiento_guia.strip() == respuestas.pregunta5.strip():
        similitud += 1
    if actividad.epoca_recomendada.strip() == respuestas.pregunta6.strip():
        similitud += 1

    # Comparación para el precio
    try:
        actividad_precio_min, actividad_precio_max = [int(x.replace('$', '').replace(',', '').strip()) for x in
                                                      actividad.precio_referencial.replace(' ', '').split('-')]
        if respuestas.pregunta7 == 'Menos de $50' and actividad_precio_max < 50:
            similitud += 1
        elif respuestas.pregunta7 == '$50-$100' and 50 <= actividad_precio_min <= 100:
            similitud += 1
        elif respuestas.pregunta7 == 'Más de $100' and actividad_precio_min > 100:
            similitud += 1
    except ValueError as e:
        print(f"Error al procesar el precio de la actividad {actividad.nombre}: {e}")

    return similitud


def obtener_recomendaciones(user_id):
    respuestas = RespuestasFormulario.query.filter_by(user_id=user_id).first()

    if not respuestas:
        return []

    actividades = ActividadTuristica.query.all()
    actividades_recomendadas = sorted(actividades, key=lambda actividad: calcular_similitud(actividad, respuestas),
                                      reverse=True)

    return actividades_recomendadas[:5]  # Retornar las 5 actividades con mayor similitud


@main_bp.route('/')
def index():
    categorias = Categoria.query.all()
    actividades = ActividadTuristica.query.all()
    recomendaciones = []
    form = None

    if current_user.is_authenticated:
        recomendaciones = obtener_recomendaciones(current_user.id)
        respuestas = RespuestasFormulario.query.filter_by(user_id=current_user.id).first()
        if not respuestas or request.args.get('new_user') == 'True':
            form = RecomendacionForm()

    return render_template('index.html', categorias=categorias, actividades=actividades, recomendaciones=recomendaciones, form=form)

@main_bp.route('/recomendaciones', methods=['GET', 'POST'])
@login_required
def recomendaciones():
    form = RecomendacionForm()
    respuestas = RespuestasFormulario.query.filter_by(user_id=current_user.id).first()

    if respuestas:
        recomendaciones = obtener_recomendaciones(current_user.id)
        return render_template('recomendaciones.html', respuestas=respuestas, recomendaciones=recomendaciones)

    if form.validate_on_submit():
        respuestas = RespuestasFormulario(
            pregunta1=form.pregunta1.data,
            pregunta2=form.pregunta2.data,
            pregunta3=form.pregunta3.data,
            pregunta4=form.pregunta4.data,
            pregunta5=form.pregunta5.data,
            pregunta6=form.pregunta6.data,
            pregunta7=form.pregunta7.data,
            user_id=current_user.id
        )
        db.session.add(respuestas)
        db.session.commit()
        flash('Respuestas guardadas correctamente', 'success')
        return redirect(url_for('main.recomendaciones'))

    return render_template('recomendaciones.html', form=form)



@main_bp.route('/logo1.png')
def serve_logo():
    return send_from_directory('', 'logo1.png')

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # Redirige al dashboard de admin si es admin, o a la página principal si no lo es
        return redirect(url_for('admin.dashboard')) if current_user.es_admin else redirect(url_for('main.index'))

    form = LoginForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(correo=form.correo.data).first()
        if user and user.check_password(form.contraseña.data):
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            # Redirige al dashboard de admin si es admin, o a la página principal si no lo es
            if user.es_admin:
                return redirect(next_page) if next_page else redirect(url_for('admin.dashboard'))
            else:
                return redirect(next_page) if next_page else redirect(url_for('main.index'))
        else:
            flash('No se ha podido iniciar sesión. Por favor revisa el correo electrónico y la contraseña', 'danger')
    return render_template('login.html', title='Login', form=form)


@main_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_pwd = generate_password_hash(form.contraseña.data)
        user = Usuario(nombre=form.nombre.data, correo=form.correo.data, contraseña_hash=hashed_pwd, es_admin=form.es_admin.data)
        db.session.add(user)
        try:
            db.session.commit()
            flash('¡Registro exitoso!', 'success')
            login_user(user)
            return redirect(url_for('main.recomendaciones'))  # Redirigir a la función recomendaciones
        except:
            db.session.rollback()
            flash('Error al registrar el usuario.', 'danger')
    return render_template('register.html', title='Registro', form=form)



@main_bp.route('/preferencias', methods=['GET', 'POST'])
@login_required
def preferencias():
    form = RecomendacionForm()
    if form.validate_on_submit():
        flash('Preferencias actualizadas.')
        return redirect(url_for('main.inicio'))
    return render_template('preferencias.html', form=form)


@main_bp.route('/inicio')
@login_required
def inicio():
    actividades_recomendadas = obtener_recomendaciones(current_user.id)
    return render_template('inicio.html', actividades=actividades_recomendadas)

@main_bp.route('/imagen_categoria/<int:id>')
def get_categoria_image(id):
    categoria = Categoria.query.get_or_404(id)
    if categoria.image_data:
        return send_file(io.BytesIO(categoria.image_data), mimetype=categoria.image_mimetype)
    else:
        return 'No image found', 404


@main_bp.route('/imagen_actividad/<int:id>')
def get_actividad_image(id):
    imagen = ImagenActividad.query.get_or_404(id)
    if imagen.data:
        return send_file(io.BytesIO(imagen.data), mimetype=imagen.mimetype)
    else:
        return 'No image found', 404

@main_bp.app_context_processor
def inject_categories():
    categorias = Categoria.query.all()
    return dict(categorias=categorias)

@main_bp.route('/actividades')
def actividades():
    try:
        actividades = ActividadTuristica.query.all()
        return render_template('actividades.html', actividades=actividades)
    except Exception as e:
        print(e)
        flash('Error al cargar las actividades.', 'danger')
        return redirect(url_for('main.index'))

@main_bp.route('/categoria/<int:categoria_id>')
def actividades_por_categoria(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    actividades = ActividadTuristica.query.filter_by(categoria_id=categoria.id).all()
    return render_template('actividades_por_categoria.html', categoria=categoria, actividades=actividades)

@main_bp.route('/profile')
@login_required
def profile():
    return render_template('perfil.html', user=current_user)



@main_bp.route('/cambiar_contraseña', methods=['GET', 'POST'])
@login_required
def cambiar_contraseña():
    # Lógica para cambiar la contraseña
    return render_template('cambiar_contraseña.html')



# Función para extraer texto del PDF desde una ruta local
def extract_text_from_pdf_local(pdf_path):
    try:
        document = fitz.open(pdf_path)
        text = ""
        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            text += page.get_text()
        return text
    except Exception as e:
        print(f"Error processing PDF: {e}")
        return "Error: Unable to process PDF."

# Ruta del PDF local
pdf_path = "C:/Users/andre/Desktop/U/tessis/18T00955.pdf"
pdf_text = extract_text_from_pdf_local(pdf_path)
print(f"Extracted PDF text: {pdf_text[:500]}...")  # Imprimir los primeros 500 caracteres para depuración

# Función para hacer consultas a gpt-3.5-turbo-16k
def query_gpt4(question, context, max_context_length=2000):
    # Limitar el tamaño del contexto
    if len(context) > max_context_length:
        context = context[:max_context_length]
    prompt = f"Context from the PDF:\n{context}\n\nQuestion: {question}\nAnswer:"
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",  # Cambia a gpt-3.5-turbo-16k
        messages=messages,
        max_tokens=150,
    )
    return response.choices[0].message["content"].strip()

# <><><><><><><> ASISTENTE VIRTUAL <><><><><><><> #
@main_bp.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(force=True)

    # Asegurar que 'queryResult' y 'action' existen
    query_result = req.get('queryResult', {})
    action = query_result.get('action', None)

    # Si no hay acción, devuelve un mensaje de error más informativo
    if not action:
        return jsonify(
            {"fulfillmentText": "No action provided in the request. Please check the action settings in Dialogflow."})

    # Manejar las acciones según lo configurado
    if action == 'consultar_actividades':
        categoria_nombre = query_result.get('parameters', {}).get('categoria', 'general')
        return consultar_actividades(categoria_nombre)
    elif action == 'dar_consejos':
        actividad_nombre = query_result.get('parameters', {}).get('actividad', None)
        return dar_consejos(actividad_nombre)
    elif action == 'pregunta_gpt4':
        question = query_result.get('queryText')
        context = pdf_text  # Utilizar el texto del PDF como contexto
        answer = query_gpt4(question, context)
        return jsonify({"fulfillmentText": answer})

    return jsonify({"fulfillmentText": "Action not handled by the webhook."})

def consultar_actividades(categoria_nombre):
    if categoria_nombre == 'general':
        actividades = ActividadTuristica.query.all()
        actividades_text = "\n ".join([actividad.nombre for actividad in actividades])
        response_text = f"Todas las actividades: {actividades_text}"
    else:
        categoria = Categoria.query.filter_by(nombre=categoria_nombre).first()
        if categoria and categoria.actividades:
            actividades = [actividad.nombre for actividad in categoria.actividades]
            actividades_text = "\n- ".join(actividades)
            response_text = f"Actividades en la categoría: {categoria_nombre}: {actividades_text}"
        else:
            response_text = f"No se han encontrado actividades en la categoría: {categoria_nombre}."
    return jsonify({"fulfillmentText": response_text})

def dar_consejos(actividad_nombre):
    actividad = ActividadTuristica.query.filter_by(nombre=actividad_nombre).first()
    if actividad:
        consejos = "Para participar en {}, se recomienda {}. Realizar durante {}, y el nivel de dificultad es {}.".format(
            actividad.nombre, actividad.requerimiento_guia, actividad.epoca_recomendada, actividad.nivel_dificultad)
        response_text = consejos
    else:
        response_text = "No se encontró información sobre esa actividad."
    return jsonify({"fulfillmentText": response_text})