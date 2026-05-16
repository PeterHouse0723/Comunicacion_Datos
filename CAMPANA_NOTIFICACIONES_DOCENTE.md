# Campana de Notificaciones para Docentes - Guía de Implementación

## 📋 Cambios Realizados

Se ha implementado un sistema de notificaciones/campana de mensajes en el dashboard del docente, permitiendo que visualice todos los mensajes recibidos de sus estudiantes de manera centralizada.

## 🔧 Componentes Modificados/Creados

### 1. Template: Docente Dashboard
**Archivo**: `backend/templates/docente/dashboard.html`

**Cambios**:
- Agregado botón "Mensajes" con campana en el header
- Badge rojo que muestra el contador de mensajes no leídos
- Modal para visualizar conversaciones de todos los cursos
- Layout responsivo para mobile

**Estructura del Header**:
```html
<button class="btn-mensajes-campana" onclick="abrirModalMensajesDocente()">
    <i class="fas fa-bell"></i> Mensajes
    <span id="badgeMensajesDocente" class="badge-mensajes">0</span>
</button>
```

### 2. Rutas API Nuevas
**Archivo**: `backend/routes/dashboard.py`

#### GET `/dashboard/api/mensajes-docente-no-leidos`
- Retorna la cantidad total de mensajes no leídos del docente
- De todos sus cursos combinados
- Response:
```json
{
    "success": true,
    "total": 5
}
```

#### GET `/dashboard/api/mensajes-docente-global`
- Retorna lista de estudiantes que han enviado mensajes
- Incluye información del curso
- Ordenados por fecha del último mensaje (más recientes primero)
- Response:
```json
{
    "success": true,
    "estudiantes": [
        {
            "id": 1,
            "nombre": "Juan",
            "apellido": "Pérez",
            "email": "juan@example.com",
            "curso_id": 5,
            "curso_codigo": "MAT101",
            "curso_nombre": "Matemáticas",
            "no_leidos": 3,
            "ultimo_mensaje_fecha": "2026-05-16T14:30:00"
        }
    ]
}
```

### 3. Estilos CSS Actualizados
**Archivo**: `backend/static/css/docente.css`

**Nuevas clases CSS**:
- `.btn-mensajes-campana` - Botón de campana
- `.badge-mensajes` - Badge con contador
- `.modal-mensajes` - Modal contenedor
- `.modal-content-mensajes` - Contenido del modal
- `.modal-header-mensajes` - Header del modal
- `.conversaciones-list` - Lista de conversaciones
- `.conversacion-item` - Elemento individual
- `.mensajes-area` - Área de mensajes
- `.mensaje-item` - Mensaje individual
- `.modal-footer-mensajes` - Footer con input

## 🎨 Características Visuales

