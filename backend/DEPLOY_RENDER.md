# 🚀 Guía de Deployment en Render

## 📋 Prerequisitos
- Cuenta en [Render.com](https://render.com) (gratuita)
- Repositorio Git con el proyecto (GitHub, GitLab, etc.)
- Proyecto subido a Git

## 📊 Paso 1: Preparar el Repositorio Git

### 1.1 Inicializar Git (si no está hecho)
```bash
cd backend
git init
git add .
git commit -m "Preparar para deployment en Render"
git remote add origin https://github.com/TU_USUARIO/TU_REPO.git
git push -u origin main
```

### 1.2 Archivo .gitignore (verificar que exista)
```
__pycache__/
*.pyc
*.pyo
.env
*.db
instance/
.vscode/
```

---

## 🗄️ Paso 2: Crear Base de Datos PostgreSQL en Render

### 2.1 En el Dashboard de Render:
1. Click en **"New+"** → **"PostgreSQL"**
2. Completa:
   - **Name**: `academico-db` (nombre del servicio)
   - **Database**: `academico` (nombre de la BD)
   - **User**: `academico` (usuario de BD, auto-generado)
   - **Region**: Elige la más cercana (ej: Frankfurt, São Paulo)
   - **PostgreSQL Version**: 15 o superior
3. Click **"Create Database"**

### 2.2 Copiar la URL de conexión
Una vez creada, verás un campo **"Internal Database URL"**:
```
postgresql://academico:CONTRASEÑA_AUTO@dpg-XXXXXX.render.internal/academico
```
⚠️ **Guarda esta URL, la necesitarás después**

---

## 🌐 Paso 3: Crear Web Service en Render

### 3.1 En el Dashboard:
1. Click **"New+"** → **"Web Service"**
2. Conecta tu repositorio GitHub

### 3.2 Configurar el servicio:
- **Name**: `academico-app` (nombre de tu aplicación)
- **Runtime**: `Python 3`
- **Build Command**: 
  ```
  pip install -r backend/requirements.txt
  ```
- **Start Command**:
  ```
  cd backend && gunicorn wsgi:app
  ```
- **Instance Type**: Free (para empezar)

### 3.3 Environment Variables
Click en **"Environment"** y agrega:

```env
FLASK_ENV=production
SECRET_KEY=TU_CLAVE_SECRETA_ALEATORIA_AQUI
DATABASE_URL=postgresql://academico:CONTRASEÑA@dpg-XXXXXX.render.internal/academico
```

⚠️ **IMPORTANTE**: 
- Reemplaza `SECRET_KEY` con algo seguro (ej: resultado de `python -c "import secrets; print(secrets.token_hex(16))"`)
- Usa la DATABASE_URL que copiaste antes (Internal URL de PostgreSQL)

### 3.4 Deploy
Click **"Create Web Service"** y espera a que termine el build

---

## ✅ Paso 4: Ejecutar Migraciones en Render

Una vez que el Web Service esté corriendo:

### 4.1 Opción A: Usando Render Console (Recomendado)
1. En el Dashboard del Web Service, click en **"Shell"**
2. Ejecuta:
   ```bash
   cd backend
   python manage.py init_db
   python manage.py create_admin
   flask db upgrade
   ```

### 4.2 Opción B: Automático con Procfile (alternativa)
Ya configuramos el Procfile para ejecutar:
```
release: python manage.py migrate
```

---

## 🎯 Paso 5: Verificar Deployment

1. Ve a tu URL de Render (ej: `https://academico-app.onrender.com`)
2. Deberías ver la página de login
3. Accede con:
   - **Email**: `admin@universitario.edu`
   - **Contraseña**: `Admin123!`

---

## 🔧 Troubleshooting

### Error: "ModuleNotFoundError: No module named 'gunicorn'"
```bash
# Asegúrate que requirements.txt tiene gunicorn
pip install gunicorn==21.2.0
```

### Error: "Cannot connect to database"
- Verifica que `DATABASE_URL` sea correcto en Environment Variables
- Asegúrate de que DATABASE_URL sea la "Internal URL" de Render (no la externa)

### Error: "No module named 'flask_migrate'"
```bash
# Actualiza requirements.txt
pip install Flask-Migrate==4.1.0
```

### Error: "ModuleNotFoundError: No module named 'psycopg2'"
- Ya está en requirements.txt
- Si persiste, reinicia el Web Service

---

## 📁 Estructura de Archivos para Deploy

```
backend/
├── app.py              ✓ Punto de entrada
├── wsgi.py             ✓ Para gunicorn (NUEVO)
├── manage.py           ✓ Gestor de migraciones (NUEVO)
├── config.py           ✓ Configuración (ACTUALIZADO)
├── Procfile            ✓ Instrucciones para Render (NUEVO)
├── .env.example        ✓ Template de variables (NUEVO)
├── requirements.txt    ✓ Dependencias (ACTUALIZADO)
├── models.py           ✓
├── extensions.py       ✓
├── utils.py            ✓
├── routes/
├── templates/
├── static/
├── migrations/
└── instance/
```

---

## 🔄 Actualizar el Código en Render

Cada vez que hagas cambios:

```bash
git add .
git commit -m "Descripción del cambio"
git push origin main
```

Render detectará automáticamente los cambios y redesplegará la aplicación.

---

## 💰 Costos en Render

- **PostgreSQL**: $7/mes (o gratuito durante 90 días con crédito inicial)
- **Web Service**: Gratuito (con limitaciones) o $7/mes (sin limitaciones)

---

## 📝 Variables de Entorno Recomendadas

```env
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=your-super-secret-key-here
DATABASE_URL=postgresql://user:pass@host:5432/dbname
SQLALCHEMY_TRACK_MODIFICATIONS=False
```

---

## ✨ Checklist Final

- [ ] Código en Git (GitHub/GitLab)
- [ ] PostgreSQL creada en Render
- [ ] Web Service creada en Render
- [ ] DATABASE_URL agregada a Environment Variables
- [ ] SECRET_KEY configurada
- [ ] Migraciones ejecutadas
- [ ] Admin creado
- [ ] Prueba de login exitosa
- [ ] Datos de ejemplo cargados (opcional)

---

## 🆘 Soporte

Si tienes problemas:
1. Revisa los logs en Render: **Web Service → Logs**
2. Verifica que las variables de entorno sean correctas
3. Reinicia el Web Service: **Web Service → Manual Deploy**
