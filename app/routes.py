import datetime
import io
import logging
import os

import requests
from flask import Blueprint, render_template, flash, redirect, url_for, request, send_from_directory, jsonify, \
    send_file, make_response, current_app
from flask_login import login_user, logout_user, current_user, login_required
from flask_mail import Message
from flask_wtf import csrf, CSRFProtect
from pip._internal import req
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

import openai
import fitz  # PyMuPDF
from io import BytesIO

from werkzeug.utils import secure_filename

from . import db
from app import mail
from .email import send_reset_email, send_recommendation_email
from .forms import LoginForm, RegistrationForm, RecomendacionForm, \
    RegistroVisitaForm, EditarRespuestasForm, RequestResetForm, ResetPasswordForm, CambiarContraseñaForm, \
    UpdateProfileForm
from .models import Usuario, ActividadTuristica, Categoria, ImagenActividad, RespuestasFormulario, Visita, FotoVisita, \
    ActividadVista

main_bp = Blueprint('main', __name__)

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY')

openai.api_key = OPENAI_API_KEY

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

    return actividades_recomendadas[:3]


@main_bp.route('/')
def index():
    categorias = Categoria.query.all()
    actividades = ActividadTuristica.query.all()
    recomendaciones = []
    destacadas = []
    form = None

    if current_user.is_authenticated:
        recomendaciones = obtener_recomendaciones(current_user.id)
        respuestas = RespuestasFormulario.query.filter_by(user_id=current_user.id).first()
        if not respuestas or request.args.get('new_user') == 'True':
            form = RecomendacionForm()
    else:
        # Obtener las actividades con las mejores valoraciones
        mejor_actividades = (db.session.query(ActividadTuristica, func.avg(Visita.valoracion).label('avg_valoracion'))
                             .join(Visita)
                             .group_by(ActividadTuristica.id)
                             .order_by(func.avg(Visita.valoracion).desc())
                             .limit(3)
                             .all())
        # Filtra solo las actividades
        destacadas = [actividad for actividad, _ in mejor_actividades]

    return render_template('index.html', categorias=categorias, actividades=actividades, recomendaciones=recomendaciones, destacadas=destacadas, form=form)


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


@main_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    usuario = current_user
    form = UpdateProfileForm(original_email=usuario.correo, obj=usuario)

    if form.validate_on_submit():
        if form.correo.data != usuario.correo:
            usuario.correo = form.correo.data
        usuario.nombre = form.nombre.data
        db.session.commit()
        flash('Tu perfil ha sido actualizado.', 'success')
        return redirect(url_for('main.profile'))
    else:
        # Si hay errores en el formulario, agregarlos como mensajes flash
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en el campo {field}: {error}", 'danger')

    return render_template('perfil.html', user=usuario, form=form)


@main_bp.route('/cambiar_contraseña', methods=['POST'])
@login_required
def cambiar_contraseña():
    user = current_user
    form = CambiarContraseñaForm()

    if form.validate_on_submit():
        current_password = form.current_password.data
        new_password = form.new_password.data
        confirm_password = form.confirm_password.data

        if not check_password_hash(user.password, current_password):
            flash('Contraseña actual incorrecta.', 'danger')
        elif new_password != confirm_password:
            flash('La nueva contraseña y la confirmación no coinciden.', 'danger')
        else:
            user.password = generate_password_hash(new_password)
            db.session.commit()
            flash('Contraseña actualizada con éxito.', 'success')
    else:
        # Agregar mensajes de errores específicos de validación
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Error en el campo {field}: {error}", 'danger')

    return redirect(url_for('main.profile'))


