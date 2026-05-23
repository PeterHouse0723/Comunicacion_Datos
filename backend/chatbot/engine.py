import re
from math import floor
from models import EstudianteCurso, Mensaje, Curso
from extensions import db

# Solo se mantiene "ayuda/menu" como comando especial para mostrar el menú
_PATRON_AYUDA = re.compile(
    r'^\s*(ayuda|menu|menú|opciones|qu[eé]\s+puedes\s+hacer|start)\s*$',
    re.IGNORECASE
)
_PATRON_MENSAJES = re.compile(
    r'^\s*(mensajes?|cuantos?\s+mensajes?|tengo\s+mensajes?)\s*$',
    re.IGNORECASE
)

_DIAS = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom']


def responder(usuario_id, role, mensaje_usuario, estado_chat, historial_ia=None):
    """
    Returns (respuesta_texto, nuevo_estado, opciones_list)
    opciones_list: [{'texto': str, 'valor': str}]
    historial_ia: list of {'role': 'user'|'assistant', 'content': str}
    """
    estado_chat = estado_chat or {}

    # Comando exacto: ayuda/menú → muestra opciones estáticas
    if _PATRON_AYUDA.match(mensaje_usuario):
        return _respuesta_ayuda(role)

    # Comando exacto: mensajes sin leer
    if _PATRON_MENSAJES.match(mensaje_usuario):
        return _respuesta_mensajes(usuario_id)

    # Todo lo demás → IA conversacional con contexto académico completo
    from chatbot.ia import responder_con_ia
    respuesta = responder_con_ia(usuario_id, role, mensaje_usuario, historial_ia or [])
    return (respuesta, {'modo_ia': True}, [])


def _respuesta_ayuda(role):
    if role == 'estudiante':
        texto = (
            '¡Hola! Soy tu asistente académico 🤖\n\n'
            'Puedo ayudarte con:\n\n'
            '• **mis cursos** — ver tus materias inscritas\n'
            '• **mis faltas** — cuántas faltas tienes por materia\n'
            '• **estado materia** — ¿estás en riesgo de perder por inasistencia?\n'
            '• **mensajes** — cuántos mensajes tienes sin leer\n\n'
            '¿Qué quieres consultar?'
        )
    elif role == 'docente':
        texto = (
            '¡Hola! Soy tu asistente 🤖\n\n'
            'Puedo ayudarte con:\n\n'
            '• **mensajes** — cuántos mensajes tienes sin leer\n\n'
            '¿Qué quieres consultar?'
        )
    else:
        texto = (
            '¡Hola! Soy tu asistente 🤖\n\n'
            'Puedo ayudarte con:\n\n'
            '• **mensajes** — cuántos mensajes tienes sin leer\n\n'
            '¿Qué quieres consultar?'
        )
    return (texto, {}, [])


def _respuesta_cursos(usuario_id, role):
    if role != 'estudiante':
        return ('Esta consulta solo está disponible para estudiantes.', {}, [])
    inscripciones = EstudianteCurso.query.filter_by(estudiante_id=usuario_id).all()
    activos = [(i.curso.codigo, i.curso.nombre, i.curso.get_dias_semana_list())
               for i in inscripciones if i.curso and i.curso.activo]
    if not activos:
        return ('No tienes cursos activos actualmente.', {}, [])
    lineas = []
    for codigo, nombre, dias in activos:
        dias_str = ', '.join(_DIAS[d] for d in dias) if dias else 'Sin días'
        lineas.append(f'• **{codigo}** — {nombre} ({dias_str})')
    return ('Tus cursos inscritos:\n\n' + '\n'.join(lineas), {}, [])


def _pedir_curso(usuario_id, intent_origen):
    inscripciones = EstudianteCurso.query.filter_by(estudiante_id=usuario_id).all()
    cursos_activos = [
        (i.curso.id, i.curso.nombre, i.curso.codigo)
        for i in inscripciones if i.curso and i.curso.activo
    ]
    if not cursos_activos:
        return ('No tienes cursos activos actualmente.', {}, [])
    opciones = [{'texto': f'{c[2]} — {c[1]}', 'valor': str(c[0])} for c in cursos_activos]
    nuevo_estado = {
        'paso': 'eligiendo_curso',
        'intent_origen': intent_origen,
        'esperando_opcion': True
    }
    return ('¿De qué materia quieres consultar?', nuevo_estado, opciones)


def _manejar_opcion(usuario_id, role, valor, estado_chat):
    if estado_chat.get('paso') == 'eligiendo_curso':
        try:
            curso_id = int(valor)
        except (ValueError, TypeError):
            return ('Opción inválida. Escribe **ayuda** para reiniciar.', {}, [])

        curso = Curso.query.get(curso_id)
        if not curso:
            return ('Curso no encontrado.', {}, [])

        insc = EstudianteCurso.query.filter_by(
            estudiante_id=usuario_id, curso_id=curso_id
        ).first()
        if not insc:
            return ('No tienes acceso a ese curso.', {}, [])

        intent_origen = estado_chat.get('intent_origen')
        if intent_origen == 'mis_faltas':
            return _respuesta_faltas(usuario_id, curso)
        elif intent_origen == 'estado_materia':
            return _respuesta_estado_materia(usuario_id, curso)

    return ('No entendí tu selección. Escribe **ayuda** para reiniciar.', {}, [])


