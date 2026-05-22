from flask import Blueprint, request, jsonify, session
from chatbot.engine import responder

chatbot_bp = Blueprint('chatbot', __name__, url_prefix='/api/chatbot')


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

    try:
        respuesta, nuevo_estado, opciones = responder(usuario_id, role, texto, estado_chat)
        return jsonify({
            'respuesta': respuesta,
            'estado': nuevo_estado,
            'opciones': opciones
        })
    except Exception as e:
        return jsonify({
            'respuesta': 'Ocurrió un error al procesar tu consulta. Intenta de nuevo.',
            'estado': {},
            'opciones': []
        })
