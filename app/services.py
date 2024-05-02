# from .models import PreferenciaUsuario, ActividadTuristica

def obtener_recomendaciones(usuario_id):
    preferencias = PreferenciaUsuario.query.filter_by(usuario_id=usuario_id).first()
    actividades = ActividadTuristica.query
    if preferencias:
        actividades = actividades.filter(
            ActividadTuristica.nivel_dificultad == preferencias.nivel_dificultad,
            ActividadTuristica.tipos_superficie.any(tipo=preferencias.tipo_superficie),
            ActividadTuristica.temperatura_minima >= preferencias.temperatura_minima,
            ActividadTuristica.temperatura_maxima <= preferencias.temperatura_maxima
        )
    return actividades.all()
