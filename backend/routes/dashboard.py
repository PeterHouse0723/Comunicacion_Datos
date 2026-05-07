"""Rutas de dashboards para cada rol"""
from flask import Blueprint, render_template, session, redirect, url_for, request
from functools import wraps
from models import Usuario, Curso, EstudianteCurso, SolicitudEstudianteMateria
from extensions import db
from datetime import datetime

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

# ============================================================================
# DECORADOR: Verificar sesión
# ============================================================================

def login_required(f):
    """Decorador para rutas que requieren autenticación"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================================================
# RUTA: Dashboard Admin (redirige al nuevo admin.dashboard)
# ============================================================================

@dashboard_bp.route('/admin')
@login_required
def admin():
    """Redirige al nuevo panel administrativo"""
    if session.get('role') not in ['admin_global', 'admin_local']:
        return redirect(url_for('auth.login'))
    
    return redirect(url_for('admin.dashboard'))

# ============================================================================
# RUTA: Dashboard Docente
# ============================================================================

@dashboard_bp.route('/docente')
@login_required
def docente():
    """Dashboard para docentes"""
    if session.get('role') != 'docente':
        return redirect(url_for('auth.login'))
    
    usuario = Usuario.query.get(session.get('usuario_id'))
    materias = Curso.query.filter_by(docente_principal_id=usuario.id, activo=True).all()
    return render_template('dashboard/docente.html', usuario=usuario, materias=materias)

# ============================================================================
# RUTA: SOLICITAR ESTUDIANTE A MATERIA (DOCENTE)
# ============================================================================

@dashboard_bp.route('/docente/solicitudes', methods=['POST'])
@login_required
def solicitar_estudiante_materia():
    """Crear solicitud para agregar estudiante a una materia"""
    if session.get('role') != 'docente':
        return jsonify({'success': False, 'error': 'No tienes permiso'}), 403

    data = request.get_json() or {}
    materia_id = data.get('materia_id')
    email = (data.get('email') or '').strip().lower()
    motivo = (data.get('motivo') or '').strip()

    if not materia_id or not email:
        return jsonify({'success': False, 'error': 'Materia y email requeridos'}), 400

    docente = Usuario.query.get(session.get('usuario_id'))
    materia = Curso.query.get(materia_id)
    if not materia or materia.docente_principal_id != docente.id:
        return jsonify({'success': False, 'error': 'Materia no válida'}), 404

    estudiante = Usuario.query.filter_by(email=email, role='estudiante').first()
    if not estudiante or estudiante.institucion_id != docente.institucion_id:
        return jsonify({'success': False, 'error': 'Estudiante no encontrado'}), 404

    inscrito = EstudianteCurso.query.filter_by(
        estudiante_id=estudiante.id,
        curso_id=materia.id
    ).first()
    if inscrito:
        return jsonify({'success': False, 'error': 'El estudiante ya está inscrito'}), 409

    existe = SolicitudEstudianteMateria.query.filter_by(
        curso_id=materia.id,
        estudiante_id=estudiante.id,
        docente_id=docente.id,
        estado='pendiente'
    ).first()
    if existe:
        return jsonify({'success': False, 'error': 'Ya existe una solicitud pendiente'}), 409

    solicitud = SolicitudEstudianteMateria(
        curso_id=materia.id,
        estudiante_id=estudiante.id,
        docente_id=docente.id,
        motivo=motivo
    )

    db.session.add(solicitud)
    db.session.commit()

    return jsonify({'success': True, 'mensaje': 'Solicitud enviada'}), 201

# ============================================================================
# RUTA: Dashboard Estudiante
# ============================================================================

@dashboard_bp.route('/estudiante')
@login_required
def estudiante():
    """Dashboard para estudiantes"""
    if session.get('role') != 'estudiante':
        return redirect(url_for('auth.login'))
    
    usuario = Usuario.query.get(session.get('usuario_id'))
    return render_template('dashboard/estudiante.html', usuario=usuario)