@main_bp.route('/actividad/<int:id>', methods=['GET', 'POST'])
def ver_actividad(id):
    actividad = ActividadTuristica.query.get_or_404(id)
    google_maps_api_key = current_app.config['GOOGLE_MAPS_API_KEY']
    visitas = Visita.query.filter_by(actividad_id=id).order_by(Visita.valoracion.desc()).limit(6).all()
    fotos_visitas = FotoVisita.query.join(Visita).filter(Visita.actividad_id == id).all()
    form = RegistroVisitaForm()
    form.actividad_id.choices = [(actividad.id, actividad.nombre)]

    actividades_relacionadas = ActividadTuristica.query.filter(
        ActividadTuristica.categoria_id == actividad.categoria_id,
        ActividadTuristica.id != id
    ).limit(4).all()  # Limitar a 4 actividades relacionadas para no sobrecargar la vista

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

    # Manejar vistas
    usuario_id = current_user.id if current_user.is_authenticated else 3
    vista = ActividadVista.query.filter_by(usuario_id=usuario_id, actividad_id=id).first()
    if vista:
        vista.vistas += 1
    else:
        vista = ActividadVista(usuario_id=usuario_id, actividad_id=id, vistas=1)
        db.session.add(vista)
    db.session.commit()

    return render_template(
        'ver_actividad.html', actividad=actividad,
        fotos_visitas=fotos_visitas, form=form,
        date=datetime.date, visitas=visitas,
        google_maps_api_key = current_app.config['GOOGLE_MAPS_API_KEY'],
        actividades_relacionadas=actividades_relacionadas
    )

@main_bp.route('/foto_visita/<int:id>')
def get_foto_visita(id):
    foto = FotoVisita.query.get_or_404(id)
    response = make_response(foto.data)
    response.headers.set('Content-Type', foto.mimetype)
    response.headers.set('Content-Disposition', 'inline', filename=foto.filename)
    return response

@main_bp.route('/buscar', methods=['GET'])
def buscar():
    query = request.args.get('q')
    if query:
        actividades = ActividadTuristica.query.filter(ActividadTuristica.nombre.ilike(f'%{query}%')).all()
        resultados = [{'id': actividad.id, 'nombre': actividad.nombre, 'descripcion': actividad.descripcion} for actividad in actividades]
        return jsonify(resultados)
    return jsonify([])


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
        return redirect(url_for('main.preferencias'))

    return render_template('preferencias.html', form=form, visitas=visitas)

@main_bp.route('/mapa')
def mapa():
    return render_template('asistente/mapa.html')

@main_bp.route('/eliminar_cuenta', methods=['POST'])
@login_required
def eliminar_cuenta():
    user = current_user
    password = request.form.get('password')

    if check_password_hash(user.password, password):
        try:
            Visita.query.filter_by(user_id=user.id).delete()
            RespuestasFormulario.query.filter_by(user_id=user.id).delete()
            db.session.delete(user)
            db.session.commit()
            logout_user()
            flash('Cuenta eliminada con éxito.', 'success')
            return redirect(url_for('main.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error al eliminar la cuenta: {str(e)}', 'danger')
    else:
        flash('Contraseña incorrecta.', 'danger')

    return redirect(url_for('main.profile'))


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif'}


# Función para extraer texto del PDF desde una URL
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


##pdf_url = "https://drive.google.com/uc?id=10uDnZuUciYZ2oirwE7qP2UyZtMDS4rx-"  # Reemplaza con la URL de tu PDF
##pdf_text = extract_text_from_pdf_url(pdf_url)


# Función para hacer consultas a gpt-3.5-turbo-16k
def query_gpt4(question, context, max_context_length=2000):
    if len(context) > max_context_length:
        context = context[:max_context_length]
    prompt = f"{context}\n\nQuestion: {question}\nAnswer:"
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=messages,
        max_tokens=150,
    )
    return response.choices[0].message["content"].strip()


