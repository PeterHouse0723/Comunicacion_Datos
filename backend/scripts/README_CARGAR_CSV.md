# 📋 Guía: Cargar CSV de Estudiantes sin Timeouts

## ¿Cómo funciona?

En lugar de usar el formulario web (que causa timeouts), usas un **script de línea de comandos** que procesa el CSV **directamente sin pasar por Gunicorn**.

---

## 🚀 Pasos Rápidos

### 1️⃣ Prepara el CSV
Tu archivo debe tener 3 columnas:
```
email,nombre,apellido
estudiante1@mail.com,Juan,Pérez
estudiante2@mail.com,María,García
```

### 2️⃣ Sube a Render

**Local (tu computadora):**
```bash
cd c:\ProCD\Comunicacion_Datos
git add backend/scripts/cargar_estudiantes_cli.py
git commit -m "Add: Script para cargar CSV sin timeouts"
git push
```

### 3️⃣ En Render - Abre Shell

1. Ve a [render.com](https://render.com)
2. Click en tu **Web Service**
3. Pestaña **"Shell"** (arriba a la derecha)
4. Se abrirá una terminal

### 4️⃣ Ejecuta el Script

**En la shell de Render:**

```bash
cd backend
python scripts/cargar_estudiantes_cli.py Recursos/estudiantes_39.csv 1 1
```

**Parámetros:**
- `Recursos/estudiantes_39.csv` = ruta al archivo CSV
- `1` = ID del curso (puedes cambiar según tu curso)
- `1` = ID de la institución (puedes cambiar según tu institución)

### 5️⃣ Ver Resultado

Si todo funciona, verás:
```
✅ CARGA COMPLETADA
==================================================
📊 Resumen:
   ✓ Creados: 39
   ✓ Inscritos: 39
   ⚠️  Errores: 0
==================================================
```

---

## 📝 Ejemplos

### Ejemplo 1: Cargar estudiantes en curso 1, institución 1
```bash
python scripts/cargar_estudiantes_cli.py Recursos/estudiantes_39.csv 1 1
```

### Ejemplo 2: Cargar en curso 5, institución 2
```bash
python scripts/cargar_estudiantes_cli.py Recursos/estudiantes_39.csv 5 2
```

### Ejemplo 3: Cargar desde otra ubicación
```bash
python scripts/cargar_estudiantes_cli.py /path/to/miarchivo.csv 1 1
```

---

## ⚡ Ventajas

✅ **No hay timeouts** - Se ejecuta directamente en la shell  
✅ **Rápido** - Procesa el CSV sin pasar por Gunicorn  
✅ **Ligero** - No requiere cambios en la web  
✅ **Escalable** - Puedes cargar archivos muy grandes  

---

## ❌ Errores Comunes

### Error: `Archivo no encontrado`
**Solución:** Verifica que la ruta sea correcta. Usa rutas relativas desde `backend/`:
```bash
# ✅ Correcto
python scripts/cargar_estudiantes_cli.py Recursos/estudiantes_39.csv 1 1

# ❌ Incorrecto
python scripts/cargar_estudiantes_cli.py ../Recursos/estudiantes_39.csv 1 1
```

### Error: `Curso con ID X no encontrado`
**Solución:** Usa el ID de curso correcto. Si no sabes cuál es:
1. Ve a la interfaz web
2. Abre un curso
3. Mira la URL: `https://tuapp.com/admin/cursos/5` → ID = 5

### Error: `El curso no pertenece a la institución X`
**Solución:** Asegúrate de usar el ID de institución correcto (normalmente es 1)

---

## 🎯 Flujo Completo

1. **Local:** Edita tu CSV, asegúrate que tenga email, nombre, apellido
2. **Local:** Sube a Render con `git push`
3. **Render:** Abre Shell en Dashboard
4. **Render:** Ejecuta `python scripts/cargar_estudiantes_cli.py Recursos/estudiantes_39.csv 1 1`
5. **Render:** Ves el resultado ✅
6. **Web:** Verifica en la interfaz que los estudiantes fueron cargados

---

## 📞 ¿Necesitas Ayuda?

Si algo no funciona:
1. Copia el mensaje de error completo
2. Verifica que el CSV esté bien formado
3. Comprueba que `curso_id` e `institucion_id` existen en la BD

**Eso es todo! 🎉**
