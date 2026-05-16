# Error: Tabla "mensajes" No Existe - Solución

## 🔴 El Problema

Al intentar enviar mensajes en Render, aparece el error:

```
sqlalchemy.exc.ProgrammingError: (psycopg2.errors.UndefinedTable) relation "mensajes" does not exist
```

Esto significa que la tabla `mensajes` **no existe** en la base de datos de Render.

## ✅ La Solución

He actualizado los archivos para que la tabla se cree automáticamente. Tienes 2 opciones:

### **Opción 1: Hacer Push a Render (RECOMENDADO ✨)**

Esta es la forma más simple. Al hacer push, Render ejecutará automáticamente las migraciones.

**Pasos:**

1. Asegúrate de que todos los cambios estén guardados
2. Abre la terminal PowerShell en VS Code
3. Ejecuta:

```powershell
cd c:\ProCD\Comunicacion_Datos
git add .
git commit -m "Agregar tabla de mensajes y campana de notificaciones"
git push origin main
```

4. Espera a que Render termine el deploy (2-5 minutos)
5. Intenta enviar un mensaje nuevamente

**¿Qué sucede automáticamente?**
- Render ejecuta la función `apply_migrations()` en `app.py`
- Esta función lee el archivo `backend/migrations/create_mensajes.sql`
- Crea la tabla `mensajes` en PostgreSQL

### **Opción 2: Ejecutar Script Localmente (Si no quieres hacer push aún)**

```powershell
cd c:\ProCD\Comunicacion_Datos\backend
python create_tables.py
```

Esto crear la tabla en tu BD local, pero **aún necesitarás hacer push a Render** para que se cree en producción.

## 📊 Archivos Modificados

```
✅ backend/app.py 
   - Agregado 'Mensaje' al import de modelos
   - Agregado 'create_mensajes.sql' a la lista de migraciones

✅ backend/migrations/create_mensajes.sql
   - Convertido a sintaxis PostgreSQL
   - Ahora usa SERIAL en lugar de AUTO_INCREMENT
   - Compatible con Render

✅ backend/create_tables.py
   - Script para ejecutar migraciones manualmente
```

## 🔍 Cómo Funciona la Migración

Cuando tu aplicación inicia (en cualquier entorno), la función `apply_migrations()` en `app.py`:

1. ✅ Lee todos los archivos SQL en `backend/migrations/`
2. ✅ Ejecuta los comandos SQL en orden
3. ✅ Si la tabla ya existe, la ignora (no produce error)
4. ✅ Si la tabla no existe, la crea
5. ✅ Crea automáticamente los índices para optimización

```python
# En app.py
with app.app_context():
    try:
        apply_migrations(app)  # ← Esto ejecuta create_mensajes.sql
    except Exception as e:
        logger.error(f"Error al aplicar migraciones: {e}")
```

## 📝 Estructura de la Tabla Mensajes

```sql
CREATE TABLE mensajes (
    id SERIAL PRIMARY KEY,
    remitente_id INTEGER NOT NULL,
    destinatario_id INTEGER NOT NULL,
    curso_id INTEGER NOT NULL,
    contenido TEXT NOT NULL,
    leido BOOLEAN DEFAULT FALSE,
    fecha_lectura TIMESTAMP,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (remitente_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (destinatario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (curso_id) REFERENCES cursos(id) ON DELETE CASCADE
);
```

**Índices creados:**
- `idx_mensaje_remitente_destinatario` - Para búsquedas de conversaciones
- `idx_mensaje_curso` - Para filtrar por curso
- `idx_mensaje_fecha_creacion` - Para ordenar por fecha
- `idx_mensaje_leido` - Para encontrar no leídos
- `idx_mensaje_destinatario` - Para ver mensajes recibidos

## 🚀 Después de Resolver

Una vez que la tabla esté creada:

1. ✅ El docente puede enviar mensajes a estudiantes
2. ✅ Los estudiantes pueden recibir y responder
3. ✅ La campana de notificaciones funciona
4. ✅ Los mensajes se guardan en BD

## 🐛 Si Aún Hay Problemas

### Problema: Aún dice "relation does not exist" después de push

**Solución:**
1. Verifica que `create_mensajes.sql` esté en `backend/migrations/`
2. Asegúrate de que está en sintaxis PostgreSQL (no MySQL)
3. Haz un nuevo push a Render
4. Revisa los logs de Render en el dashboard

### Problema: Error en la migración

**Solución:**
Si ves un error en los logs de Render, es probablemente porque:
- La tabla ya existe (esto es OK, se ignora)
- Hay conflicto con claves foráneas
- PostgreSQL tiene restricciones diferentes

En ese caso, copia este comando SQL y ejecuta manualmente en la consola de Render:

```sql
-- Ejecutar en la BD de Render si la tabla aún no existe

CREATE TABLE IF NOT EXISTS mensajes (
    id SERIAL PRIMARY KEY,
    remitente_id INTEGER NOT NULL,
    destinatario_id INTEGER NOT NULL,
    curso_id INTEGER NOT NULL,
    contenido TEXT NOT NULL,
    leido BOOLEAN DEFAULT FALSE,
    fecha_lectura TIMESTAMP,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_mensaje_remitente FOREIGN KEY (remitente_id) 
        REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_mensaje_destinatario FOREIGN KEY (destinatario_id) 
        REFERENCES usuarios(id) ON DELETE CASCADE,
    CONSTRAINT fk_mensaje_curso FOREIGN KEY (curso_id) 
        REFERENCES cursos(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_mensaje_remitente_destinatario ON mensajes (remitente_id, destinatario_id);
CREATE INDEX IF NOT EXISTS idx_mensaje_curso ON mensajes (curso_id);
CREATE INDEX IF NOT EXISTS idx_mensaje_fecha_creacion ON mensajes (fecha_creacion);
CREATE INDEX IF NOT EXISTS idx_mensaje_leido ON mensajes (leido);
CREATE INDEX IF NOT EXISTS idx_mensaje_destinatario ON mensajes (destinatario_id);
```

## 📞 Resumen Rápido

| Paso | Acción |
|------|--------|
| 1 | Abre terminal PowerShell |
| 2 | `git add .` |
| 3 | `git commit -m "Tabla de mensajes"` |
| 4 | `git push origin main` |
| 5 | Espera 2-5 minutos |
| 6 | Intenta enviar mensaje |
| 7 | ✅ Funciona! |

---

**Actualizado**: 16 de Mayo de 2026  
**Estado**: Listo para resolver el problema
