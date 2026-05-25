"""
Detección de señales de bienestar emocional en mensajes del chatbot.
Retorna (nivel, tipo, resumen) o (None, None, None) si no hay señal.

Niveles:
  'critico' — pensamientos suicidas o autolesión
  'alto'    — depresión o ansiedad severa
  'medio'   — estrés extremo, desesperanza, llanto frecuente
"""
import re
from datetime import datetime

# ─── Patrones por nivel ───────────────────────────────────────────────────────

_CRITICO = re.compile(
    r'\b('
    r'me\s+quiero?\s+morir|quiero?\s+morir(me)?|no\s+quiero?\s+vivir'
    r'|quitarme\s+la\s+vida|acabar\s+con\s+(mi\s+)?vida|acabar\s+con\s+todo'
    r'|suicid(io|arme|ar(se)?)|matarme|no\s+quiero?\s+(estar\s+aqu[íi]|seguir\s+viviendo)'
    r'|desaparecer\s+para\s+siempre|mejor\s+estar\s+muerto|prefiero\s+morir'
    r'|pensar\s+en\s+quitarme|hacerme\s+da[ñn]o|autolesion|cortarme'
    r')',
    re.IGNORECASE,
)

_ALTO_DEP = re.compile(
    r'\b('
    r'deprimi(do|da|endo)|depresi[oó]n|me\s+siento\s+mal\s+(todo|siempre)'
    r'|no\s+tengo\s+ganas\s+de\s+nada|todo\s+es\s+in[uú]til|sin\s+esperanza'
    r'|no\s+vale\s+la\s+pena\s+vivir|desesperado|desesperanza'
    r'|lloro\s+(mucho|todo\s+el\s+tiempo|sin\s+parar|constantemente)'
    r'|me\s+siento\s+vac[ií]o|vac[ií]o\s+interior|no\s+me\s+importa\s+(nada|vivir)'
    r'|ya\s+no\s+puedo\s+m[aá]s|no\s+aguanto\s+m[aá]s|estoy\s+harto\s+de\s+todo'
    r'|no\s+sirvo\s+para\s+nada|soy\s+un\s+fracaso|fracasado'
    r')',
    re.IGNORECASE,
)

_ALTO_ANS = re.compile(
    r'\b('
    r'ansiedad|ansios[ao]|ataque\s+de\s+p[aá]nico|p[aá]nico\s+total'
    r'|no\s+puedo\s+respirar\s+bien|me\s+tiemblan|temblor\s+(de\s+manos|cuerpo)'
    r'|no\s+puedo\s+dormir\s+(de\s+preocupaci[oó]n|por\s+el\s+estr[eé]s)'
    r'|angustia\s+(mucha|terrible|constante)|angustiad[ao]'
    r'|miedo\s+de\s+todo|me\s+preocupa\s+todo\s+el\s+tiempo'
    r'|estr[eé]s\s+(extremo|insoportable|muy\s+grande)'
    r')',
    re.IGNORECASE,
)

_MEDIO = re.compile(
    r'\b('
    r'muy\s+estresad[ao]|estresad[ao]\s+al\s+m[aá]ximo|me\s+estreso\s+mucho'
    r'|no\s+puedo\s+con\s+(tant[ao]|todo\s+esto|el\s+estudio)'
    r'|me\s+siento\s+solo|me\s+siento\s+sola|nadie\s+me\s+entiende'
    r'|siento\s+que\s+fallo\s+a\s+(todos|mi\s+familia)'
    r'|me\s+da\s+miedo\s+el\s+futuro|no\s+s[eé]\s+si\s+puedo\s+(seguir|continuar)'
    r'|estoy\s+agotad[ao]|agotamiento\s+total|burnout'
    r'|me\s+cuesta\s+mucho\s+levantarme|no\s+quiero\s+salir|encerrad[ao]'
    r')',
    re.IGNORECASE,
)

# ─── Etiquetas legibles ───────────────────────────────────────────────────────

_RESUMEN = {
    ('critico', 'suicida'): 'El estudiante expresó pensamientos relacionados con hacerse daño o no querer vivir.',
    ('alto', 'depresion'): 'El estudiante manifestó síntomas importantes de depresión: desesperanza, vacío emocional o llanto frecuente.',
    ('alto', 'ansiedad'): 'El estudiante reportó síntomas de ansiedad severa o ataques de pánico.',
    ('medio', 'estres'): 'El estudiante expresó estrés extremo, agotamiento o sensación de no poder continuar.',
}

