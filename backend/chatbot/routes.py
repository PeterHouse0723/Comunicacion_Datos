import traceback
import logging
from flask import Blueprint, request, jsonify, session
from chatbot.engine import responder
from chatbot import bienestar

logger = logging.getLogger(__name__)

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api/chatbot')

_MAX_HISTORIAL = 20  # máximo de mensajes guardados (10 intercambios)


@chatbot_bp.route('/mensaje', methods=['POST'])
def mensaje():
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    data = request.get_json(silent=True) or {}
    texto = (data.get('mensaje') or '').strip()
    estado_chat = data.get('estado') or {}

    if not texto and not estado_chat.get('esperando_opcion'):
        return jsonify({'error': 'Mensaje vacío'}), 400

    usuario_id = session['usuario_id']
    role = session.get('role', '')

    historial_ia = session.get('chatbot_historial', [])

    # Detección de bienestar emocional (solo para estudiantes)
    if texto and role == 'estudiante':
        nivel, tipo, resumen = bienestar.detectar(texto)
        logger.info('[BIENESTAR] uid=%s texto="%s" nivel=%s tipo=%s', usuario_id, texto[:60], nivel, tipo)
        if nivel:
            # Construir historial con el mensaje actual incluido para el extracto
            historial_con_mensaje = historial_ia + [{'role': 'user', 'content': texto}]
            try:
                n_alertas = bienestar.crear_alerta(usuario_id, nivel, tipo, resumen,
                                                   historial=historial_con_mensaje)
                logger.info('[BIENESTAR] alerta creada: %d nuevas (uid=%s nivel=%s)', n_alertas, usuario_id, nivel)
            except Exception:
                logger.error('[BIENESTAR] ERROR en crear_alerta uid=%s', usuario_id, exc_info=True)
                traceback.print_exc()
            respuesta_bio = bienestar.respuesta_empatetica(nivel, tipo)
            # Guardar turno en historial de sesión
            historial_actualizado = historial_con_mensaje + [
                {'role': 'assistant', 'content': respuesta_bio}
            ]
            if len(historial_actualizado) > _MAX_HISTORIAL:
                historial_actualizado = historial_actualizado[-_MAX_HISTORIAL:]
            session['chatbot_historial'] = historial_actualizado
            session.modified = True
            return jsonify({
                'respuesta': respuesta_bio,
                'estado': estado_chat,
                'opciones': []
            })

    try:
        respuesta, nuevo_estado, opciones = responder(
            usuario_id, role, texto, estado_chat, historial_ia
        )

        # Actualizar historial solo para respuestas de IA (modo conversacional)
        if nuevo_estado.get('modo_ia') and texto:
            historial_ia = historial_ia + [
                {'role': 'user', 'content': texto},
                {'role': 'assistant', 'content': respuesta}
            ]
            # Limitar tamaño del historial
            if len(historial_ia) > _MAX_HISTORIAL:
                historial_ia = historial_ia[-_MAX_HISTORIAL:]
            session['chatbot_historial'] = historial_ia
            session.modified = True

        return jsonify({
            'respuesta': respuesta,
            'estado': nuevo_estado,
            'opciones': opciones
        })
    except Exception:
        traceback.print_exc()
        return jsonify({
            'respuesta': 'Ocurrió un error al procesar tu consulta. Intenta de nuevo.',
            'estado': {},
            'opciones': []
        })


@chatbot_bp.route('/limpiar-historial', methods=['POST'])
def limpiar_historial():
    """Limpia el historial de conversación con la IA."""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401
    session.pop('chatbot_historial', None)
    return jsonify({'ok': True})


@chatbot_bp.route('/diagnostico')
def diagnostico():
    """Diagnóstico del sistema de alertas de bienestar (solo usuarios autenticados)."""
    if 'usuario_id' not in session:
        return jsonify({'error': 'No autenticado'}), 401

    usuario_id = session['usuario_id']
    role = session.get('role', '')
    resultado = {
        'sesion': {'usuario_id': usuario_id, 'role': role},
        'pasos': [],
    }

    # Paso 1: detección
    msg_test = 'me quiero suicidar'
    nivel, tipo, resumen = bienestar.detectar(msg_test)
    resultado['pasos'].append({
        'paso': '1_deteccion',
        'mensaje_test': msg_test,
        'nivel': nivel,
        'tipo': tipo,
        'ok': nivel is not None,
    })

    # Paso 2: columnas de la tabla
    try:
        from extensions import db
        from sqlalchemy import inspect, text
        cols = [c['name'] for c in inspect(db.engine).get_columns('alertas_bienestar')]
        resultado['pasos'].append({'paso': '2_columnas_tabla', 'columnas': cols, 'ok': 'extracto' in cols})
    except Exception as e:
        resultado['pasos'].append({'paso': '2_columnas_tabla', 'error': str(e), 'ok': False})

    # Paso 3: inscripciones del usuario
    try:
        from models import EstudianteCurso
        inscripciones = EstudianteCurso.query.filter_by(estudiante_id=usuario_id).all()
        cursos = [{'curso_id': i.curso_id, 'activo': i.curso.activo if i.curso else None} for i in inscripciones]
        activos = [c for c in cursos if c['activo']]
        resultado['pasos'].append({'paso': '3_inscripciones', 'cursos': cursos, 'activos': len(activos), 'ok': len(activos) > 0})
    except Exception as e:
        resultado['pasos'].append({'paso': '3_inscripciones', 'error': str(e), 'ok': False})

    # Paso 4: intentar crear alerta de prueba
    try:
        n = bienestar.crear_alerta(usuario_id, nivel or 'critico', tipo or 'suicida',
                                   resumen or 'Test diagnóstico',
                                   historial=[{'role': 'user', 'content': msg_test}])
        resultado['pasos'].append({'paso': '4_crear_alerta', 'alertas_nuevas': n, 'ok': True})
    except Exception as e:
        resultado['pasos'].append({'paso': '4_crear_alerta', 'error': str(e), 'ok': False})

    # Paso 5: total de alertas en BD para este usuario
    try:
        from models import AlertaBienestar
        total = AlertaBienestar.query.filter_by(estudiante_id=usuario_id).count()
        ultimas = AlertaBienestar.query.filter_by(estudiante_id=usuario_id)\
            .order_by(AlertaBienestar.fecha.desc()).limit(5).all()
        resultado['pasos'].append({
            'paso': '5_alertas_bd',
            'total_este_usuario': total,
            'ultimas': [{'id': a.id, 'tipo': a.tipo, 'nivel': a.nivel_urgencia,
                         'fecha': str(a.fecha), 'revisada': a.revisada} for a in ultimas],
            'ok': True,
        })
    except Exception as e:
        resultado['pasos'].append({'paso': '5_alertas_bd', 'error': str(e), 'ok': False})

    resultado['resumen'] = 'OK' if all(p['ok'] for p in resultado['pasos']) else 'HAY ERRORES'
    return jsonify(resultado)
