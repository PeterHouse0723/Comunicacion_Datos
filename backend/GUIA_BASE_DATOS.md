# 📊 Guía de Base de Datos - Sistema Académico

## 🎯 Resumen Ejecutivo

### Motor de BD recomendado: **PostgreSQL**

**Por qué PostgreSQL:**
- ✅ Mejor escalabilidad que SQLite
- ✅ Excelente soporte en Render (hosting en la nube)
- ✅ Maneja relaciones complejas perfectamente
- ✅ Soporta migraciones sin perder datos
- ✅ Estándar industrial para producción

**Usar ahora:** SQLite en desarrollo (ya configurado)  
**Para producción:** PostgreSQL en Render (veremos después)

---

## 📋 Estructura de Tablas

### 1. **Roles** (roles)
```sql
- id (PK)
- nombre (único): admin, docente, estudiante
- descripcion
```
**Propósito:** Control de acceso y permisos

---

### 2. **Usuarios** (usuarios)
```sql
- id (PK)
- email (único, indexado)
- password (encriptada)
- nombre
- apellido
- role_id (FK → roles)
- activo (bool)
- fecha_creacion
- fecha_actualizacion
```
**Propósito:** Almacena estudiantes, docentes y admin

---

### 3. **Cursos/Materias** (cursos)
```sql
- id (PK)
- nombre
- codigo (único)
- descripcion
- creditos
- fecha_inicio
- fecha_fin
- activo
```
**Propósito:** Materias dictadas

---

### 4. **Relación Docente-Curso** (curso_docente)
```sql
- id (PK)
- curso_id (FK → cursos)
- docente_id (FK → usuarios)
```
**Propósito:** Un docente dicta varios cursos, un curso tiene varios docentes

---

### 5. **Calificaciones** (notas)
```sql
- id (PK)
- estudiante_id (FK → usuarios, indexado)
- curso_id (FK → cursos, indexado)
- parcial_1
- parcial_2
- parcial_3
- examen_final
- promedio_final (calculado automáticamente)
- estado: en_curso | aprobado | reprobado
- fecha_registro
```
**Propósito:** Calificaciones por estudiante/curso  
**Función:** `calcular_promedio()` actualiza promedio automáticamente

---

### 6. **Asistencia** (asistencias)
```sql
- id (PK)
- estudiante_id (FK → usuarios, indexado)
- curso_id (FK → cursos, indexado)
- fecha
- presente (bool)
- justificacion
- fecha_registro
```
**Propósito:** Registro de asistencia diaria  
**Bonus:** Poder calcular porcentaje de asistencia

---

### 7. **Auditoría de Login** (login_auditoria) ✅
```sql
- id (PK)
- usuario_id (FK → usuarios, indexado)
- fecha_login
- ip_address (IPv4 e IPv6)
- navegador
- estado: exitoso | fallido
- razon_fallo (si es fallido)
```
**Propósito:** Registro completo de todos los inicios de sesión  
**Cumple requisito:** "Dejar registro en la BD de q inicio secion a modo de auditoria"

---

### 8. **Notificaciones** (notificaciones)
```sql
- id (PK)
- usuario_id (FK → usuarios, indexado)
- titulo
- mensaje
- tipo: info | warning | danger | success
- leida (bool)
- fecha_creacion
- fecha_lectura (null si no leída)
```
**Propósito:** Sistema de notificaciones en tiempo real

---

### 9. **Alertas de Riesgo Académico** (alertas_riesgo)
```sql
- id (PK)
- estudiante_id (FK → usuarios, indexado)
- curso_id (FK → cursos)
- tipo_alerta: bajo_promedio | faltas_excesivas | en_riesgo
- promedio_actual
- porcentaje_asistencia
- fecha_alerta
- estado: activa | resuelta
```
**Propósito:** Alertas automáticas para riesgo académico  
**Cumple requisito:** "Evaluar si el alumno está en riesgo de perder la calidad de estudiante"

---

## 🔄 Cómo Evolucionar la BD Conforme Avances

### Opción 1: Desarrollo (actual)
```bash
# Editas models.py
# El servidor reinicia automáticamente y recrela las tablas
# SQLite es suficiente
```

