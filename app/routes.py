import datetime
import io
import logging
import os

import requests
from flask import Blueprint, render_template, flash, redirect, url_for, request, send_from_directory, jsonify, \
    send_file, make_response
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf import csrf, CSRFProtect
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

import openai
import fitz  # PyMuPDF
from io import BytesIO

from werkzeug.utils import secure_filename

from . import db
from .email import send_reset_email
from .forms import LoginForm, RegistrationForm, RecomendacionForm, \
    RegistroVisitaForm, EditarRespuestasForm, RequestResetForm, ResetPasswordForm
from .models import Usuario, ActividadTuristica, Categoria, ImagenActividad, RespuestasFormulario, Visita, FotoVisita

main_bp = Blueprint('main', __name__)
openai.api_key = os.environ.get('OPENAI_API_KEY')


from decimal import Decimal

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
    actividad_precio = actividad.precio_referencial

    if respuestas.pregunta7 == 'Menos de $50' and actividad_precio < Decimal('50.00'):
        similitud += 1
    elif respuestas.pregunta7 == '$50-$100' and Decimal('50.00') <= actividad_precio <= Decimal('100.00'):
        similitud += 1
    elif respuestas.pregunta7 == 'Más de $100' and actividad_precio > Decimal('100.00'):
        similitud += 1

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


@main_bp.route('/baner.png')
def serve_baner():
    return send_from_directory('', 'image.jpg')

@main_bp.route('/recom.png')
def serve_recom():
    return send_from_directory('', 'recomendaciones.jpg')

@main_bp.route('/visita.png')
def serve_visita():
    return send_from_directory('', 'visita.jpg')