# Función para consultar actividades
def consultar_actividades(categoria_nombre=None):
    actividades_text = []

    if categoria_nombre:
        categoria = Categoria.query.filter_by(nombre=categoria_nombre).first()
        if not categoria:
            return [{
                "type": "info",
                "title": f"No se encontró la categoría {categoria_nombre}.",
                "subtitle": ""
            }]

        actividades = ActividadTuristica.query.filter_by(categoria_id=categoria.id).all()
    else:
        # Obtener 2 o 3 actividades generales
        actividades = ActividadTuristica.query.limit(1).all()

    for actividad in actividades:
        actividad_info = [
            {
                "type": "image",
                "rawUrl": f"https://turismo.ngrok.app/imagen_actividad/{actividad.imagenes[0].id}" if actividad.imagenes else "https://example.com/default.jpg",
                "accessibilityText": f"Imagen de la actividad {actividad.nombre}"
            },
            {
                "type": "info",
                "title": actividad.nombre,
                "subtitle": actividad.descripcion,
                "actionLink": f"https://turismo.ngrok.app/actividad/{actividad.id}"
            }
        ]
        actividades_text.append(actividad_info)

    if not categoria_nombre:
        actividades_text.append([
            {
                "type": "info",
                "title": "Consulta todas nuestras actividades aquí",
                "actionLink": "https://turismo.ngrok.app/actividades"
            }
        ])

    return actividades_text


def send_recommendation_email(email, recommendations, days):
    if not recommendations:
        print("No recommendations found. Skipping email send.")
        return

    # Limitar las recomendaciones al número de días especificado
    recommendations = recommendations[:days]

    # Asegúrate de que las recomendaciones se pasen correctamente al template
    formatted_recommendations = [
        {
            'nombre': r.nombre,
            'descripcion': r.descripcion,
            'imagen_url': f"https://turismo.ngrok.app/imagen_actividad/{r.imagenes[0].id}" if r.imagenes else "https://example.com/default.jpg"
        }
        for r in recommendations
    ]

    msg = Message('Recomendaciones de Actividades',
                  sender='tessis.asesor@gmail.com',
                  recipients=[email])
    msg.html = render_template('emails/recommendation_email.html', recommendations=formatted_recommendations)
    try:
        mail.send(msg)
        print("Correo enviado correctamente.")
    except Exception as e:
        print(f"Error al enviar el correo: {str(e)}")


def obtener_actividades_mas_populares(n):
    actividades = ActividadTuristica.query \
        .join(ActividadVista) \
        .group_by(ActividadTuristica.id) \
        .order_by(db.func.count(ActividadVista.id).desc()) \
        .limit(n) \
        .all()
    return actividades

# Función para obtener información de una actividad con coincidencia parcial
def obtener_informacion_actividad(actividad_nombre):
    actividad = ActividadTuristica.query.filter(
        or_(ActividadTuristica.nombre.ilike(f"%{actividad_nombre}%"),
            ActividadTuristica.descripcion.ilike(f"%{actividad_nombre}%"))
    ).first()
    if actividad:
        actividad_info = {
            "title": actividad.nombre,
            "subtitle": actividad.descripcion,
            "image": f"https://turismo.ngrok.app/imagen_actividad/{actividad.imagenes[0].id}" if actividad.imagenes else "https://example.com/default.jpg",
            "link": f"https://turismo.ngrok.app/actividad/{actividad.id}"
        }
        return actividad_info
    else:
        return None
# Función para dar consejos sobre una actividad usando GPT-4
def dar_consejos(actividad_nombre):
    actividad = ActividadTuristica.query.filter(
        or_(ActividadTuristica.nombre.ilike(f"%{actividad_nombre}%"),
            ActividadTuristica.descripcion.ilike(f"%{actividad_nombre}%"))
    ).first()
    if actividad:
        contexto = f"Nombre: {actividad.nombre}\nDescripción: {actividad.descripcion}\nRecomendaciones: {actividad.requerimiento_guia}\nÉpoca recomendada: {actividad.epoca_recomendada}\nNivel de dificultad: {actividad.nivel_dificultad}"
        pregunta = f"Dame consejos para participar en {actividad.nombre}."
        respuesta = query_gpt4(pregunta, contexto)
        return respuesta
    else:
        return f"No se encontraron consejos para {actividad_nombre}."

