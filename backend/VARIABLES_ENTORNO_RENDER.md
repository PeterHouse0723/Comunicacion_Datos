# 🔧 Variables de Entorno para Render - Guía Detallada

## 📊 Datos de tu Base de Datos (Render PostgreSQL)

```
Internal URL: postgresql://academico:gWOOqCygeQ74lVs3wyZJXinlG6Dz9H6p@dpg-d815pu7avr4c73b4aq00-a/academico_vu50
Hostname:     dpg-d815pu7avr4c73b4aq00-a
Port:         5432
Database:     academico_vu50
Username:     academico
Password:     gWOOqCygeQ74lVs3wyZJXinlG6Dz9H6p
```

---

## ✅ Variables de Entorno que DEBES Configurar en Render

### **Opción Recomendada: Usa la Internal URL Completa (MÁS FÁCIL)**

En el Dashboard de Render, ve a tu **Web Service** → **Environment** y agrega estas 3 variables:

### Variable 1️⃣: DATABASE_URL (LA MÁS IMPORTANTE)
```
DATABASE_URL=postgresql://academico:gWOOqCygeQ74lVs3wyZJXinlG6Dz9H6p@dpg-d815pu7avr4c73b4aq00-a/academico_vu50
```
⚠️ **IMPORTANTE**: 
- Copia EXACTAMENTE la Internal URL que te proporcionó Render
- Esta es la que empieza con `postgresql://academico:...`
- NO uses la External URL (la que termina en `.render.com`)

---

### Variable 2️⃣: FLASK_ENV
```
FLASK_ENV=production
```
⚠️ Esto le dice a Flask que corra en modo producción (sin debug)

---

### Variable 3️⃣: SECRET_KEY
Genera una clave aleatoria segura. Ejecuta en tu terminal:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Recibirás algo como:
```
a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

Luego en Render agrega:
```
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

---

## 📋 RESUMEN: 3 Variables en Render

| Variable | Valor |
|----------|-------|
| `DATABASE_URL` | `postgresql://academico:gWOOqCygeQ74lVs3wyZJXinlG6Dz9H6p@dpg-d815pu7avr4c73b4aq00-a/academico_vu50` |
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | *(ejecuta el comando python de arriba)* |

---

## 🎯 Cómo Configurar en Render Paso a Paso

### Paso 1: Ir al Dashboard
1. Abre [render.com](https://render.com)
2. Ve a tu **Web Service** (el que vas a crear o ya creaste)

### Paso 2: Abrir Environment Variables
1. Click en tu Web Service
2. Click en pestaña **"Environment"** (o "Env vars")
3. Click en **"Add Environment Variable"**

### Paso 3: Agregar DATABASE_URL
1. **Key**: `DATABASE_URL`
2. **Value**: (pega exactamente esto)
   ```
   postgresql://academico:gWOOqCygeQ74lVs3wyZJXinlG6Dz9H6p@dpg-d815pu7avr4c73b4aq00-a/academico_vu50
   ```
3. Click **"Save"**

### Paso 4: Agregar FLASK_ENV
1. Click **"Add Environment Variable"**
2. **Key**: `FLASK_ENV`
3. **Value**: `production`
4. Click **"Save"**

### Paso 5: Agregar SECRET_KEY
1. Click **"Add Environment Variable"**
2. **Key**: `SECRET_KEY`
3. **Value**: (copia el resultado del comando python)
4. Click **"Save"**

---

## ✨ Resultado Final

Deberías ver así en Render:

```
DATABASE_URL = postgresql://academico:gWOOqCygeQ74lVs3wyZJXinlG6Dz9H6p@dpg-d815pu7avr4c73b4aq00-a/academico_vu50
FLASK_ENV = production
SECRET_KEY = a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
```

---

## 🔍 Desglose de la DATABASE_URL (Si Quieres Entender)

```
postgresql://academico:gWOOqCygeQ74lVs3wyZJXinlG6Dz9H6p@dpg-d815pu7avr4c73b4aq00-a/academico_vu50
│           │       │       │                                  │                      │
│           │       │       │                                  │                      └─ Nombre de BD
│           │       │       │                                  └─ Hostname de Render
│           │       │       └─ Contraseña (auto-generada)
│           │       └─ Usuario de BD (academico)
│           └─ Motor de BD (PostgreSQL)
└─ Protocolo
```

**Lo importante**: 
- ✅ NO cambies nada, copia y pega TODO
- ✅ Usa Internal URL (no External)
- ✅ Las 3 variables son suficientes

---

## 🚀 Después de Configurar las Variables

1. Render redesplegará automáticamente
2. Espera a que termine el build (5-10 minutos)
3. Una vez que esté verde (✅ Live), ve a tu URL

---

## ⚠️ Errores Comunes

### ❌ Error: "Cannot connect to database"
**Solución**: 
- Verifica que `DATABASE_URL` sea la **Internal URL** de Render
- No uses la External URL (la que termina en `.render.com`)

### ❌ Error: "ConnectionRefusedError"
**Solución**:
- Asegúrate de haber guardado TODAS las variables
- Reinicia el Web Service: **Web Service → Manual Deploy**

### ❌ Las variables no se ven
**Solución**:
- Recarga la página de Render
- Limpia el caché (Ctrl+Shift+Delete)

---

## 📝 .env Local (Para Desarrollo)

En tu `.env` local, puedes tener:

```env
FLASK_ENV=development
DATABASE_URL=sqlite:///app.db
SECRET_KEY=dev-key-local
```

Pero en **Render Web Service** debes usar las 3 variables anteriores.

---

## ✅ Checklist

- [ ] Copié la Internal URL desde Render PostgreSQL
- [ ] Generé un SECRET_KEY con el comando python
- [ ] Agregué DATABASE_URL a Render
- [ ] Agregué FLASK_ENV a Render
- [ ] Agregué SECRET_KEY a Render
- [ ] El Web Service se redesplegó
- [ ] Verifi que está en estado "Live" (verde)

---

## 🎯 Próximo Paso

Una vez que las variables estén configuradas y el Web Service esté corriendo:

1. Abre la Shell de Render:
   ```bash
   cd backend
   python manage.py init_db
   python manage.py create_admin
   ```

2. Luego accede a tu URL con:
   - Email: `admin@universitario.edu`
   - Contraseña: `Admin123!`

¿Necesitas ayuda con algo más?
