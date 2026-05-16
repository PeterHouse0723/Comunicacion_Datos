# Sistema de Mensajería - Documentación de Implementación

## 📋 Resumen

Se ha implementado un sistema completo de mensajería bidireccional entre docentes y estudiantes dentro del contexto de un curso específico. El sistema permite:

- **Para Docentes**: Enviar mensajes individuales a estudiantes desde el listado de estudiantes del curso
- **Para Estudiantes**: Recibir mensajes y responder a docentes desde la vista del curso

## 🔧 Componentes Implementados

### 1. **Modelo de Base de Datos** (`models.py`)
```python
class Mensaje(db.Model):
    - id: Identificador único
    - remitente_id: Usuario que envía el mensaje
    - destinatario_id: Usuario que recibe el mensaje
    - curso_id: Curso donde se envía el mensaje
    - contenido: Texto del mensaje (hasta 5000 caracteres)
    - leido: Estado de lectura
    - fecha_lectura: Cuándo fue leído
    - fecha_creacion: Cuándo se envió
```

**Características**:
- Relaciones con Usuario y Curso
- Índices para consultas rápidas
- Método `marcar_como_leido()` para actualizar estado

### 2. **Migración SQL** (`migrations/create_mensajes.sql`)
Crea la tabla `mensajes` con:
- Claves foráneas a usuarios y cursos
- Índices compuestos para búsquedas eficientes
- Cascada DELETE para integridad referencial

### 3. **Rutas API** (`routes/dashboard.py`)

#### POST `/dashboard/api/mensajes`
- Envía un nuevo mensaje
- Validaciones:
  - Contenido no vacío y máximo 5000 caracteres
  - Usuario y destinatario existen
  - Ambos pertenecen al mismo curso
  - Permisos validados por rol (docente/estudiante)

#### GET `/dashboard/api/mensajes/<otro_usuario_id>/<curso_id>`
- Obtiene la conversación con otro usuario
- Parámetros: `limit` (máx 50), `offset` (para paginación)
- Marca automáticamente como leídos los mensajes recibidos

#### GET `/dashboard/api/mensajes/no-leidos/<curso_id>`
- Retorna cantidad de mensajes no leídos en un curso

#### PUT `/dashboard/api/mensajes/<mensaje_id>/marcar-leido`
- Marca un mensaje como leído
- Solo el destinatario puede hacerlo

#### GET `/dashboard/api/mensajes/remitentes/<curso_id>`
- Lista de conversaciones activas
- Incluye cantidad de no leídos
- Ordenadas por fecha del último mensaje

### 4. **Frontend - Docente** (`templates/docente/curso_estudiantes.html`)

**Características**:
- Icono "Mensaje" en cada fila de estudiante
- Modal flotante al hacer clic
- Muestra conversación anterior (si existe)
- Textarea para escribir nuevo mensaje
- Distinción visual entre mensajes enviados/recibidos
- Feedback visual (loading, error, éxito)

