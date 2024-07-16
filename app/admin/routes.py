from datetime import datetime, timedelta
from io import BytesIO

from flask import abort, request, render_template, redirect, url_for, flash, send_file, jsonify, make_response, Response
from flask_login import current_user, logout_user, login_required
from matplotlib import pyplot as plt
from psycopg2._psycopg import IntegrityError
from sqlalchemy import func
from werkzeug.utils import secure_filename
from xhtml2pdf import pisa

from app import db
from app.admin.forms import UsuarioForm, EditarUsuarioForm, CategoriaForm, ActividadTuristicaForm, EventoForm, \
    EditarVisitaForm
from app.models import Usuario, Categoria, ActividadTuristica, ImagenActividad, Evento, Visita, ActividadVista, \
    FotoVisita
from config import Config  # Asegúrate de importar Config correctamente
from . import admin_bp


@admin_bp.route('/dashboard')
@login_required
def dashboard():
    if not current_user.es_admin:
        abort(403)
    return render_template('dashboard.html')

@admin_bp.route('/dashboard_data')
@login_required
def dashboard_data():
    # Obtener el parámetro de período de tiempo
    periodo = request.args.get('periodo', 'mes')
    now = datetime.utcnow()

    if periodo == 'dia':
        start_date = now - timedelta(days=1)
    elif periodo == 'semana':
        start_date = now - timedelta(weeks=1)
    elif periodo == 'año':
        start_date = now - timedelta(days=365)
    else:  # mes por defecto
        start_date = now - timedelta(days=30)

    total_actividades = db.session.query(func.count(ActividadTuristica.id)).scalar()
    total_usuarios = db.session.query(func.count(Usuario.id)).scalar()
    total_visitas = db.session.query(func.count(Visita.id)).scalar()

    visitas_por_categoria = db.session.query(
        Categoria.nombre,
        func.count(Visita.id).label('count')
    ).join(ActividadTuristica, ActividadTuristica.categoria_id == Categoria.id)\
     .join(Visita, Visita.actividad_id == ActividadTuristica.id)\
     .group_by(Categoria.nombre).all()

    actividades_mas_vistas = db.session.query(
        ActividadTuristica.nombre,
        func.sum(ActividadVista.vistas).label('total_vistas')
    ).join(ActividadVista, ActividadVista.actividad_id == ActividadTuristica.id)\
     .group_by(ActividadTuristica.nombre)\
     .order_by(func.sum(ActividadVista.vistas).desc()).limit(5).all()

    actividades_mas_visitadas = db.session.query(
        ActividadTuristica.nombre,
        func.count(Visita.id).label('count')
    ).join(Visita, Visita.actividad_id == ActividadTuristica.id)\
     .group_by(ActividadTuristica.nombre)\
     .order_by(func.count(Visita.id).desc()).limit(5).all()

    usuarios_registrados = db.session.query(
        func.date(Usuario.created_at),
        func.count(Usuario.id).label('count')
    ).filter(Usuario.created_at >= start_date)\
     .group_by(func.date(Usuario.created_at))\
     .all()

    data = {
        'total_actividades': total_actividades,
        'total_usuarios': total_usuarios,
        'total_visitas': total_visitas,
        'visitas_por_categoria': [{'nombre': row[0], 'count': row[1]} for row in visitas_por_categoria],
        'actividades_mas_vistas': [{'nombre': row[0], 'count': row[1]} for row in actividades_mas_vistas],
        'actividades_mas_visitadas': [{'nombre': row[0], 'count': row[1]} for row in actividades_mas_visitadas],
        'usuarios_registrados': [{'fecha': row[0], 'count': row[1]} for row in usuarios_registrados]
    }
    return jsonify(data)