### Colores
- **Primario**: Verde (#4CAF50) - Consistente con tema docente
- **Badge**: Rojo (#ff4444) - Destaca mensajes no leídos
- **Hover**: Verde oscuro (#45a049)

### Animaciones
- Modal: Fade in + slide in
- Botón: Hover effect
- Mensajes: Scroll automático al final

### Responsividad
- ✅ Desktop: Layout completo con dos paneles
- ✅ Tablet: Conversaciones en scroll horizontal
- ✅ Mobile: Full width con layout adaptado

## 🚀 Cómo Funciona

### Para el Docente:

1. **Ver Notificaciones**:
   - Hace clic en el botón "Mensajes" con campana
   - Se muestra el número de mensajes no leídos (si hay)

2. **Abrir Modal**:
   - Modal se abre con dos paneles
   - Panel izquierdo: Lista de estudiantes que enviaron mensajes
   - Panel derecho: Conversación con el estudiante seleccionado

3. **Ver Conversación**:
   - Clic en un estudiante carga la conversación
   - Se muestra historial de mensajes
   - Mensajes enviados: Verde
   - Mensajes recibidos: Gris

4. **Responder Mensaje**:
   - Escribe en el textarea
   - Clic en botón "Enviar" o Enter
   - Mensaje se guarda en DB
   - Conversación se actualiza automáticamente

5. **Auto-actualización**:
   - Badge se actualiza cada 30 segundos
   - Muestra cantidad actualizada de no leídos

## 📊 Flujo de Datos

```
1. Docente abre dashboard
   ↓
2. JavaScript ejecuta: actualizarBadgeMensajesDocente()
   ↓
3. GET /api/mensajes-docente-no-leidos
   ↓
4. Badge se actualiza con cantidad
   ↓
5. Docente hace clic en "Mensajes"
   ↓
6. GET /api/mensajes-docente-global
   ↓
7. Se cargan todas las conversaciones
   ↓
8. Docente selecciona un estudiante
   ↓
9. GET /api/mensajes/<estudiante_id>/<curso_id>
   ↓
10. Se muestra conversación
    ↓
11. Docente escribe y envía
    ↓
12. POST /api/mensajes
    ↓
13. Mensaje se guarda
    ↓
14. GET /api/mensajes/<estudiante_id>/<curso_id> para refrescar
```

## 🔐 Seguridad

- ✅ Solo docentes pueden acceder a `/api/mensajes-docente-*`
- ✅ Valida que usuario sea docente (role == 'docente')
- ✅ Solo muestra cursos propios del docente
- ✅ Validación de permisos en todas las rutas
- ✅ Sanitización HTML en frontend

## 🔄 Variables JavaScript

```javascript
docenteMensajesData = {
    usuarioId: 1,                      // ID del docente autenticado
    conversacionActualId: null,        // "estudianteId_cursoId"
    cursoActual: null                  // ID del curso actual
}
```

## 📱 Funciones JavaScript Principales

```javascript
// Abrir/Cerrar Modal
abrirModalMensajesDocente()
cerrarModalMensajesDocente()

// Cargar datos
cargarConversacionesDocente()
obtenerMensajesGlobales()
seleccionarConversacionDocente(estudianteId, cursoId, nombre)
cargarMensajesDocente(estudianteId, cursoId)

// Enviar
enviarMensajeDocente()

// Notificaciones
actualizarBadgeMensajesDocente()

// Utilidad
escapeHtml(text)
```

## ⚙️ Configuración

- **Actualización de badge**: Cada 30 segundos
- **Máximo de mensajes por carga**: 50
- **Máximo de caracteres por mensaje**: 5000
- **Timeout de peticiones**: 30 segundos (por defecto)

## 🐛 Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| Badge no muestra número | Rutas API no existen | Verificar que las rutas estén en dashboard.py |
| Modal no abre | JavaScript error | Abrir consola (F12) y revisar errores |
| No se cargan conversaciones | Sin mensajes | Los estudiantes deben enviar mensajes primero |
| Mensaje no se envía | Error en ruta | Verificar que ruta POST /api/mensajes funcione |
| Auto-actualización no funciona | setInterval no ejecuta | Verificar que JavaScript esté habilitado |

## 📝 Notas Técnicas

1. **Sincronización**:
   - Las conversaciones se cargan bajo demanda (al abrir modal)
   - El badge se actualiza automáticamente cada 30 segundos
   - Los mensajes se marcan como leídos automáticamente

2. **Permisos**:
   - Docente solo ve mensajes de sus estudiantes en sus cursos
   - No puede ver mensajes de otros docentes
   - No puede enviar mensajes a usuarios que no estén en sus cursos

3. **Performance**:
   - Índices en DB optimizados para búsquedas rápidas
   - Límite de 50 mensajes por carga para no saturar
   - Paginación mediante offset/limit

## 🚀 Próximas Mejoras Sugeridas

- [ ] WebSockets para actualización en tiempo real
- [ ] Búsqueda de conversaciones
- [ ] Marcar como no leído
- [ ] Archivos adjuntos
- [ ] Notificaciones de navegador
- [ ] Perfil del estudiante en modal
- [ ] Mensajes de grupo (toda la clase)

## 📚 Archivos Modificados

```
✅ backend/templates/docente/dashboard.html - Agregado modal y botón
✅ backend/routes/dashboard.py - Nuevas rutas API
✅ backend/static/css/docente.css - Nuevos estilos y media queries
```

## ✅ Checklist de Implementación

- [x] Modelo Mensaje creado
- [x] Migración SQL creada
- [x] Rutas API del estudiante
- [x] Template estudiante actualizado
- [x] Rutas API del docente (global)
- [x] Template docente actualizado
- [x] Estilos CSS agregados
- [x] Responsividad
- [x] Validaciones de seguridad

---

**Implementado**: 16 de Mayo de 2026  
**Estado**: ✅ Completamente funcional y listo para usar
