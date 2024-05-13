from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_user, logout_user, current_user, login_required
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from app.services import obtener_recomendaciones
from . import db
from .forms import LoginForm, RegistrationForm, PreferenciasForm
from .models import Usuario, ActividadTuristica, Categoria

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    return render_template('index.html')


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


@main_bp.route('/')
def home():
    categories = Categoria.query.all()
    print(categories)  # Esto debería imprimir los objetos de categoría en tu consola
    return render_template('index.html', categories=categories)