"""
@admin_bp.route('/visitas_por_categoria.png')
@login_required
def visitas_por_categoria_chart():
    if not current_user.es_admin:
        abort(403)

    visitas_por_categoria = db.session.query(
        Categoria.nombre, db.func.count(Visita.id).label('count')
    ).join(ActividadTuristica, ActividadTuristica.categoria_id == Categoria.id).join(Visita, Visita.actividad_id == ActividadTuristica.id).group_by(Categoria.nombre).all()

    nombres = [row[0] for row in visitas_por_categoria]
    counts = [row[1] for row in visitas_por_categoria]

    fig, ax = plt.subplots()
    ax.bar(nombres, counts)
    ax.set_xlabel('Categoría')
    ax.set_ylabel('Número de Visitas')
    ax.set_title('Visitas por Categoría')

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    return send_file(img, mimetype='image/png')

@admin_bp.route('/actividades_mas_vistas.png')
@login_required
def actividades_mas_vistas_chart():
    if not current_user.es_admin:
        abort(403)

    actividades_mas_vistas = db.session.query(
        ActividadTuristica.nombre, db.func.count(ActividadVista.id).label('count')
    ).join(ActividadVista, ActividadVista.actividad_id == ActividadTuristica.id).group_by(ActividadTuristica.nombre).order_by(db.func.count(ActividadVista.id).desc()).all()

    nombres = [row[0] for row in actividades_mas_vistas]
    counts = [row[1] for row in actividades_mas_vistas]

    fig, ax = plt.subplots()
    ax.bar(nombres, counts)
    ax.set_xlabel('Actividad')
    ax.set_ylabel('Número de Vistas')
    ax.set_title('Actividades Más Vistas')

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    return send_file(img, mimetype='image/png')

@admin_bp.route('/actividades_mas_visitadas.png')
@login_required
def actividades_mas_visitadas_chart():
    if not current_user.es_admin:
        abort(403)

    actividades_mas_visitadas = db.session.query(
        ActividadTuristica.nombre, db.func.count(Visita.id).label('count')
    ).join(Visita, Visita.actividad_id == ActividadTuristica.id).group_by(ActividadTuristica.nombre).order_by(db.func.count(Visita.id).desc()).all()

    nombres = [row[0] for row in actividades_mas_visitadas]
    counts = [row[1] for row in actividades_mas_visitadas]

    fig, ax = plt.subplots()
    ax.bar(nombres, counts)
    ax.set_xlabel('Actividad')
    ax.set_ylabel('Número de Visitas')
    ax.set_title('Actividades Más Visitadas')

    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    return send_file(img, mimetype='image/png')
"""
def render_pdf(template_src, context):
    template = render_template(template_src, **context)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(template.encode("UTF-8")), result)
    if not pdf.err:
        return make_response(result.getvalue())
    return None


@admin_bp.route('/dashboard/export')
@login_required
def export_dashboard_pdf():
    if not current_user.es_admin:
        abort(403)

    total_actividades = ActividadTuristica.query.count()
    total_usuarios = Usuario.query.count()
    total_visitas = Visita.query.count()

    visitas_por_categoria = db.session.query(
        Categoria.nombre, func.count(Visita.id)
    ).select_from(Visita).join(ActividadTuristica, ActividadTuristica.id == Visita.actividad_id).join(Categoria,
                                                                                                      Categoria.id == ActividadTuristica.categoria_id).group_by(
        Categoria.nombre).all()

    actividades_mas_vistas = db.session.query(
        ActividadTuristica.nombre, func.sum(ActividadVista.vistas).label('vistas')
    ).select_from(ActividadVista).join(ActividadTuristica,
                                       ActividadTuristica.id == ActividadVista.actividad_id).group_by(
        ActividadTuristica.nombre).order_by(func.count(ActividadVista.vistas).desc()).limit(5).all()

    actividades_mas_visitadas = db.session.query(
        ActividadTuristica.nombre, func.count(Visita.id).label('visitas')
    ).select_from(Visita).join(ActividadTuristica, ActividadTuristica.id == Visita.actividad_id).group_by(
        ActividadTuristica.nombre).order_by(func.count(Visita.id).desc()).limit(5).all()

    context = {
        'total_actividades': total_actividades,
        'total_usuarios': total_usuarios,
        'total_visitas': total_visitas,
        'visitas_por_categoria': visitas_por_categoria,
        'actividades_mas_vistas': actividades_mas_vistas,
        'actividades_mas_visitadas': actividades_mas_visitadas
    }

    pdf = render_pdf('dashboard_pdf.html', context)
    response = make_response(pdf)
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = 'attachment; filename=dashboard.pdf'
    return response

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
            # flash('Categoría creada con éxito!', 'success')
            return jsonify({'status': 'success', 'message': 'Categoría creada con éxito!'}), 200
        except IntegrityError as e:
            db.session.rollback()
            if 'categoria_nombre_key' in str(e.orig):
                # flash('Ya existe una categoría con ese nombre.', 'danger')
                return jsonify({'status': 'error', 'message': 'Ya existe una categoría con ese nombre.'}), 400
            else:
                # flash(f'Error al crear la categoría: {str(e)}', 'danger')
                return jsonify({'status': 'error', 'message': f'Error al crear la categoría: {str(e)}'}), 500
        except Exception as e:
            db.session.rollback()
            # flash(f'Error al crear la categoría: {str(e)}', 'danger')
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
        return jsonify({'status': 'error',
                        'message': 'Error: Asegúrate de eliminar todas las actividades asociadas a esta categoría antes de eliminarla.'}), 400

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
            descripcion=form.descripcion_equipamiento.data,
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
        return send_file(io.BytesIO(imagen.data), mimetype=imagen.mimetype, as_attachment=False,
                         download_name=imagen.name)
    return 'Image not found!', 404


