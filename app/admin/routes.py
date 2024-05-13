import os

from flask import abort, request, current_app
from flask import render_template, redirect, url_for, flash
from flask_login import current_user, logout_user
from flask_login import login_required
from werkzeug.utils import secure_filename
from datetime import datetime
from app import db
from app.admin.forms import UsuarioForm, EditarUsuarioForm, \
    CategoriaForm, ActividadTuristicaForm
from app.models import Usuario, Categoria, ActividadTuristica, ImagenActividad
from . import admin_bp
import cloudinary.uploader
from config import Config

# Define el Blueprint con la ubicación correcta de las plantillas.

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.es_admin:
        abort(403)
    # Flask buscará la plantilla en app/templates/admin/dashboard.html automáticamente.
    return render_template('dashboard.html')


@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión con éxito.', 'success')
    return redirect(url_for('main.index'))  # Asegúrate de cambiar 'main.index' al endpoint correcto.


@admin_bp.route('/usuarios')
@login_required
def usuarios():
    page = request.args.get('page', 1, type=int)
    # Ordena los usuarios de manera que los administradores aparezcan primero.
    usuarios = Usuario.query.order_by(Usuario.es_admin.desc()).paginate(page=page, per_page=6)
    return render_template('admin/usuarios.html', usuarios=usuarios)




@admin_bp.route('/usuarios/crear', methods=['GET', 'POST'])
@login_required
def crear_usuario():
    form = UsuarioForm()
    if form.validate_on_submit():
        usuario = Usuario(nombre=form.nombre.data, correo=form.correo.data)
        usuario.set_password(form.password.data)
        db.session.add(usuario)
        db.session.commit()
        flash('Usuario creado con éxito', 'success')
        return redirect(url_for('admin.usuarios'))
    else:
        for fieldName, errorMessages in form.errors.items():
            for err in errorMessages:
                flash(f"{fieldName}: {err}", 'danger')
    return render_template('admin/crear_usuario.html', form=form)