**Estilos**:
- Modal responsivo con animaciones
- Colores: Verde (#4CAF50) para el tema docente
- Botones con hover effects

### 5. **Frontend - Estudiante** (`templates/estudiante/curso_detalle.html`)

**Características**:
- Botón "Mensajes" con campana en el header
- Badge rojo con cantidad de mensajes no leídos
- Modal con dos paneles:
  - Izquierda: Lista de conversaciones
  - Derecha: Mensajes con la persona seleccionada
- Interfaz similar a WhatsApp/Telegram
- Auto-actualización de badge cada 30 segundos

**Estilos**:
- Modal responsivo (se adapta a mobile)
- Colores: Azul (#2196F3) para el tema estudiante
- Notificación de no leídos
- Interfaz intuitiva y moderna

## 🚀 Instrucciones de Uso

### Para el Docente:

1. Ir a "Cursos" → Seleccionar un curso → "Estudiantes"
2. En el listado de estudiantes, hacer clic en el botón verde "Mensaje"
3. Se abre un modal con:
   - Conversación anterior (si existe)
   - Área de texto para escribir
   - Botón "Enviar Mensaje"
4. Escribir el mensaje y enviar
5. El mensaje aparece inmediatamente en la conversación

### Para el Estudiante:

1. Al entrar a una materia (curso_detalle), hay un botón "Mensajes" en el header
2. Si hay mensajes no leídos, se muestra un número rojo
3. Al hacer clic en "Mensajes":
   - Se abre modal con lista de conversaciones
   - Clic en una conversación muestra los mensajes
   - Escribir en el textarea y enviar
4. Los mensajes se actualizan automáticamente

## 🔐 Seguridad

- ✅ Validación de permisos (usuario debe estar en el curso)
- ✅ Solo docentes y estudiantes pueden enviar mensajes
- ✅ Validación de longitud de contenido
- ✅ Sanitización HTML en frontend
- ✅ Validación de IDs de usuarios y cursos
- ✅ Solo destinatario puede marcar como leído

## 📊 Base de Datos

### Tabla `mensajes`

```sql
CREATE TABLE mensajes (
    id INTEGER PRIMARY KEY AUTO_INCREMENT,
    remitente_id INTEGER NOT NULL,
    destinatario_id INTEGER NOT NULL,
    curso_id INTEGER NOT NULL,
    contenido LONGTEXT NOT NULL,
    leido BOOLEAN DEFAULT FALSE,
    fecha_lectura DATETIME,
    fecha_creacion DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (remitente_id) REFERENCES usuarios(id),
    FOREIGN KEY (destinatario_id) REFERENCES usuarios(id),
    FOREIGN KEY (curso_id) REFERENCES cursos(id),
    
    INDEX idx_mensaje_remitente_destinatario (remitente_id, destinatario_id),
    INDEX idx_mensaje_curso (curso_id),
    INDEX idx_mensaje_fecha_creacion (fecha_creacion),
    INDEX idx_mensaje_leido (leido),
    INDEX idx_mensaje_destinatario (destinatario_id)
);
```

## 🔄 Flujo de Datos

```
1. Docente abre modal → GET /api/mensajes/remitentes/<curso_id>
   ↓
2. Se cargan conversaciones previas
   ↓
3. Docente escribe mensaje → POST /api/mensajes
   ↓
4. Mensaje se guarda en DB
   ↓
5. GET /api/mensajes/<otro_usuario_id>/<curso_id> para actualizar
   ↓
6. Estudiante ve badge con contador de no leídos → GET /api/mensajes/no-leidos/<curso_id>
   ↓
7. Estudiante abre modal y ve conversaciones → GET /api/mensajes/remitentes/<curso_id>
   ↓
8. Selecciona conversación → GET /api/mensajes/<docente_id>/<curso_id>
   ↓
9. Mensajes se marcan como leídos automáticamente
```

## 🎨 Colores y Estilos

**Docente**:
- Verde primario: #4CAF50
- Hover: #45a049

**Estudiante**:
- Azul primario: #2196F3
- Hover: #0b7dda
- Badge no leídos: #ff4444 (rojo)

## 📱 Responsividad

- ✅ Modal funciona en mobile
- ✅ Layout adaptativo para pantallas pequeñas
- ✅ Conversaciones en horizontal en mobile (swipe)
- ✅ Textarea con tamaño mínimo accesible

## 🔮 Futuras Mejoras

- [ ] Notificaciones en tiempo real (WebSockets)
- [ ] Adjuntos de archivos
- [ ] Reacciones con emojis
- [ ] Búsqueda en mensajes
- [ ] Marcar como no leído
- [ ] Mensajes eliminados/editados
- [ ] Grupo de mensajes (para toda la clase)
- [ ] Notificaciones por email

## 🐛 Troubleshooting

**Problema**: Los mensajes no se guardan
- Solución: Verificar que la migración se ejecutó (`migrations/create_mensajes.sql`)

**Problema**: Badge no actualiza
- Solución: El badge se actualiza cada 30 segundos o al abrir modal

**Problema**: Modal no abre
- Solución: Verificar que JavaScript esté habilitado en el navegador

## 📝 Notas Técnicas

- Los mensajes se almacenan en UTC
- Las fechas se convierten al navegador del usuario (cliente)
- Máximo 5000 caracteres por mensaje
- Las conversaciones son bidireccionales
- No hay límite de mensajes por conversación
- Cada mensaje es un registro independiente

---

**Implementado**: 16 de Mayo de 2026
**Estado**: ✅ Completo y funcional