@admin_bp.route('/categoria_imagen/<int:id>')
def get_categoria_image(id):
    categoria = Categoria.query.get(id)
    if categoria and categoria.image_data:
        return send_file(io.BytesIO(categoria.image_data), mimetype=categoria.image_mimetype, as_attachment=False,
                         download_name=categoria.image_name)
    return 'Image not found!', 404


@admin_bp.route('/eventos')
def eventos():
    page = request.args.get('page', 1, type=int)
    eventos = Evento.query.paginate(page=page, per_page=6)
    return render_template('admin/eventos.html', eventos=eventos)


@admin_bp.route('/evento/nuevo', methods=['GET', 'POST'])
def nuevo_evento():
    form = EventoForm()
    if form.validate_on_submit():
        evento = Evento(
            nombre=form.nombre.data,
            descripcion=form.descripcion.data,
            fecha=form.fecha.data,
            lugar=form.lugar.data
        )
        db.session.add(evento)
        db.session.commit()

        for file in form.imagenes.data:
            if file:
                filename = secure_filename(file.filename)
                mimetype = file.mimetype
                data = file.read()
                imagen = ImagenActividad(name=filename, data=data, mimetype=mimetype, evento_id=evento.id)
                db.session.add(imagen)

        db.session.commit()
        flash('Evento creado exitosamente', 'success')
        return redirect(url_for('admin.eventos'))
    return render_template('admin/nuevo_evento.html', form=form)


@admin_bp.route('/evento/editar/<int:evento_id>', methods=['GET', 'POST'])
def editar_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    form = EventoForm(obj=evento)
    if form.validate_on_submit():
        form.populate_obj(evento)
        db.session.commit()

        for file in form.imagenes.data:
            if file:
                filename = secure_filename(file.filename)
                mimetype = file.mimetype
                data = file.read()
                imagen = ImagenActividad(name=filename, data=data, mimetype=mimetype, evento_id=evento.id)
                db.session.add(imagen)

        db.session.commit()
        flash('Evento actualizado exitosamente', 'success')
        return redirect(url_for('admin.eventos'))
    return render_template('admin/editar_evento.html', form=form, evento=evento)


@admin_bp.route('/foto_visita/<int:id>')
@login_required
def get_foto_visita(id):
    foto = FotoVisita.query.get_or_404(id)
    return Response(foto.data, mimetype=foto.mimetype)


@admin_bp.route('/evento/eliminar/<int:evento_id>', methods=['POST'])
def eliminar_evento(evento_id):
    evento = Evento.query.get_or_404(evento_id)
    db.session.delete(evento)
    db.session.commit()
    flash('Evento eliminado exitosamente', 'success')
    return redirect(url_for('admin.eventos'))

@admin_bp.route('/visitas')
@login_required
def listar_visitas():
    page = request.args.get('page', 1, type=int)
    visitas = Visita.query.paginate(page=page, per_page=6)
    return render_template('listar_visitas.html', visitas=visitas)


@admin_bp.route('/visitas/editar/<int:visita_id>', methods=['GET', 'POST'])
@login_required
def editar_visita(visita_id):
    visita = Visita.query.get_or_404(visita_id)
    form = EditarVisitaForm(obj=visita)

    if form.validate_on_submit():
        form.populate_obj(visita)

        # Procesar eliminación de imágenes
        delete_image_ids = request.form.getlist('delete_images')
        for imagen_id in delete_image_ids:
            imagen = FotoVisita.query.get(imagen_id)
            if imagen:
                db.session.delete(imagen)

        # Procesar nuevas imágenes
        if 'nuevas_fotos' in request.files:
            files = request.files.getlist('nuevas_fotos')
            for file in files:
                if file and file.filename != '':
                    filename, mimetype, image_data = save_image(file)
                    if filename and mimetype and image_data:
                        nueva_foto = FotoVisita(
                            visita_id=visita.id,
                            data=image_data,
                            mimetype=mimetype,
                            filename=filename
                        )
                        db.session.add(nueva_foto)

        db.session.commit()
        flash('Visita actualizada con éxito!', 'success')
        return redirect(url_for('admin.listar_visitas'))

    return render_template('admin/editar_visita.html', form=form, visita=visita)



@admin_bp.route('/visitas/eliminar/<int:visita_id>', methods=['POST'])
@login_required
def eliminar_visita(visita_id):
    if not current_user.es_admin:
        abort(403)
    visita = Visita.query.get_or_404(visita_id)
    db.session.delete(visita)
    db.session.commit()
    flash('Visita eliminada exitosamente', 'success')
    return redirect(url_for('admin.listar_visitas'))