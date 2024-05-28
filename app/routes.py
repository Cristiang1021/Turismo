from flask import Blueprint, render_template, flash, redirect, url_for, request, send_from_directory, jsonify
from flask_login import login_user, logout_user, current_user, login_required
from flask_wtf import csrf, CSRFProtect
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.services import obtener_recomendaciones
from . import db
from .forms import LoginForm, RegistrationForm, PreferenciasForm
from .models import Usuario, ActividadTuristica, Categoria

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    categorias = Categoria.query.all()
    for categoria in categorias:
        print(categoria.nombre, categoria.image_url)  # Verificar qué datos se están recuperando
    return render_template('index.html', categorias=categorias)

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
            flash('Login unsuccessful. Please check email and password', 'danger')
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
            flash('¡Registro exitoso! Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('main.login'))
        except:
            db.session.rollback()
            flash('Error al registrar el usuario.', 'danger')
    return render_template('register.html', title='Registro', form=form)



@main_bp.route('/preferencias', methods=['GET', 'POST'])
@login_required
def preferencias():
    form = PreferenciasForm()
    if form.validate_on_submit():
        # Aquí iría la lógica para guardar las preferencias en la base de datos
        flash('Preferencias actualizadas.')
        return redirect(url_for('main.inicio'))
    return render_template('preferencias.html', form=form)


@main_bp.route('/inicio')
@login_required
def inicio():
    actividades_recomendadas = obtener_recomendaciones(current_user.id)
    return render_template('inicio.html', actividades=actividades_recomendadas)


@main_bp.route('/actividades')
def actividades():
    try:
        actividades = ActividadTuristica.query.all()
        return render_template('actividades.html', actividades=actividades)
    except Exception as e:
        print(e)
        flash('Error al cargar las actividades.', 'danger')
        return redirect(url_for('main.index'))



# <><><><><><><> ASISTENTE VIRTUAL <><><><><><><> #
@main_bp.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(force=True)
    if 'queryResult' not in req:
        return jsonify({"fulfillmentText": "Lo siento, no pude entender tu solicitud."})

    query_result = req.get('queryResult')
    if 'action' not in query_result:
        return jsonify({"fulfillmentText": "Lo siento, no pude entender tu solicitud."})

    action = query_result.get('action')
    if action == 'consultar_actividades':
        categoria_nombre = query_result.get('parameters', {}).get('categoria', '')
        return consultar_actividades(categoria_nombre)
    elif action == 'especificar_categoria':
        categoria = query_result.get('parameters').get('categoria')
        # Aquí agregarías la lógica para buscar actividades por categoría
        return jsonify({"fulfillmentText": f"Aquí tienes las actividades relacionadas con la categoría {categoria}."})

    return jsonify({"fulfillmentText": "Lo siento, no pude entender tu solicitud."})

def consultar_actividades(categoria_nombre):
    categoria = Categoria.query.filter_by(nombre=categoria_nombre).first()
    if categoria and categoria.actividades:
        actividades = [actividad.nombre for actividad in categoria.actividades]
        actividades_text = ", ".join(actividades)
        response_text = f"Actividades en la categoría de {categoria_nombre}: {actividades_text}"
    else:
        response_text = f"No se encontraron actividades en la categoría de {categoria_nombre}."
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