def handle_mostrar_actividad_y_mas():
    actividad = obtener_actividad_destacada()
    if actividad:
        fulfillment_messages = [
            {
                "payload": {
                    "richContent": [
                        [
                            {
                                "type": "image",
                                "rawUrl": f"https://turismo.ngrok.app/imagen_actividad/{actividad.imagenes[0].id}" if actividad.imagenes else "https://example.com/default.jpg",
                                "accessibilityText": f"Imagen de la actividad {actividad.nombre}"
                            },
                            {
                                "type": "info",
                                "title": actividad.nombre,
                                "subtitle": actividad.descripcion,
                                "actionLink": f"https://turismo.ngrok.app/actividad/{actividad.id}"
                            },
                            {
                                "type": "button",
                                "icon": {
                                    "type": "chevron_right",
                                    "color": "#FF9800"
                                },
                                "text": "Descubre el resto de actividades aquí",
                                "link": "https://turismo.ngrok.app/actividades"
                            }
                        ]
                    ]
                }
            }
        ]
        return jsonify({"fulfillmentMessages": fulfillment_messages})
    else:
        return jsonify({"fulfillmentText": "No se encontró una actividad destacada."})

@main_bp.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(force=True)
    action = req.get('queryResult').get('action')
    parameters = req.get('queryResult').get('parameters')

    if action == 'opciones_mapa':
        # Opciones de actividades
        response = {
            "fulfillmentMessages": [
                {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "type": "info",
                                    "title": "¿De qué actividad te gustaría ver el mapa?"
                                },
                                {
                                    "type": "chips",
                                    "options": [
                                        {
                                            "text": "Quiero ver el mapa de Camping en la ruta de los Hieleros del Chimborazo"
                                        },
                                        {
                                            "text": "Quiero ver el mapa de Interpretación de flora y fauna"
                                        },
                                        {
                                            "text": "Quiero ver el mapa de Camping en la ruta Piedra de Bolívar"
                                        },
                                        {
                                            "text": "Quiero ver el mapa de Camping en la ruta del Glaciar Hans Meyer"
                                        },
                                        {
                                            "text": "Quiero ver el mapa de Camping en la ruta Cascada Cóndor Samana"
                                        },
                                        {
                                            "text": "Quiero ver el mapa de Snowboard",
                                        },
                                        {
                                            "text": "Quiero ver el mapa de Cicloturismo ruta Hieleros del Chimborazo"
                                        },
                                        {
                                            "text": "Quiero ver el mapa de Cayoning en la Cascada Cóndor Samana"
                                        },
                                        {
                                            "text": "Quiero ver el mapa de Senderismo Ruta Piedra de Bolívar"
                                        },
                                        {
                                            "text": "Quiero ver el mapa de Senderismo Ruta Hieleros del Chimborazo"
                                        }
                                    ]
                                }
                            ]
                        ]
                    }
                }
            ]
        }
        return jsonify(response)

    if action == 'mostrar_mapa':
        actividad_nombre = parameters.get('actividad')
        # Verificar si la actividad es seleccionada de las opciones
        if actividad_nombre in ["Senderismo Ruta Piedra de Bolívar", "Cayoning en la Cascada Cóndor Samana",
                                "Otra Actividad"]:
            response = {
                "fulfillmentText": f"Quiero ver el mapa de {actividad_nombre}"
            }
            return jsonify(response)

        actividad = ActividadTuristica.query.filter_by(nombre=actividad_nombre).first()
        if actividad:
            localizacion = actividad.localizacion_geografica
            if localizacion:
                latitud, longitud = map(str.strip, localizacion.split(','))
                mapa_url = f"https://www.google.com/maps/search/?api=1&query={latitud},{longitud}"
                response = {
                    "fulfillmentMessages": [
                        {
                            "payload": {
                                "richContent": [
                                    [
                                        {
                                            "type": "info",
                                            "title": f"Ubicación de {actividad_nombre}",
                                            "subtitle": f"Latitud: {latitud}, Longitud: {longitud}",
                                            "actionLink": mapa_url
                                        },
                                        {
                                            "type": "image",
                                            "rawUrl": f"https://maps.googleapis.com/maps/api/staticmap?center={latitud},{longitud}&zoom=15&size=600x300&maptype=roadmap&markers=color:red%7C{latitud},{longitud}&key={GOOGLE_MAPS_API_KEY}",
                                            "accessibilityText": f"Mapa de la actividad {actividad_nombre}"
                                        }
                                    ]
                                ]
                            }
                        }
                    ]
                }
                return jsonify(response)
            else:
                return jsonify({"fulfillmentText": "Lo siento, no se encontró la localización de esa actividad."})
        else:
            return jsonify({"fulfillmentText": "Lo siento, no pude encontrar la ubicación de esa actividad."})


    elif action == 'opciones_informacion':
        return handle_opciones_informacion()
    elif action == 'mostrar_informacion':
        return handle_mostrar_informacion(parameters)

    elif action == 'recomendaciones':
        response = {
            "fulfillmentMessages": [
                {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "title": "¿Estás registrado?",
                                    "subtitle": "Selecciona una opción para continuar.",
                                    "type": "info"
                                },
                                {
                                    "type": "chips",
                                    "options": [
                                        {
                                            "text": "Sí"
                                        },
                                        {
                                            "text": "No"
                                        }
                                    ]
                                }
                            ]
                        ]
                    }
                }
            ]
        }
        return jsonify(response)

    elif action == 'usuario_registrado':
        registrado = parameters.get('registrado')
        if registrado.lower() == 'sí':
            response = {
                "fulfillmentText": "Por favor, proporciona tu correo electrónico."
            }
            return jsonify(response)
        else:
            response = {
                "fulfillmentMessages": [
                    {
                        "payload": {
                            "richContent": [
                                [
                                    {
                                        "title": "Para darte recomendaciones personalizadas, por favor regístrate en nuestro sitio web.",
                                        "type": "info"
                                    }
                                ]
                            ]
                        }
                    }
                ]
            }
            return jsonify(response)

    elif action == 'capturar_correo':
        email = parameters.get('email')
        usuario = Usuario.query.filter_by(correo=email).first()
        if usuario:
            recomendaciones = obtener_recomendaciones(usuario.id)
            if recomendaciones:
                fulfillment_messages = [
                    {
                        "payload": {
                            "richContent": [
                                [
                                    {
                                        "type": "image",
                                        "rawUrl": f"https://turismo.ngrok.app/imagen_actividad/{actividad.imagenes[0].id}" if actividad.imagenes else "https://example.com/default.jpg",
                                        "accessibilityText": f"Imagen de la actividad {actividad.nombre}"
                                    },
                                    {
                                        "type": "info",
                                        "title": f"Recomendación {i + 1}: {actividad.nombre}",
                                        "subtitle": actividad.descripcion,
                                        "actionLink": f"https://turismo.ngrok.app/actividad/{actividad.id}"
                                    }
                                ]
                            ]
                        }
                    } for i, actividad in enumerate(recomendaciones)
                ]
                return jsonify({"fulfillmentMessages": fulfillment_messages})
            else:
                response = {
                    "fulfillmentText": "Todavía no has seleccionado tus preferencias. ¿Quieres hacerlo ahora?",
                    "outputContexts": [
                        {
                            "name": f"{req.get('session')}/contexts/awaiting_preferences",
                            "lifespanCount": 5,
                            "parameters": {
                                "email": email
                            }
                        }
                    ]
                }
                return jsonify(response)
        else:
            response = {
                "fulfillmentMessages": [
                    {
                        "payload": {
                            "richContent": [
                                [
                                    {
                                        "type": "info",
                                        "title": "No se encontró un usuario con ese correo.",
                                        "subtitle": "Por favor, regístrate en nuestro sitio web."
                                    },
                                    {
                                        "type": "button",
                                        "icon": {
                                            "type": "chevron_right",
                                            "color": "#FF9800"
                                        },
                                        "text": "Registrar",
                                        "link": "https://turismo.ngrok.app/register"
                                    }
                                ]
                            ]
                        }
                    }
                ]
            }
            return jsonify(response)

    elif action == 'mostrar_actividad_y_mas':
        return handle_mostrar_actividad_y_mas()

    elif action == 'actividades_mejores_resenas':
        mejores_actividades = obtener_actividades_mejores_resenas()
        if mejores_actividades:
            fulfillment_messages = []
            for actividad, valoracion_media, num_resenas in mejores_actividades:
                message = {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "type": "image",
                                    "rawUrl": f"https://turismo.ngrok.app/imagen_actividad/{actividad.imagenes[0].id}" if actividad.imagenes else "https://example.com/default.jpg",
                                    "accessibilityText": f"Imagen de la actividad {actividad.nombre}"
                                },
                                {
                                    "type": "info",
                                    "title": f"{actividad.nombre}",
                                    "subtitle": f"Valoración media: {valoracion_media:.1f} estrellas\nNúmero de reseñas: {num_resenas}",
                                    "actionLink": f"https://turismo.ngrok.app/actividad/{actividad.id}"
                                }
                            ]
                        ]
                    }
                }
                fulfillment_messages.append(message)
            return jsonify({"fulfillmentMessages": fulfillment_messages})
        else:
            return jsonify({"fulfillmentText": "No se encontraron actividades con reseñas."})

    elif action == 'dar_consejos':
        actividad_nombre = parameters.get('actividad_nombre')
        actividad = ActividadTuristica.query.filter_by(nombre=actividad_nombre).first()
        if actividad:
            consejos = f"Para participar en {actividad.nombre}, se recomienda {actividad.requerimiento_guia}. Realizar durante {actividad.epoca_recomendada}, y el nivel de dificultad es {actividad.nivel_dificultad}."
            response_text = consejos
        else:
            response_text = "No se encontró información sobre esa actividad."
        return jsonify({"fulfillmentText": response_text})

    return jsonify({"fulfillmentText": "Lo siento, no pude entender tu solicitud."})