@admin_bp.route('/usuarios/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    form = EditarUsuarioForm(obj=usuario, original_email=usuario.correo)
    if form.validate_on_submit():
        usuario.nombre = form.nombre.data
        # Actualiza el correo solo si ha cambiado
        if usuario.correo != form.correo.data:
            usuario.correo = form.correo.data
        # Actualiza la contraseña solo si el campo no está vacío
        if form.password.data:
            usuario.set_password(form.password.data)
        usuario.es_admin = form.es_admin.data
        db.session.commit()
        flash('Usuario actualizado con éxito.', 'success')
        return redirect(url_for('admin.dashboard'))
    # Si no es POST, rellenar el formulario con los datos del usuario
    elif request.method == 'GET':
        form.nombre.data = usuario.nombre
        form.correo.data = usuario.correo
        form.es_admin.data = usuario.es_admin
    return render_template('admin/editar_usuario.html', form=form, usuario=usuario)



@admin_bp.route('/usuarios/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_usuario(id):
    usuario = Usuario.query.get_or_404(id)
    if usuario:
        db.session.delete(usuario)
        db.session.commit()
        flash('Usuario eliminado con éxito.', 'success')
    else:
        flash('Usuario no encontrado.', 'danger')
    return redirect(url_for('admin.usuarios'))


@admin_bp.route('/categorias')
@login_required
def listar_categorias():
    page = request.args.get('page', 1, type=int)
    categorias = Categoria.query.paginate(page=page, per_page=6) # Assuming you have a Categoria model and want to retrieve all records
    return render_template('admin/categorias.html', categorias=categorias)


@admin_bp.route('/categorias/crear', methods=['GET', 'POST'])
def crear_categoria():
    form = CategoriaForm()
    if form.validate_on_submit():
        categoria = Categoria(nombre=form.nombre.data, descripcion=form.descripcion.data)
        db.session.add(categoria)
        db.session.commit()
        flash('Categoría creada con éxito.')
        return redirect(url_for('admin.listar_categorias'))
    return render_template('admin/crear_categoria.html', form=form)

@admin_bp.route('/categorias/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    form = CategoriaForm(obj=categoria)
    if form.validate_on_submit():
        form.populate_obj(categoria)
        db.session.commit()
        flash('Categoría actualizada con éxito!', 'success')
        return redirect(url_for('admin.listar_categorias'))
    return render_template('admin/editar_categoria.html', form=form, categoria=categoria)


@admin_bp.route('/categorias/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    db.session.delete(categoria)
    db.session.commit()
    flash('Categoría eliminada con éxito!', 'success')
    return redirect(url_for('admin.listar_categorias'))


@admin_bp.route('/actividades')
@login_required
def listar_actividades():

    page = request.args.get('page', 1, type=int)
    actividades = ActividadTuristica.query.paginate(page=page, per_page=6)
    return render_template('admin/actividades.html', actividades=actividades)



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_image(file):
    if file and allowed_file(file.filename):
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        filename = f"{timestamp}_{secure_filename(file.filename)}"
        file_path = os.path.join(current_app.root_path, 'static', 'uploads', filename)
        file.save(file_path)
        return url_for('static', filename=f'uploads/{filename}')
    return None



def process_images(form, request, actividad):
    if request.method == 'POST' and 'new_images' in request.files:
        files = request.files.getlist('new_images')
        for file in files:
            if file and file.filename != '':
                image_url = save_image(file)
                if image_url:
                    imagen_actividad = ImagenActividad(url=image_url, actividad_id=actividad.id)
                    db.session.add(imagen_actividad)

@admin_bp.route('/actividades/crear', methods=['GET', 'POST'])
@login_required
def crear_actividad():

    form = ActividadTuristicaForm()

    if form.validate_on_submit():
        # Crea una nueva actividad con los datos del formulario
        actividad = ActividadTuristica(
            nombre=form.nombre.data,
            descripcion_equipamiento=form.descripcion_equipamiento.data,
            nivel_dificultad=form.nivel_dificultad.data,
            nivel_fisico_requerido=form.nivel_fisico_requerido.data,
            tiempo_promedio_duracion=form.tiempo_promedio_duracion.data,
            sitio=form.sitio.data,
            cota_maxima=form.cota_maxima.data,
            cota_minima=form.cota_minima.data,
            desnivel_subida=form.desnivel_subida.data,
            desnivel_bajada=form.desnivel_bajada.data,
            lugar_partida=form.lugar_partida.data,
            lugar_llegada=form.lugar_llegada.data,
            epoca_recomendada=form.epoca_recomendada.data,
            tipo_superficie=form.tipo_superficie.data,
            temperatura_minima=form.temperatura_minima.data,
            precipitacion_media_anual=form.precipitacion_media_anual.data,
            requerimiento_guia=form.requerimiento_guia.data,
            localizacion_geografica=form.localizacion_geografica.data,
            precio_referencial=form.precio_referencial.data,
            categoria_id = form.categoria_id.data,
            acceso = form.acceso.data,
        )
        db.session.add(actividad)
        db.session.flush()  # Asegura que la actividad tiene un ID

        if 'imagenes' in request.files:
            files = request.files.getlist('imagenes')
            for file in files:
                if file and file.filename != '':
                    image_url = save_image(file)
                    if image_url:
                        imagen_actividad = ImagenActividad(url=image_url, actividad_id=actividad.id)
                        db.session.add(imagen_actividad)
        try:
            db.session.commit()  # Confirma la transacción
            flash('¡Actividad creada con éxito!', 'success')
            return redirect(url_for('admin.listar_actividades'))
        except Exception as e:
            db.session.rollback()
            flash('Error al guardar la actividad: {}'.format(e), 'danger')
            print("Error:", e)

    return render_template('admin/crear_actividad.html', form=form)


@admin_bp.route('/actividades/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_actividad(id):
    actividad = ActividadTuristica.query.get_or_404(id)
    form = ActividadTuristicaForm(obj=actividad)

    if form.validate_on_submit():
        form.populate_obj(actividad)

        process_images(form, request, actividad)
        if request.method == 'POST' and 'delete_images' in form:
            for imagen_id in form.delete_images:
                imagen = ImagenActividad.query.get(imagen_id)
                if imagen:
                    db.session.delete(imagen)

        db.session.commit()
        flash('Actividad actualizada con éxito!', 'success')
        return redirect(url_for('admin.listar_actividades'))

    return render_template('admin/editar_actividad.html', form=form, actividad=actividad)

# Manejo de eliminación de imágenes existentes
#        if request.form.getlist('delete_images'):
#            for imagen_id in request.form.getlist('delete_images'):
#                imagen = ImagenActividad.query.get(imagen_id)
#                if imagen:
#                    db.session.delete(imagen)

@admin_bp.route('/actividades/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_actividad(id):
    actividad = ActividadTuristica.query.get_or_404(id)
    try:
        # Eliminar todas las imágenes asociadas primero
        ImagenActividad.query.filter_by(actividad_id=id).delete()

        # Eliminar la actividad
        db.session.delete(actividad)
        db.session.commit()
        flash('Actividad eliminada con éxito!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la actividad: {e}', 'danger')

    return redirect(url_for('admin.listar_actividades'))
