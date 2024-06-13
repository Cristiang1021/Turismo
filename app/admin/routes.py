import os
from flask import abort, request, current_app, render_template, redirect, url_for, flash, send_file, jsonify
from flask_login import current_user, logout_user, login_required
from psycopg2._psycopg import IntegrityError
from werkzeug.utils import secure_filename
from datetime import datetime
from app import db
from app.admin.forms import UsuarioForm, EditarUsuarioForm, CategoriaForm, ActividadTuristicaForm
from app.models import Usuario, Categoria, ActividadTuristica, ImagenActividad
from . import admin_bp
import io
from config import Config  # Asegúrate de importar Config correctamente

@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.es_admin:
        abort(403)
    return render_template('dashboard.html')

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión con éxito.', 'success')
    return redirect(url_for('main.index'))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def save_image(file):
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        mimetype = file.mimetype
        image_data = file.read()
        print(f"Filename: {filename}, Mimetype: {mimetype}, Image Data Length: {len(image_data)}")
        return filename, mimetype, image_data
    return None, None, None




@admin_bp.route('/usuarios')
@login_required
def usuarios():
    page = request.args.get('page', 1, type=int)
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
        if usuario.correo != form.correo.data:
            usuario.correo = form.correo.data
        if form.password.data:
            usuario.set_password(form.password.data)
        usuario.es_admin = form.es_admin.data
        db.session.commit()
        flash('Usuario actualizado con éxito.', 'success')
        return redirect(url_for('admin.dashboard'))
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
    categorias = Categoria.query.paginate(page=page, per_page=6)
    return render_template('admin/categorias.html', categorias=categorias)


@admin_bp.route('/categorias/crear', methods=['GET', 'POST'])
@login_required
def crear_categoria():
    form = CategoriaForm()

    if form.validate_on_submit():
        # Procesar carga de nueva imagen
        filename, mimetype, image_data = None, None, None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename, mimetype, image_data = save_image(file)

        nueva_categoria = Categoria(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            image_name=filename,
            image_data=image_data,
            image_mimetype=mimetype
        )

        try:
            db.session.add(nueva_categoria)
            db.session.commit()
            #flash('Categoría creada con éxito!', 'success')
            return jsonify({'status': 'success', 'message': 'Categoría creada con éxito!'}), 200
        except IntegrityError as e:
            db.session.rollback()
            if 'categoria_nombre_key' in str(e.orig):
                #flash('Ya existe una categoría con ese nombre.', 'danger')
                return jsonify({'status': 'error', 'message': 'Ya existe una categoría con ese nombre.'}), 400
            else:
                #flash(f'Error al crear la categoría: {str(e)}', 'danger')
                return jsonify({'status': 'error', 'message': f'Error al crear la categoría: {str(e)}'}), 500
        except Exception as e:
            db.session.rollback()
            #flash(f'Error al crear la categoría: {str(e)}', 'danger')
            return jsonify({'status': 'error', 'message': f'Error al crear la categoría: {str(e)}'}), 500

    return render_template('admin/crear_categoria.html', form=form)


