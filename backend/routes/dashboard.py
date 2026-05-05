"""Rutas de dashboards para cada rol"""
from flask import Blueprint, render_template, session, redirect, url_for
from functools import wraps
from models import Usuario

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
# RUTA: Dashboard Admin
# ============================================================================

@dashboard_bp.route('/admin')
@login_required
def admin():
    """Dashboard para administradores"""
    if session.get('role') not in ['admin_global', 'admin_local']:
        return redirect(url_for('auth.login'))
    
    usuario = Usuario.query.get(session.get('usuario_id'))
    return render_template('dashboard/admin.html', usuario=usuario)

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
    return render_template('dashboard/docente.html', usuario=usuario)

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