def obtener_actividad_destacada():
    # Obtener la actividad con el mayor número de vistas
    actividad_vista = ActividadVista.query.order_by(ActividadVista.vistas.desc()).first()
    if actividad_vista:
        actividad = ActividadTuristica.query.get(actividad_vista.actividad_id)
        return actividad
    return None


def obtener_actividades_mejores_resenas():
    actividades = db.session.query(
        Visita.actividad_id,
        db.func.avg(Visita.valoracion).label('valoracion_media'),
        db.func.count(Visita.id).label('num_resenas')
    ).group_by(Visita.actividad_id) \
        .order_by(db.func.avg(Visita.valoracion).desc()) \
        .limit(5) \
        .all()

    resultados = []
    for actividad_id, valoracion_media, num_resenas in actividades:
        actividad = ActividadTuristica.query.get(actividad_id)
        resultados.append((actividad, valoracion_media, num_resenas))

    return resultados

def handle_opciones_mapa():
    response = {
        "fulfillmentMessages": [
            {
                "payload": {
                    "richContent": [
                        [
                            {
                                "type": "info",
                                "title": "¿De qué actividad te gustaría ver el mapa?"
                            },
                            {
                                "type": "chips",
                                "options": [
                                    {"text": "Senderismo Ruta Piedra de Bolívar"},
                                    {"text": "Cayoning en la Cascada Cóndor Samana"},
                                    {"text": "Senderismo Ruta Hieleros del Chimborazo"},
                                    {"text": "Cicloturismo ruta Hieleros del Chimborazo"},
                                    {"text": "Snowboard"},
                                    {"text": "Camping en la ruta Cascada Cóndor Samana"},
                                    {"text": "Camping en la ruta del Glaciar Hans Meyer"},
                                    {"text": "Camping en la ruta Piedra de Bolívar"},
                                    {"text": "Interpretación de flora y fauna"},
                                    {"text": "Camping en la ruta de los Hieleros del Chimborazo"}
                                ]
                            }
                        ]
                    ]
                }
            }
        ]
    }
    return jsonify(response)

