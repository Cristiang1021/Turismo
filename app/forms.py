from datetime import date

from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField, RadioField, \
    DateField, TextAreaField, MultipleFileField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Regexp, NumberRange
from app.models import Usuario, Categoria #ActividadTuristica


class LoginForm(FlaskForm):
    correo = StringField('Correo', validators=[DataRequired(), Email()])
    contraseña = PasswordField('Contraseña', validators=[DataRequired()])
    remember_me = BooleanField('Recuérdame')
    submit = SubmitField('Iniciar Sesión')

class RegistrationForm(FlaskForm):
    nombre = StringField('Nombre', validators=[DataRequired()])
    correo = StringField('Correo', validators=[DataRequired(), Email()])
    contraseña = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.'),
        Regexp(
            r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*()_\-+={}\[\]:;<>?,./~`|])[A-Za-z\d!@#$%^&*()_\-+={}\[\]:;<>?,./~`|]{8,}$',
            message='Debe incluir mayúsculas, minúsculas, números y caracteres especiales.')
    ])
    contraseña2 = PasswordField('Confirmar Contraseña', validators=[
        DataRequired(),
        EqualTo('contraseña', message='Las contraseñas no coinciden.')
    ])
    es_admin = BooleanField('Administrador')
    submit = SubmitField('Registrar')

    def validate_correo(self, correo):
        usuario = Usuario.query.filter_by(correo=correo.data).first()
        if usuario:
            raise ValidationError('El correo ya está en uso. Por favor, elige un correo diferente.')


class RecomendacionForm(FlaskForm):
    pregunta1 = RadioField('Tipo de actividad', choices=[('Aventura', 'Aventura'), ('Fotografía', 'Fotografía'), ('Deportes', 'Deportes'), ('Recreación', 'Recreación'), ('Senderismo', 'Senderismo')], validators=[DataRequired()])
    pregunta2 = RadioField('Nivel de dificultad', choices=[('Fácil', 'Fácil'), ('Medio', 'Medio'), ('Difícil', 'Difícil')], validators=[DataRequired()])
    pregunta3 = RadioField('Nivel físico requerido', choices=[('Bajo', 'Bajo'), ('Medio', 'Medio'), ('Alto', 'Alto')], validators=[DataRequired()])
    pregunta4 = RadioField('Duración de la actividad', choices=[('Menos de 2 horas', 'Menos de 2 horas'), ('2-4 horas', '2-4 horas'), ('Más de 4 horas', 'Más de 4 horas')], validators=[DataRequired()])
    pregunta5 = RadioField('Requiere guía', choices=[('Sí', 'Sí'), ('No', 'No')], validators=[DataRequired()])
    pregunta6 = RadioField('Época preferida', choices=[('Todo el año', 'Todo el año'), ('Invierno', 'Invierno'), ('Verano', 'Verano')], validators=[DataRequired()])
    pregunta7 = RadioField('Precio', choices=[('Menos de $50', 'Menos de $50'), ('$50-$100', '$50-$100'), ('Más de $100', 'Más de $100')], validators=[DataRequired()])
    submit = SubmitField('Enviar')

class RegistroVisitaForm(FlaskForm):
    actividad_id = SelectField('Actividad', coerce=int, validators=[DataRequired()])
    fecha_visita = DateField('Fecha de Visita', validators=[DataRequired()])
    valoracion = IntegerField('Valoración', validators=[DataRequired(), NumberRange(min=1, max=5)])
    reseña = TextAreaField('Reseña')
    fotos = MultipleFileField('Fotografías', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'], 'Solo se permiten imágenes')])
    submit = SubmitField('Registrar Visita')

    def validate_fecha_visita(form, field):
        if field.data > date.today():
            raise ValidationError('La fecha de visita no puede ser en el futuro.')
        if field.data < date.today().replace(year=date.today().year - 1):
            raise ValidationError('La fecha de visita no puede ser anterior a un año.')


class EditarRespuestasForm(FlaskForm):
    pregunta1 = SelectField('Tipo de actividad',
                            choices=[('Aventura', 'Aventura'), ('Fotografía', 'Fotografía'), ('Deportes', 'Deportes'),
                                     ('Recreación', 'Recreación'), ('Senderismo', 'Senderismo')],
                            validators=[DataRequired()])
    pregunta2 = SelectField('Nivel de dificultad',
                            choices=[('Fácil', 'Fácil'), ('Medio', 'Medio'), ('Difícil', 'Difícil')],
                            validators=[DataRequired()])
    pregunta3 = SelectField('Nivel físico requerido', choices=[('Bajo', 'Bajo'), ('Medio', 'Medio'), ('Alto', 'Alto')],
                            validators=[DataRequired()])
    pregunta4 = SelectField('Duración de la actividad',
                            choices=[('Menos de 2 horas', 'Menos de 2 horas'), ('2-4 horas', '2-4 horas'),
                                     ('Más de 4 horas', 'Más de 4 horas')], validators=[DataRequired()])
    pregunta5 = SelectField('Requiere guía', choices=[('Sí', 'Sí'), ('No', 'No')], validators=[DataRequired()])
    pregunta6 = SelectField('Época recomendada',
                            choices=[('Todo el año', 'Todo el año'), ('Invierno', 'Invierno'), ('Verano', 'Verano')],
                            validators=[DataRequired()])
    pregunta7 = SelectField('Precio', choices=[('Menos de $50', 'Menos de $50'), ('$50-$100', '$50-$100'),
                                               ('Más de $100', 'Más de $100')], validators=[DataRequired()])
    submit = SubmitField('Enviar')


class RequestResetForm(FlaskForm):
    correo = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    submit = SubmitField('Solicitar Restablecimiento de Contraseña')

   ## def validate_correo(self, correo):
    ##    user = Usuario.query.filter_by(correo=correo.data).first()
      ##  if user is None:
        ##    raise ValidationError('No hay cuenta con ese correo electrónico. Debe registrarse primero.')

class ResetPasswordForm(FlaskForm):
    contraseña = PasswordField('Contraseña', validators=[
        DataRequired(),
        Length(min=8, message='La contraseña debe tener al menos 8 caracteres.'),
        EqualTo('contraseña2', message='Las contraseñas deben coincidir.')
    ])
    contraseña2 = PasswordField('Confirmar Contraseña', validators=[DataRequired()])
    submit = SubmitField('Restablecer Contraseña')