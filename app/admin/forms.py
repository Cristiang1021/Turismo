from wtforms import PasswordField, HiddenField
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileRequired
from wtforms import PasswordField, HiddenField
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, SelectField, FileField
from wtforms.validators import DataRequired
from wtforms.validators import Email, EqualTo, Length, ValidationError, Regexp, Optional

from app.models import Categoria
from app.models import Usuario


class UsuarioForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    correo = StringField('Correo', validators=[DataRequired(), Email()])
    password = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.'),
        Regexp(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
               message='La contraseña debe contener al menos una letra mayúscula, una letra minúscula, un número y un carácter especial.')
    ])
    confirm_password = PasswordField('Confirmar Contraseña', validators=[DataRequired(), EqualTo('password', message='Las contraseñas deben coincidir.')])
    es_admin = BooleanField('Es administrador')
    submit = SubmitField('Registrar')

    def validate_correo(self, correo):
        usuario = Usuario.query.filter_by(correo=correo.data).first()
        if usuario:
            raise ValidationError('El correo ya está en uso. Por favor, elige un correo diferente.')


class EditarUsuarioForm(FlaskForm):
    usuario_id = HiddenField()
    nombre = StringField('Nombre', validators=[DataRequired()])
    correo = StringField('Correo', validators=[DataRequired(), Email()])
    password = PasswordField('Nueva Contraseña', validators=[
        Optional(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.'),
        Regexp(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
               message='La contraseña debe contener al menos una letra mayúscula, una letra minúscula, un número y un carácter especial.')
    ])
    confirm_password = PasswordField('Confirmar Nueva Contraseña', validators=[
        Optional(),
        EqualTo('password', message='Las contraseñas deben coincidir.')
    ])
    es_admin = BooleanField('Es administrador')
    submit = SubmitField('Actualizar Usuario')

    def __init__(self, *args, **kwargs):
        super(EditarUsuarioForm, self).__init__(*args, **kwargs)
        self.original_email = kwargs.get('original_email', None)

    def validate_correo(self, correo):
        if correo.data != self.original_email:
            usuario = Usuario.query.filter_by(correo=correo.data).first()
            if usuario:
                raise ValidationError('El correo ya está en uso. Por favor, elige un correo diferente.')


class CategoriaForm(FlaskForm):
    nombre = StringField('Nombre de la categoría', validators=[DataRequired()])
    descripcion = StringField('Descripcion de la categoría', validators=[DataRequired()])
    imagen = FileField('Imagen', validators=[Optional(),
        FileRequired(),
        FileAllowed(['jpg', 'png', 'webp', 'jpeg'], 'Solo imágenes!')
    ])
    submit = SubmitField('Guardar Categoría')


class ActividadTuristicaForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    descripcion_equipamiento = TextAreaField('Descripción del Equipamiento', validators=[DataRequired()])
    nivel_dificultad = SelectField('Nivel de Dificultad',
                                   choices=[('Fácil', 'Fácil'), ('Medio', 'Medio'), ('Difícil', 'Difícil')])
    nivel_fisico_requerido = SelectField('Nivel Físico Requerido',
                                         choices=[('Bajo', 'Bajo'), ('Medio', 'Medio'), ('Alto', 'Alto')])
    tiempo_promedio_duracion = StringField('Tiempo Promedio de Duración', validators=[DataRequired()])
    sitio = StringField('Sitio', validators=[DataRequired()])
    cota_maxima = StringField('Cota Máxima')
    cota_minima = StringField('Cota Mínima')
    desnivel_subida = StringField('Desnivel Subida')
    desnivel_bajada = StringField('Desnivel Bajada')
    lugar_partida = StringField('Lugar de Partida', validators=[DataRequired()])
    lugar_llegada = StringField('Lugar de Llegada', validators=[DataRequired()])
    epoca_recomendada = StringField('Época Recomendada', validators=[DataRequired()])
    tipo_superficie = StringField('Tipo de Superficie', validators=[DataRequired()])
    temperatura_minima = StringField('Temperatura Mínima')
    temperatura_maxima = StringField('Temperatura Máxima')
    precipitacion_media_anual = StringField('Precipitación Media Anual')
    requerimiento_guia = SelectField('Requerimiento Guia',
                                     choices=[('Si', 'Si'), ('No', 'No')])
    localizacion_geografica = StringField('Localización Geográfica', validators=[DataRequired()])
    acceso = TextAreaField('Acceso', validators=[DataRequired()])
    precio_referencial = StringField('Precio Referencial', validators=[DataRequired()])
    categoria_id = SelectField('Categoría', coerce=int, validators=[DataRequired()])
    imagenes = FileField('Imágenes', validators=[
        FileAllowed(['jpg', 'png', 'webp', 'jpeg'], 'Imágenes solamente!')], render_kw={"multiple": True})
    es_portada = BooleanField('Es portada')
    submit = SubmitField('Guardar Actividad')

    def __init__(self, *args, **kwargs):
        super(ActividadTuristicaForm, self).__init__(*args, **kwargs)
        self.categoria_id.choices = [(c.id, c.nombre) for c in Categoria.query.all()]
