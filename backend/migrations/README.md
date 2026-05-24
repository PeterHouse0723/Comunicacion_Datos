# Migraciones de Actividades y Calificaciones

## Descripción

Se han creado dos nuevas tablas en la base de datos para el sistema de actividades y calificaciones:

1. **actividades** - Almacena las actividades de cada curso (9 actividades por curso)
2. **calificaciones** - Almacena las notas de los estudiantes en cada actividad

## Ejecución de Migraciones

### Opción 1: Usando Python Script (Recomendado)

Desde la terminal en el servidor o localmente:

```bash
cd backend
python run_migrations.py
```

Este script ejecutará automáticamente todas las migraciones pendientes en el orden correcto.

### Opción 2: Ejecutar manualmente desde PostgreSQL

Si estás en **Render**, usa la Shell de la aplicación:

```bash
psql $DATABASE_URL -f /app/backend/migrations/create_actividades.sql
psql $DATABASE_URL -f /app/backend/migrations/create_calificaciones.sql
```

Si estás **localmente** y usas SQLite, no necesitas hacer nada (SQLAlchemy crea las tablas automáticamente).

### Opción 3: Usar DBeaver o pgAdmin

1. Abre una conexión a tu base de datos PostgreSQL
2. Copia el contenido de `create_actividades.sql` y ejecútalo
3. Copia el contenido de `create_calificaciones.sql` y ejecútalo

## Verificar que las tablas se crearon

```sql
-- Verificar tabla actividades
SELECT COUNT(*) FROM actividades;

-- Verificar tabla calificaciones
SELECT COUNT(*) FROM calificaciones;
```

## Cargar datos de prueba

Una vez que las tablas están creadas, ejecuta:

```bash
cd backend
python scripts/simular_actividades.py
```

Esto creará 27 actividades (9 por curso) y 720 calificaciones simuladas.

## Estructura de tablas

### Tabla: actividades
- `id` - ID único
- `curso_id` - Referencia al curso
- `nombre` - Nombre de la actividad
- `tipo_evaluacion` - Tipo (taller, parcial, proyecto, examen, tarea)
- `semana` - Semana de clase
- `ponderacion` - Porcentaje de ponderación
- `fecha_vencimiento` - Fecha de entrega
- `activa` - Estado (true/false)

### Tabla: calificaciones
- `id` - ID único
- `actividad_id` - Referencia a la actividad
- `estudiante_id` - Referencia al estudiante
- `valor_nota` - Nota (0.0 - 5.0)
- `retroalimentacion` - Comentarios del docente
- `fecha_actualizacion` - Última actualización

## Pasos en Render

1. Ve a tu aplicación en Render
2. Click en "Shell" 
3. Ejecuta: `python backend/run_migrations.py`
4. Verifica que no haya errores
5. Recarga tu aplicación

¡Listo! Ahora deberías poder ver las calificaciones en la interfaz.