_TIPO_LABEL = {
    'suicida':   'Riesgo de autolesión / pensamiento suicida',
    'depresion': 'Síntomas de depresión',
    'ansiedad':  'Ansiedad severa',
    'estres':    'Estrés extremo / agotamiento',
}

_NIVEL_LABEL = {
    'critico': 'CRÍTICO',
    'alto':    'ALTO',
    'medio':   'MEDIO',
}


def detectar(mensaje: str):
    """
    Analiza un mensaje y retorna (nivel, tipo, resumen) o (None, None, None).
    """
    if _CRITICO.search(mensaje):
        return ('critico', 'suicida', _RESUMEN[('critico', 'suicida')])
    if _ALTO_DEP.search(mensaje):
        return ('alto', 'depresion', _RESUMEN[('alto', 'depresion')])
    if _ALTO_ANS.search(mensaje):
        return ('alto', 'ansiedad', _RESUMEN[('alto', 'ansiedad')])
    if _MEDIO.search(mensaje):
        return ('medio', 'estres', _RESUMEN[('medio', 'estres')])
    return (None, None, None)


def _formatear_extracto(historial: list) -> str:
    """Convierte el historial de mensajes en un texto legible para el docente."""
    if not historial:
        return ''
    lineas = []
    for msg in historial[-10:]:  # últimos 10 turnos máximo
        rol = 'Estudiante' if msg.get('role') == 'user' else 'Sofia'
        lineas.append(f"{rol}: {msg.get('content', '').strip()}")
    return '\n'.join(lineas)


def crear_alerta(estudiante_id: int, nivel: str, tipo: str, resumen: str,
                 historial=None):
    """
    Crea una AlertaBienestar para todos los cursos activos del estudiante.
    Idempotente: no crea duplicados en <6 horas por el mismo tipo.
    """
    from models import AlertaBienestar, EstudianteCurso, db
    from datetime import timedelta

    extracto = _formatear_extracto(historial or [])
    reciente = datetime.utcnow() - timedelta(hours=6)
    inscripciones = EstudianteCurso.query.filter_by(estudiante_id=estudiante_id).all()
    cursos_activos = [i for i in inscripciones if i.curso and i.curso.activo]

    nuevas = []
    for insc in cursos_activos:
        existe = (
            AlertaBienestar.query
            .filter_by(estudiante_id=estudiante_id, curso_id=insc.curso_id, tipo=tipo)
            .filter(AlertaBienestar.fecha >= reciente)
            .first()
        )
        if not existe:
            alerta = AlertaBienestar(
                estudiante_id=estudiante_id,
                curso_id=insc.curso_id,
                tipo=tipo,
                nivel_urgencia=nivel,
                resumen=resumen,
                extracto=extracto,
            )
            db.session.add(alerta)
            nuevas.append(alerta)

    if nuevas:
        db.session.commit()

    return len(nuevas)


def respuesta_empatetica(nivel: str, tipo: str) -> str:
    """
    Devuelve un mensaje de respuesta empático según el nivel detectado.
    No menciona al docente para no romper la confianza del estudiante.
    """
    if nivel == 'critico':
        return (
            "Gracias por confiar en mí y contarme cómo te sientes. "
            "Lo que describes es muy serio y quiero que sepas que no estás solo/a. "
            "Por favor, comunícate ahora con alguien de confianza o llama a la **Línea 106** "
            "(Colombia, gratuita, 24 horas, completamente confidencial). "
            "Tu vida tiene un valor enorme y hay personas que quieren ayudarte. "
            "¿Puedes contarme un poco más sobre cómo te sientes ahora mismo? 💙"
        )
    if nivel == 'alto' and tipo == 'depresion':
        return (
            "Escucho que estás pasando por un momento muy difícil, y eso importa mucho. "
            "Sentirse así durante un tiempo prolongado es agotador, y tiene todo el sentido "
            "que necesites apoyo. No tienes que cargarlo solo/a. "
            "¿Quieres contarme qué ha estado pasando? Estoy aquí para escucharte. 💙"
        )
    if nivel == 'alto' and tipo == 'ansiedad':
        return (
            "Entiendo que la ansiedad puede sentirse completamente abrumadora. "
            "Lo que describes es real y merece atención. "
            "Mientras hablamos, intenta respirar despacio: inhala 4 segundos, sostén 4, exhala 4. "
            "¿Qué es lo que más te está generando esta sensación últimamente? 💙"
        )
    return (
        "Noto que estás bajo mucha presión en este momento. "
        "Es válido sentirse así, y no tienes que aguantarlo todo solo/a. "
        "Cuéntame, ¿qué es lo que más te está pesando? Estoy aquí contigo. 💙"
    )