@main_bp.route('/Usuario.png')
def serve_pref():
    return send_from_directory('', 'Usuario.jpg')


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
        except IntegrityError:
            db.session.rollback()
            flash('El correo ya está en uso. Por favor, elige un correo diferente.', 'danger')
        except Exception as e:
            db.session.rollback()
            flash('Error al registrar el usuario.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en {getattr(form, field).label.text}: {error}", 'danger')
    return render_template('register.html', title='Registro', form=form)

@main_bp.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    user = Usuario.verify_reset_token(token)
    if user is None:
        flash('El token es inválido o ha expirado', 'warning')
        return redirect(url_for('main.token_expired'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.password = form.contraseña.data
        db.session.commit()
        flash('Su contraseña ha sido actualizada. ¡Ahora puede iniciar sesión!', 'success')
        return redirect(url_for('main.login'))
    return render_template('reset_token.html', title='Restablecer Contraseña', form=form, token=token)

@main_bp.route("/token_expired")
def token_expired():
    return render_template('token_expired.html', title='Token Expirado')

@main_bp.route('/reset_request', methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    form = RequestResetForm()
    if form.validate_on_submit():
        user = Usuario.query.filter_by(correo=form.correo.data).first()
        if user:
            send_reset_email(user)
        flash('Si el correo está registrado, se le enviará un enlace para restablecer su contraseña.', 'info')
        return redirect(url_for('main.login'))
    return render_template('reset_request.html', title='Solicitar Restablecimiento de Contraseña', form=form)





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


@main_bp.route('/actividades', methods=['GET'])
def actividades():
    categoria_id = request.args.get('categoria')
    nivel_dificultad = request.args.get('nivel_dificultad')
    precio_minimo = request.args.get('precio_minimo')

    actividades = ActividadTuristica.query

    if categoria_id:
        actividades = actividades.filter_by(categoria_id=categoria_id)

    if nivel_dificultad:
        actividades = actividades.filter_by(nivel_dificultad=nivel_dificultad)

    if precio_minimo:
        actividades = actividades.filter(ActividadTuristica.precio_referencial >= float(precio_minimo))

    actividades = actividades.all()

    return render_template('actividades.html', actividades=actividades, categorias=Categoria.query.all())


@main_bp.route('/categoria/<int:categoria_id>')
def actividades_por_categoria(categoria_id):
    categoria = Categoria.query.get_or_404(categoria_id)
    nivel_dificultad = request.args.get('nivel_dificultad')
    precio_minimo = request.args.get('precio_minimo')
    filtro_categoria = request.args.get('categoria')

    actividades = ActividadTuristica.query.filter_by(categoria_id=categoria_id)

    if nivel_dificultad:
        actividades = actividades.filter_by(nivel_dificultad=nivel_dificultad)

    if precio_minimo:
        actividades = actividades.filter(ActividadTuristica.precio_referencial >= float(precio_minimo))

    if filtro_categoria:
        actividades = actividades.filter_by(categoria_id=filtro_categoria)

    actividades = actividades.all()

    return render_template('actividades_por_categoria.html', categoria=categoria, actividades=actividades,
                           categorias=Categoria.query.all())

@main_bp.route('/profile')
@login_required
def profile():
    return render_template('perfil.html', user=current_user)



@main_bp.route('/cambiar_contraseña', methods=['GET', 'POST'])
@login_required
def cambiar_contraseña():
    # Lógica para cambiar la contraseña
    return render_template('cambiar_contraseña.html')


@main_bp.route('/actividad/<int:id>', methods=['GET', 'POST'])
def ver_actividad(id):
    actividad = ActividadTuristica.query.get_or_404(id)
    visitas = Visita.query.filter_by(actividad_id=id).all()
    fotos_visitas = FotoVisita.query.join(Visita).filter(Visita.actividad_id == id).all()
    form = RegistroVisitaForm()
    form.actividad_id.choices = [(actividad.id, actividad.nombre)]

    if form.validate_on_submit() and current_user.is_authenticated:
        visita = Visita(
            user_id=current_user.id,
            actividad_id=id,
            fecha_visita=form.fecha_visita.data,
            valoracion=form.valoracion.data,
            reseña=form.reseña.data
        )
        db.session.add(visita)
        db.session.commit()

        for file in form.fotos.data:
            if file:
                filename = secure_filename(file.filename)
                mimetype = file.mimetype
                data = file.read()
                foto = FotoVisita(visita_id=visita.id, filename=filename, data=data, mimetype=mimetype)
                db.session.add(foto)

        db.session.commit()
        flash('Visita registrada con éxito', 'success')
        return redirect(url_for('main.ver_actividad', id=id))
    elif form.is_submitted() and not current_user.is_authenticated:
        flash('Debes iniciar sesión para registrar una visita', 'danger')
        return redirect(url_for('login'))

    return render_template('ver_actividad.html', actividad=actividad, fotos_visitas=fotos_visitas, form=form, date=datetime.date)



@main_bp.route('/foto_visita/<int:id>')
def get_foto_visita(id):
    foto = FotoVisita.query.get_or_404(id)
    response = make_response(foto.data)
    response.headers.set('Content-Type', foto.mimetype)
    response.headers.set('Content-Disposition', 'inline', filename=foto.filename)
    return response


@main_bp.route('/preferencias', methods=['GET', 'POST'])
@login_required
def preferencias():
    usuario = current_user
    respuestas = RespuestasFormulario.query.filter_by(user_id=usuario.id).first()
    visitas = Visita.query.filter_by(user_id=usuario.id).all()

    form = EditarRespuestasForm(obj=respuestas)

    if form.validate_on_submit():
        if respuestas:
            respuestas.pregunta1 = form.pregunta1.data
            respuestas.pregunta2 = form.pregunta2.data
            respuestas.pregunta3 = form.pregunta3.data
            respuestas.pregunta4 = form.pregunta4.data
            respuestas.pregunta5 = form.pregunta5.data
            respuestas.pregunta6 = form.pregunta6.data
            respuestas.pregunta7 = form.pregunta7.data
        else:
            respuestas = RespuestasFormulario(
                user_id=usuario.id,
                pregunta1=form.pregunta1.data,
                pregunta2=form.pregunta2.data,
                pregunta3=form.pregunta3.data,
                pregunta4=form.pregunta4.data,
                pregunta5=form.pregunta5.data,
                pregunta6=form.pregunta6.data,
                pregunta7=form.pregunta7.data,
            )
            db.session.add(respuestas)

        db.session.commit()
        flash('Preferencias actualizadas con éxito', 'success')
        return redirect(url_for('preferencias'))

    return render_template('preferencias.html', form=form, visitas=visitas)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


# Función para extraer texto del PDF desde una ruta local
def extract_text_from_pdf_url(pdf_url):
    response = requests.get(pdf_url)
    if response.status_code == 200:
        pdf_data = response.content
        document = fitz.open(stream=pdf_data, filetype="pdf")
        text = ""
        for page_num in range(document.page_count):
            page = document.load_page(page_num)
            text += page.get_text()
        return text
    else:
        return "Error: Unable to process PDF."


pdf_url = "https://drive.google.com/uc?id=10uDnZuUciYZ2oirwE7qP2UyZtMDS4rx-"  # Reemplaza con la URL de tu PDF
pdf_text = extract_text_from_pdf_url(pdf_url)
print(f"Extracted PDF text: {pdf_text[:20]}...")  # Imprimir los primeros 20 caracteres para depuración

# <><><><><><><> ASISTENTE VIRTUAL <><><><><><><> #

# Función para hacer consultas a gpt-3.5-turbo-16k
def query_gpt4(question, context, max_context_length=2000):
    # Limitar el tamaño del contexto
    if len(context) > max_context_length:
        context = context[:max_context_length]
    prompt = f"{context}\n\nQuestion: {question}\nAnswer:"
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-16k",
        messages=messages,
        max_tokens=150,
    )
    return response.choices[0].message["content"].strip()


# Función para consultar actividades
def consultar_actividades(categoria_nombre):
    actividades = ActividadTuristica.query.join(Categoria).filter(Categoria.nombre == categoria_nombre).all()
    if not actividades:
        return jsonify({"fulfillmentText": f"No se encontraron actividades en la categoría {categoria_nombre}."})

    elementos = []
    for actividad in actividades:
        imagen_url = None
        if actividad.imagenes:
            imagen_url = f"https://turismo-85gv.onrender.com/imagen_actividad/{actividad.imagenes[0].id}"

        elementos.append([
            {
                "type": "image",
                "rawUrl": imagen_url if imagen_url else "URL DE UNA IMAGEN POR DEFECTO",
                "accessibilityText": actividad.nombre
            },
            {
                "type": "info",
                "title": actividad.nombre,
                "subtitle": actividad.descripcion_equipamiento,
                "actionLink": f"https://turismo-85gv.onrender.com/actividades/{actividad.id}"
            }
        ])

    respuesta = {
        "fulfillmentMessages": [
            {
                "payload": {
                    "richContent": elementos
                }
            }
        ]
    }

    return jsonify(respuesta)


# Función para manejar las acciones del webhook
def handle_webhook_action(action, query_result):
    if action == 'consultar_actividades':
        categoria_nombre = query_result.get('parameters', {}).get('categoria', '').capitalize()
        return consultar_actividades(categoria_nombre)
    return jsonify({"fulfillmentText": "Lo siento, no pude entender tu solicitud."})


# Ruta para el webhook
@main_bp.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(force=True)
    query_result = req.get('queryResult', {})
    action = query_result.get('action', None)

    if not action:
        return jsonify({"fulfillmentText": "No se proporcionó ninguna acción en la solicitud."})

    return handle_webhook_action(action, query_result)

def dar_consejos(actividad_nombre):
    actividad = ActividadTuristica.query.filter_by(nombre=actividad_nombre).first()
    if actividad:
        consejos = "Para participar en {}, se recomienda {}. Realizar durante {}, y el nivel de dificultad es {}.".format(
            actividad.nombre, actividad.requerimiento_guia, actividad.epoca_recomendada, actividad.nivel_dificultad)
        response_text = consejos
    else:
        response_text = "No se encontró información sobre esa actividad."
    return jsonify({"fulfillmentText": response_text})