def _respuesta_faltas(usuario_id, curso):
    resumen = curso.resumen_asistencia_estudiante(usuario_id)
    total = resumen.get('total_clases_programadas', 0)
    ausentes = resumen.get('ausentes', 0)
    justificadas = resumen.get('justificadas', 0)
    presentes = resumen.get('presentes', 0)
    registradas = resumen.get('clases_registradas', 0)
    
    # Total de faltas = ausentes + justificadas
    total_faltas = ausentes + justificadas

    texto = f'**{curso.codigo} — {curso.nombre}**\n\n'
    texto += f'• Clases programadas: {total}\n'
    texto += f'• Clases registradas: {registradas}\n'
    texto += f'• Asistencias: {presentes}\n'
    texto += f'• Faltas totales: {total_faltas}\n'
    
    if total_faltas > ausentes:
        texto += f'  - Sin justificación: {ausentes}\n'
        texto += f'  - Justificadas/Acuerdos: {justificadas}\n'

    if registradas > 0:
        pct = round((total_faltas / registradas) * 100, 1)
        texto += f'• Porcentaje de inasistencia: {pct}%'

    return (texto, {}, [])


def _respuesta_estado_todos(usuario_id):
    inscripciones = EstudianteCurso.query.filter_by(estudiante_id=usuario_id).all()
    cursos_activos = [i.curso for i in inscripciones if i.curso and i.curso.activo]
    if not cursos_activos:
        return ('No tienes cursos activos actualmente.', {}, [])

    lineas = []
    for curso in cursos_activos:
        resumen = curso.resumen_asistencia_estudiante(usuario_id)
        total = resumen.get('total_clases_programadas', 0)
        ausentes = resumen.get('ausentes', 0)
        justificadas = resumen.get('justificadas', 0)
        
        # Total de faltas = ausentes + justificadas
        total_faltas = ausentes + justificadas

        if total == 0:
            lineas.append(f'• **{curso.codigo}** — {curso.nombre}\n  Sin datos de clases aún.')
            continue

        max_faltas = floor(total * 0.30)
        restantes = max_faltas - total_faltas

        if restantes <= 0:
            icono = '⛔'
            estado = f'Límite superado ({total_faltas}/{max_faltas} faltas)'
        elif restantes <= 2:
            icono = '⚠️'
            estado = f'En riesgo — {restantes} falta{"" if restantes==1 else "s"} restante{"" if restantes==1 else "s"}'
        else:
            icono = '✅'
            estado = f'{restantes} faltas restantes ({total_faltas}/{max_faltas})'

        lineas.append(f'{icono} **{curso.codigo}** — {curso.nombre}\n  {estado}')

    texto = 'Estado de asistencia por materia:\n\n' + '\n\n'.join(lineas)
    return (texto, {}, [])


def _respuesta_estado_materia(usuario_id, curso):
    resumen = curso.resumen_asistencia_estudiante(usuario_id)
    total = resumen.get('total_clases_programadas', 0)
    ausentes = resumen.get('ausentes', 0)
    justificadas = resumen.get('justificadas', 0)
    
    # Total de faltas = ausentes + justificadas
    total_faltas = ausentes + justificadas

    if total == 0:
        return (
            f'**{curso.codigo} — {curso.nombre}**\n\n'
            'No hay información de clases programadas para este curso.',
            {}, []
        )

    max_faltas = floor(total * 0.30)
    faltas_restantes = max_faltas - total_faltas

    texto = f'**{curso.codigo} — {curso.nombre}**\n\n'
    texto += f'• Total clases en el periodo: {total}\n'
    texto += f'• Máximo faltas permitidas (30%): {max_faltas}\n'
    texto += f'• Faltas acumuladas: {total_faltas}\n'
    
    if total_faltas > ausentes:
        texto += f'  - Sin justificación: {ausentes}\n'
        texto += f'  - Justificadas/Acuerdos: {justificadas}\n'

    if faltas_restantes <= 0:
        texto += (
            '\n⛔ **Ya superaste el límite de faltas.** '
            'Estás en riesgo de perder la materia por inasistencia.'
        )
    elif faltas_restantes <= 2:
        veces = 'vez' if faltas_restantes == 1 else 'veces'
        texto += (
            f'\n⚠️ **Estás en riesgo.** Solo puedes faltar '
            f'**{faltas_restantes}** {veces} más sin perder la materia.'
        )
    else:
        texto += (
            f'\n✅ Puedes faltar **{faltas_restantes}** veces más '
            'antes de alcanzar el límite.'
        )

    return (texto, {}, [])


def _respuesta_mensajes(usuario_id):
    count = Mensaje.query.filter_by(destinatario_id=usuario_id, leido=False).count()
    if count == 0:
        return ('No tienes mensajes sin leer. ✅', {}, [])
    s = 's' if count > 1 else ''
    return (f'Tienes **{count}** mensaje{s} sin leer.', {}, [])
