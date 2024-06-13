from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField, IntegerField, RadioField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Regexp
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
        Regexp(r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$',
               message='Debe incluir mayúsculas, minúsculas, números y caracteres especiales.')
    ])
    contraseña2 = PasswordField('Confirma Contraseña', validators=[
        DataRequired(),
        EqualTo('contraseña', message='Las contraseñas no coinciden.')
    ])
    es_admin = BooleanField('Administrador')
    submit = SubmitField('Registrar')

    def validate_correo(self, correo):
        usuario = Usuario.query.filter_by(correo=correo.data).first()
        if usuario:
            raise ValidationError('El correo ya está en uso. Por favor, elige un correo diferente.')

class PreferenciasForm(FlaskForm):
    nivel_dificultad = SelectField('Nivel de Dificultad', choices=[('Fácil', 'Fácil'), ('Medio', 'Medio'), ('Difícil', 'Difícil')])
    tipo_superficie = SelectField('Tipo de Superficie', choices=[('Roca', 'Roca'), ('Arena', 'Arena'), ('Nieve', 'Nieve')])
    temperatura_minima = IntegerField('Temperatura Mínima')
    temperatura_maxima = IntegerField('Temperatura Máxima')
    submit = SubmitField('Guardar Preferencias')


class RecomendacionForm(FlaskForm):
    pregunta1 = RadioField('Tipo de actividad', choices=[('Aventura', 'Aventura'), ('Fotografía', 'Fotografía'), ('Deportes', 'Deportes'), ('Recreación', 'Recreación'), ('Senderismo', 'Senderismo')], validators=[DataRequired()])
    pregunta2 = RadioField('Nivel de dificultad', choices=[('Fácil', 'Fácil'), ('Moderado', 'Moderado'), ('Difícil', 'Difícil')], validators=[DataRequired()])
    pregunta3 = RadioField('Nivel físico requerido', choices=[('Bajo', 'Bajo'), ('Medio', 'Medio'), ('Alto', 'Alto')], validators=[DataRequired()])
    pregunta4 = RadioField('Duración de la actividad', choices=[('Menos de 2 horas', 'Menos de 2 horas'), ('2-4 horas', '2-4 horas'), ('Más de 4 horas', 'Más de 4 horas')], validators=[DataRequired()])
    pregunta5 = RadioField('Requiere guía', choices=[('Sí', 'Sí'), ('No', 'No')], validators=[DataRequired()])
    pregunta6 = RadioField('Época recomendada', choices=[('Todo el año', 'Todo el año'), ('Invierno', 'Invierno'), ('Verano', 'Verano')], validators=[DataRequired()])
    pregunta7 = RadioField('Precio', choices=[('Menos de $50', 'Menos de $50'), ('$50-$100', '$50-$100'), ('Más de $100', 'Más de $100')], validators=[DataRequired()])
    submit = SubmitField('Enviar')