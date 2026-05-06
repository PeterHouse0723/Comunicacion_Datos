/**
 * ADMIN JAVASCRIPT UTILITIES
 * Funciones comunes para el panel administrativo
 */

// Cerrar modal al hacer click fuera
document.addEventListener('DOMContentLoaded', function() {
    // Cerrar modales al hacer click fuera
    window.addEventListener('click', function(e) {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            if (e.target === modal) {
                modal.style.display = 'none';
            }
        });
    });

    // Cerrar modal con tecla ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const modals = document.querySelectorAll('.modal[style*="display: flex"]');
            modals.forEach(modal => {
                modal.style.display = 'none';
            });
        }
    });
});

/**
 * Mostrar notificación toast
 */
function showToast(message, isSuccess = true) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    
    toast.className = 'toast-notification show';
    toast.style.background = isSuccess ? '#4caf50' : '#f44336';
    toast.innerHTML = `
        <i class="fas fa-${isSuccess ? 'check-circle' : 'exclamation-circle'}"></i>
        <span>${message}</span>
    `;
    
    setTimeout(() => {
        toast.classList.remove('show');
    }, 3500);
}

/**
 * Confirmar acción
 */
function confirmar(mensaje) {
    return confirm(mensaje);
}

/**
 * Formatear fecha
 */
function formatearFecha(fecha) {
    const options = { year: 'numeric', month: '2-digit', day: '2-digit' };
    return new Date(fecha).toLocaleDateString('es-ES', options);
}

/**
 * Cargar institución
 */
async function cargarInstitucion() {
    try {
        const response = await fetch('/admin/instituciones');
        return response.json();
    } catch (error) {
        console.error('Error al cargar institución:', error);
        return null;
    }
}