### Opción 2: Migraciones (recomendado para producción)
```bash
# Cuando cambies un modelo:
flask db migrate -m "Descripción del cambio"
flask db upgrade

# Esto guarda cambios en la carpeta migrations/
# No pierdes datos existentes
```

**Ejemplo:** Si quieres agregar un campo `telefono` a Usuario:
```python
# En models.py
class Usuario(db.Model):
    # ...
    telefono = db.Column(db.String(20))  # ← Agregar esta línea

# En terminal:
# $ flask db migrate -m "Add phone to users"
# $ flask db upgrade
```

---

## 🚀 Roadmap: De Desarrollo a Producción

### Fase 1: AHORA (Desarrollo local)
- ✅ SQLite en `backend/instance/app.db`
- ✅ Modelos definidos
- ✅ Modificaciones dinámicas

### Fase 2: Antes de Render
1. Crear cuenta en Render.com
2. Crear base de datos PostgreSQL en Render
3. Obtener `DATABASE_URL` de Render
4. Colocar en archivo `.env` de Render
5. Hacer `git push` → Render despliega automáticamente

### Fase 3: En Producción (Render)
```bash
# Render ejecutará automáticamente:
# 1. pip install -r requirements.txt
# 2. flask db upgrade (si hay migraciones)
# 3. python app.py

# Tu BD estará en PostgreSQL en la nube
```

---

## 💡 Respuestas a Tus Preguntas

### ¿Puedo modificar la BD conforme avance?

**SÍ, completamente:**

**Durante desarrollo (SQLite):**
- Edita `models.py`
- El servidor reinicia
- Las tablas se recrean
- ⚠️ Pierdes datos locales (no importa, son pruebas)

**En producción (PostgreSQL):**
- Usa migraciones con Alembic
- Los datos se preservan
- Puedes hacer cambios sin downtime

### ¿Qué pasa si agrego un nuevo campo?

```python
# En models.py - agregar campo
class Usuario(db.Model):
    celular = db.Column(db.String(20))

# Opción 1 - Desarrollo: El servidor lo crea automáticamente
# Opción 2 - Producción: 
#   $ flask db migrate -m "Add celular to users"
#   $ flask db upgrade
```

### ¿Y si me arrepiento y quiero eliminar algo?

```bash
# Haz una nueva migración
flask db migrate -m "Remove field_name from table"
# (Edit la migración si es necesario)
flask db upgrade
```

---

## 📦 Dependencias Instaladas

```
Flask==3.0.0                  # Framework web
Flask-SQLAlchemy==3.1.1       # ORM (mapeo DB)
SQLAlchemy==2.0.47            # Motor SQL
Flask-Migrate==4.1.0          # Migraciones (Alembic)
psycopg2-binary==2.9.11       # Driver PostgreSQL
python-dotenv==1.0.1          # Variables de entorno
```

---

## 🔐 Variables de Entorno (`.env`)

```
# Desarrollo
DATABASE_URL=sqlite:///app.db
FLASK_ENV=development

# Producción (en Render):
# DATABASE_URL=postgresql://user:pass@render-host:5432/db
# FLASK_ENV=production
```

---

## 📊 Diagrama de Relaciones

```
Roles (1) ──── (N) Usuarios
                      │
                ┌─────┼─────┐
                │     │     │
           Notas│     │ Asistencias│
                │     │     │
            Cursos ────────────┘
                │
        CursoDocente (Docentes)
```

---

## ✅ Próximos Pasos

1. **Ahora:** Tablas creadas ✅ (puedes ver en `instance/app.db`)
2. **Siguiente:** Implementar autenticación con contraseñas encriptadas
3. **Luego:** Rutas para crear/editar notas y asistencia
4. **Después:** Sistema de notificaciones
5. **Producción:** Deploy en Render con PostgreSQL

---

## 🎓 Características Implementadas

- ✅ Tablas para resumen académico (notas, asistencia)
- ✅ Evaluación de riesgo académico (alertas)
- ✅ Auditoría de login
- ✅ Sistema de roles (admin, docente, estudiante)
- ✅ Sistema de notificaciones
- ✅ Evolución de BD con migraciones

¿Necesitas ayuda con el siguiente paso? 🚀
