# 🚀 GUÍA RÁPIDA - Solucionar Error de Tabla Mensajes

## El Problema
```
relation "mensajes" does not exist
```

## La Solución (3 opciones)

### ✅ OPCIÓN 1: Git Push (RECOMENDADO)
```powershell
cd c:\ProCD\Comunicacion_Datos
git add .
git commit -m "Fix: crear tabla mensajes"
git push origin main
```
Render ejecutará las migraciones automáticamente. Espera 2-5 minutos y reinicia.

### ✅ OPCIÓN 2: Ejecutar Script Local
```powershell
cd c:\ProCD\Comunicacion_Datos\backend
python create_tables.py
```

### ✅ OPCIÓN 3: Ejecutar SQL Directamente en Render
1. Ve al dashboard de Render
2. Abre la consola PostgreSQL
3. Copia y ejecuta el SQL de [SOLUCION_TABLA_MENSAJES.md](SOLUCION_TABLA_MENSAJES.md)

## ¿Qué se hizo?
- ✅ Modelo `Mensaje` en `models.py`
- ✅ Migración SQL para PostgreSQL
- ✅ `app.py` actualizado para ejecutar migración automáticamente
- ✅ Todo listo para producción

## Próximos Pasos
1. Ejecuta una de las 3 opciones arriba
2. Espera a que se complete
3. Intenta enviar un mensaje nuevamente
4. ✅ ¡Debería funcionar!

---

**Ver detalles en**: [SOLUCION_TABLA_MENSAJES.md](SOLUCION_TABLA_MENSAJES.md)
