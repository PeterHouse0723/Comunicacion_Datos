import traceback
from flask import Blueprint, request, jsonify, session
from chatbot.engine import responder

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