@admin_bp.route('/categorias/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_categoria(id):
    categoria = Categoria.query.get_or_404(id)
    form = CategoriaForm(obj=categoria)

    if form.validate_on_submit():
        print("Formulario validado")
        form.populate_obj(categoria)

        # Procesar eliminación de imagen
        if 'delete_image' in request.form and request.form['delete_image'] == '1':
            categoria.image_name = None
            categoria.image_data = None
            categoria.image_mimetype = None

        # Procesar carga de nueva imagen y reemplazar la existente
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '':
                filename, mimetype, image_data = save_image(file)
                if filename and mimetype and image_data:
                    categoria.image_name = filename
                    categoria.image_data = image_data
                    categoria.image_mimetype = mimetype
                else:
                    flash('Error al guardar la imagen.', 'danger')

        try:
            db.session.commit()
            flash('Categoría actualizada con éxito!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Error al actualizar la categoría: {e}', 'danger')

        return redirect(url_for('admin.editar_categoria', id=id))

    else:
        print("Formulario no válido")
        print(form.errors)

    return render_template('admin/editar_categoria.html', form=form, categoria=categoria)


from sqlalchemy.exc import IntegrityError


@admin_bp.route('/categorias/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_categoria(id):
    categoria = Categoria.query.get_or_404(id)

    if categoria.actividades:
        ##flash('Error: Asegúrate de eliminar todas las actividades asociadas a esta categoría antes de eliminarla.', 'danger')
        return jsonify({'status': 'error', 'message': 'Error: Asegúrate de eliminar todas las actividades asociadas a esta categoría antes de eliminarla.'}), 400

    try:
        db.session.delete(categoria)
        db.session.commit()
        ##flash('Categoría eliminada con éxito!', 'success')
        return jsonify({'status': 'success', 'message': 'Categoría eliminada con éxito!'}), 200
    except Exception as e:
        db.session.rollback()
        ##flash(f'Error al eliminar la categoría: {str(e)}', 'danger')
        return jsonify({'status': 'error', 'message': f'Error al eliminar la categoría: {str(e)}'}), 500


@admin_bp.route('/actividades')
@login_required
def listar_actividades():
    page = request.args.get('page', 1, type=int)
    actividades = ActividadTuristica.query.paginate(page=page, per_page=6)
    return render_template('admin/actividades.html', actividades=actividades)

def process_images(request, actividad):
    if request.method == 'POST' and 'new_images' in request.files:
        files = request.files.getlist('new_images')
        for file in files:
            if file and file.filename != '':
                filename, mimetype, image_data = save_image(file)
                if filename:
                    imagen_actividad = ImagenActividad(
                        name=filename,
                        data=image_data,
                        mimetype=mimetype,
                        actividad_id=actividad.id
                    )
                    db.session.add(imagen_actividad)

@admin_bp.route('/actividades/crear', methods=['GET', 'POST'])
@login_required
def crear_actividad():
    form = ActividadTuristicaForm()

    if form.validate_on_submit():
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
            temperatura_maxima=form.temperatura_maxima.data,
            precipitacion_media_anual=form.precipitacion_media_anual.data,
            requerimiento_guia=form.requerimiento_guia.data,
            localizacion_geografica=form.localizacion_geografica.data,
            precio_referencial=form.precio_referencial.data,
            categoria_id=form.categoria_id.data,
            acceso=form.acceso.data,
        )
        db.session.add(actividad)
        db.session.flush()

        if 'imagenes' in request.files:
            files = request.files.getlist('imagenes')
            for file in files:
                if file and file.filename != '':
                    filename, mimetype, image_data = save_image(file)
                    if filename and mimetype and image_data:
                        imagen_actividad = ImagenActividad(
                            name=filename,
                            data=image_data,
                            mimetype=mimetype,
                            actividad_id=actividad.id
                        )
                        db.session.add(imagen_actividad)
        try:
            db.session.commit()
            flash('¡Actividad creada con éxito!', 'success')
            return redirect(url_for('admin.listar_actividades'))
        except Exception as e:
            db.session.rollback()
            flash('Error al guardar la actividad: {}'.format(e), 'danger')

    return render_template('admin/crear_actividad.html', form=form)



@admin_bp.route('/actividades/editar/<int:id>', methods=['GET', 'POST'])
@login_required
def editar_actividad(id):
    actividad = ActividadTuristica.query.get_or_404(id)
    form = ActividadTuristicaForm(obj=actividad)

    if form.validate_on_submit():
        form.populate_obj(actividad)

        # Procesar eliminación de imágenes
        delete_image_ids = request.form.getlist('delete_images')
        for imagen_id in delete_image_ids:
            imagen = ImagenActividad.query.get(imagen_id)
            if imagen:
                db.session.delete(imagen)

        # Procesar nuevas imágenes
        if 'new_images' in request.files:
            files = request.files.getlist('new_images')
            for file in files:
                if file and file.filename != '':
                    filename, mimetype, image_data = save_image(file)
                    if filename and mimetype and image_data:
                        nueva_imagen = ImagenActividad(
                            name=filename,
                            mimetype=mimetype,
                            data=image_data,
                            actividad_id=actividad.id
                        )
                        db.session.add(nueva_imagen)

        db.session.commit()
        flash('Actividad actualizada con éxito!', 'success')
        return redirect(url_for('admin.listar_actividades'))

    return render_template('admin/editar_actividad.html', form=form, actividad=actividad)


@admin_bp.route('/actividades/eliminar/<int:id>', methods=['POST'])
@login_required
def eliminar_actividad(id):
    actividad = ActividadTuristica.query.get_or_404(id)
    try:
        ImagenActividad.query.filter_by(actividad_id=id).delete()
        db.session.delete(actividad)
        db.session.commit()
        flash('Actividad eliminada con éxito!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error al eliminar la actividad: {e}', 'danger')

    return redirect(url_for('admin.listar_actividades'))

import io
@admin_bp.route('/imagen_actividad/<int:id>')
def get_imagen_actividad(id):
    imagen = ImagenActividad.query.get(id)
    if imagen:
        return send_file(io.BytesIO(imagen.data), mimetype=imagen.mimetype, as_attachment=False, download_name=imagen.name)
    return 'Image not found!', 404

@admin_bp.route('/categoria_imagen/<int:id>')
def get_categoria_image(id):
    categoria = Categoria.query.get(id)
    if categoria and categoria.image_data:
        return send_file(io.BytesIO(categoria.image_data), mimetype=categoria.image_mimetype, as_attachment=False, download_name=categoria.image_name)
    return 'Image not found!', 404