def handle_mostrar_mapa(req):
    query_text = req.get('queryResult').get('queryText')
    if query_text.startswith("Quiero ver el mapa de "):
        actividad_nombre = query_text.replace("Quiero ver el mapa de ", "").strip()

        actividad = ActividadTuristica.query.filter_by(nombre=actividad_nombre).first()
        if actividad:
            localizacion = actividad.localizacion_geografica
            if localizacion:
                latitud, longitud = map(str.strip, localizacion.split(','))
                mapa_url = f"https://www.google.com/maps/search/?api=1&query={latitud},{longitud}"
                response = {
                    "fulfillmentMessages": [
                        {
                            "payload": {
                                "richContent": [
                                    [
                                        {
                                            "type": "info",
                                            "title": f"Ubicación de {actividad_nombre}",
                                            "subtitle": f"Latitud: {latitud}, Longitud: {longitud}",
                                            "actionLink": mapa_url
                                        },
                                        {
                                            "type": "image",
                                            "rawUrl": f"https://maps.googleapis.com/maps/api/staticmap?center={latitud},{longitud}&zoom=15&size=600x300&maptype=roadmap&markers=color:red%7C{latitud},{longitud}&key={GOOGLE_MAPS_API_KEY}",
                                            "accessibilityText": f"Mapa de la actividad {actividad_nombre}"
                                        }
                                    ]
                                ]
                            }
                        }
                    ]
                }
                return jsonify(response)
            else:
                return jsonify({"fulfillmentText": "Lo siento, no se encontró la localización de esa actividad."})
        else:
            return jsonify({"fulfillmentText": "Lo siento, no pude encontrar la ubicación de esa actividad."})
    else:
        return jsonify({"fulfillmentText": "Lo siento, no pude entender tu solicitud."})

def handle_opciones_informacion():
    response = {
        "fulfillmentMessages": [
            {
                "payload": {
                    "richContent": [
                        [
                            {
                                "type": "info",
                                "title": "¿Sobre qué actividad te gustaría más información?"
                            },
                            {
                                "type": "chips",
                                "options": [
                                    {"text": "Senderismo Ruta Piedra de Bolívar"},
                                    {"text": "Cayoning en la Cascada Cóndor Samana"},
                                    {"text": "Senderismo Ruta Hieleros del Chimborazo"},
                                    {"text": "Cicloturismo ruta Hieleros del Chimborazo"},
                                    {"text": "Snowboard"},
                                    {"text": "Camping en la ruta Cascada Cóndor Samana"},
                                    {"text": "Camping en la ruta del Glaciar Hans Meyer"},
                                    {"text": "Camping en la ruta Piedra de Bolívar"},
                                    {"text": "Interpretación de flora y fauna"},
                                    {"text": "Camping en la ruta de los Hieleros del Chimborazo"}
                                ]
                            }
                        ]
                    ]
                }
            }
        ],
        "outputContexts": [
            {
                "name": "projects/<your-project-id>/agent/sessions/<session-id>/contexts/informacion_context",
                "lifespanCount": 5,
                "parameters": {
                    "actividad": "Quiero más información de Senderismo Ruta Piedra de Bolívar"
                }
            }
        ]
    }
    return jsonify(response)
def handle_mostrar_informacion(parameters):
    query_text = parameters.get('actividad')
    if query_text.startswith("Quiero más información de "):
        actividad_nombre = query_text.replace("Quiero más información de ", "").strip()

        actividad = ActividadTuristica.query.filter_by(nombre=actividad_nombre).first()
        if actividad:
            contexto = f"Nombre: {actividad.nombre}\nDescripción: {actividad.descripcion}\nRecomendaciones: {actividad.requerimiento_guia}\nÉpoca recomendada: {actividad.epoca_recomendada}\nNivel de dificultad: {actividad.nivel_dificultad}"
            pregunta = f"Dame una descripción detallada sobre la actividad {actividad.nombre}."
            informacion = query_gpt4(pregunta, contexto)

            response = {
                "fulfillmentText": f"Información sobre {actividad.nombre}: {informacion}"
            }
            return jsonify(response)
        else:
            return jsonify({"fulfillmentText": "Lo siento, no pude encontrar información sobre esa actividad."})

