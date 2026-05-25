import os
from math import floor

_client = None


def _get_client():
    global _client
    if _client is None:
        from groq import Groq
        api_key = os.environ.get('GROQ_API_KEY')
        if not api_key:
            raise ValueError("GROQ_API_KEY no configurada")
        _client = Groq(api_key=api_key)
    return _client


SYSTEM_PROMPT_ESTUDIANTE = """Eres un asistente académico virtual empático llamado "Asistente Académico" en un sistema escolar colombiano.

Reglas estrictas:
- Respuestas CORTAS: máximo 4 oraciones o 4 puntos breves. Sin relleno ni introducciones largas.
- SIEMPRE en español, usa el nombre del estudiante
- Cuando pregunten por promedios, notas o faltas: usa EXACTAMENTE los valores del contexto académico, no los calcules ni inventes
- El promedio final de cada materia está en "RESUMEN DE PROMEDIOS FINALES" — úsalo directamente
- Si muestra angustia o desmotivación, valida en una oración y da UN consejo concreto
- Escala de notas: 0.0 a 5.0, mínimo aprobatorio 3.2

APOYO ACADÉMICO — puedes hacer esto:
- Explicar conceptos académicos de cualquier materia de forma clara y sencilla
- Dar ejemplos, ejercicios resueltos paso a paso, o analogías para entender mejor un tema
- Sugerir estrategias de estudio personalizadas según la materia
- Recomendar recursos usando ÚNICAMENTE los siguientes links confiables (no inventes URLs):
  • Matemáticas y ciencias: https://es.khanacademy.org
  • Videos educativos: https://www.youtube.com (dile que busque el tema)
  • Calculadora y problemas matemáticos: https://www.wolframalpha.com
  • Cursos en línea gratuitos: https://www.coursera.org o https://www.edx.org
  • Gráficas y geometría: https://www.desmos.com
  • Enciclopedia confiable: https://es.wikipedia.org
  • Idiomas: https://www.duolingo.com
- NUNCA generes ni inventes una URL que no esté en la lista anterior
- No hagas tareas ni trabajos completos por el estudiante, pero sí puedes guiarlo paso a paso

BIENESTAR EMOCIONAL:
- Si el estudiante expresa tristeza, estrés o agotamiento leve, valida con empatía en una oración y ofrece apoyo concreto
- Nunca minimices el malestar emocional; siempre valida antes de dar consejos
- Si detectas señales de crisis (llanto intenso, desmotivación extrema), recuérdale que puede hablar con su docente o buscar apoyo"""

SYSTEM_PROMPT_DOCENTE = """Eres un asistente virtual de apoyo llamado "Asistente" integrado en un sistema de gestión escolar.

Tu misión:
- Responder preguntas sobre el sistema
- Dar sugerencias pedagógicas cuando se te pidan
- Ser un punto de apoyo para los docentes

Normas:
- SIEMPRE responde en español
- Sé profesional y conciso
- Máximo 2-3 párrafos por respuesta"""

SYSTEM_PROMPT_DEFAULT = """Eres un asistente virtual integrado en un sistema de gestión escolar. Responde siempre en español de forma concisa y útil."""


def _construir_contexto_estudiante(usuario_id):
    """Obtiene el contexto académico completo del estudiante para el asistente."""
    try:
        from datetime import date
        from models import Usuario, EstudianteCurso, Nota, Calificacion, Actividad, Mensaje, AsignacionApoyo, ActividadApoyo

        usuario = Usuario.query.get(usuario_id)
        if not usuario:
            return ""

        ctx = f"ESTUDIANTE: {usuario.nombre} {usuario.apellido}\n"

        # Mensajes sin leer
        mensajes_sin_leer = Mensaje.query.filter_by(destinatario_id=usuario_id, leido=False).count()
        if mensajes_sin_leer:
            ctx += f"Mensajes sin leer: {mensajes_sin_leer}\n"

        inscripciones = EstudianteCurso.query.filter_by(estudiante_id=usuario_id).all()
        cursos_activos = [i for i in inscripciones if i.curso and i.curso.activo]

        if not cursos_activos:
            ctx += "Sin cursos activos.\n"
            return ctx

        ctx += f"\nCURSOS ACTIVOS ({len(cursos_activos)}):\n"
        hoy = date.today()

        # ── Resumen de promedios (para que Groq lo encuentre rápido) ──
        ctx += "\nRESUMEN DE PROMEDIOS FINALES:\n"
        for insc in cursos_activos:
            curso = insc.curso
            notas_r = Nota.query.filter_by(estudiante_id=usuario_id, curso_id=curso.id).all()
            cals_r = (
                Calificacion.query
                .join(Actividad, Calificacion.actividad_id == Actividad.id)
                .filter(Calificacion.estudiante_id == usuario_id, Actividad.curso_id == curso.id)
                .all()
            )
            todos_valores = [n.valor_nota for n in notas_r] + [c.valor_nota for c in cals_r]
            if todos_valores:
                prom_final = round(sum(todos_valores) / len(todos_valores), 2)
                estado = "APROBADO" if prom_final >= 3.2 else "REPROBADO"
                ctx += f"  • {curso.nombre} ({curso.codigo}): {prom_final}/5.0 — {estado}\n"
            else:
                ctx += f"  • {curso.nombre} ({curso.codigo}): sin notas registradas\n"

        ctx += "\nDETALLE POR MATERIA:\n"

        for insc in cursos_activos:
            curso = insc.curso
            ctx += f"\n━ {curso.codigo} | {curso.nombre}\n"

            # ── Asistencia ──
            resumen = curso.resumen_asistencia_estudiante(usuario_id)
            total = resumen.get('total_clases_programadas', 0)
            ausentes = resumen.get('ausentes', 0)
            justificadas = resumen.get('justificadas', 0)
            presentes = resumen.get('presentes', 0)
            total_faltas = ausentes + justificadas

            if total > 0:
                max_faltas = floor(total * 0.30)
                pct = round((total_faltas / total) * 100, 1)
                restantes = max_faltas - total_faltas
                ctx += f"  Asistencia: {presentes}/{total} presentes | Faltas: {total_faltas} ({pct}%)"
                if ausentes and justificadas:
                    ctx += f" [{ausentes} sin justificar, {justificadas} justificadas]"
                ctx += "\n"
                if restantes <= 0:
                    ctx += f"  ⚠ LÍMITE SUPERADO: ya perdió por inasistencia ({total_faltas}/{max_faltas} faltas)\n"
                elif restantes <= 2:
                    ctx += f"  ⚠ RIESGO: solo puede faltar {restantes} vez/veces más\n"
                else:
                    ctx += f"  Puede faltar {restantes} veces más sin riesgo\n"

            # ── Notas simples ──
            notas = Nota.query.filter_by(estudiante_id=usuario_id, curso_id=curso.id)\
                              .order_by(Nota.numero_entrega).all()
            if notas:
                prom_notas = round(sum(n.valor_nota for n in notas) / len(notas), 2)
                ctx += f"  Notas ({len(notas)}): promedio {prom_notas:.2f}/5.0\n"
                for n in notas:
                    tipo = n.tipo_evaluacion or "Evaluación"
                    desc = f" — {n.descripcion}" if n.descripcion else ""
                    icono = "✓" if n.valor_nota >= 3.2 else "✗"
                    ctx += f"    {icono} {tipo}{desc}: {n.valor_nota:.1f}\n"

            # ── Calificaciones por actividad ──
            calificaciones = (
                Calificacion.query
                .join(Actividad, Calificacion.actividad_id == Actividad.id)
                .filter(Calificacion.estudiante_id == usuario_id, Actividad.curso_id == curso.id)
                .all()
            )
            if calificaciones:
                prom_cal = round(sum(c.valor_nota for c in calificaciones) / len(calificaciones), 2)
                ctx += f"  Calificaciones en actividades ({len(calificaciones)}): promedio {prom_cal:.2f}/5.0\n"
                for cal in calificaciones:
                    act = cal.actividad
                    icono = "✓" if cal.valor_nota >= 3.2 else "✗"
                    retro = f" | Retro: {cal.retroalimentacion}" if cal.retroalimentacion else ""
                    ctx += f"    {icono} {act.nombre} ({act.tipo_evaluacion}): {cal.valor_nota:.1f}{retro}\n"

            # ── Actividades pendientes ──
            actividades_curso = Actividad.query.filter_by(curso_id=curso.id, activa=True)\
                                               .order_by(Actividad.fecha_vencimiento).all()
            pendientes = []
            for act in actividades_curso:
                ya_calificado = any(c.actividad_id == act.id for c in calificaciones)
                if not ya_calificado:
                    dias = (act.fecha_vencimiento - hoy).days
                    pendientes.append((act, dias))

            if pendientes:
                ctx += f"  Actividades pendientes ({len(pendientes)}):\n"
                for act, dias in pendientes[:5]:
                    if dias < 0:
                        tiempo = f"VENCIDA hace {abs(dias)} días"
                    elif dias == 0:
                        tiempo = "vence HOY"
                    else:
                        tiempo = f"vence en {dias} días ({act.fecha_vencimiento})"
                    ctx += f"    • {act.nombre} ({act.tipo_evaluacion}): {tiempo}\n"

        # ── Actividades de apoyo académico pendientes ──
        apoyo_pendientes = (
            AsignacionApoyo.query
            .join(ActividadApoyo)
            .filter(
                AsignacionApoyo.estudiante_id == usuario_id,
                AsignacionApoyo.completada == False,
                ActividadApoyo.activa == True,
            )
            .all()
        )
        if apoyo_pendientes:
            ctx += f"\nACTIVIDADES DE APOYO ACADÉMICO PENDIENTES ({len(apoyo_pendientes)}):\n"
            for asig in apoyo_pendientes:
                act = asig.actividad_apoyo
                vence = f" — vence {act.fecha_vencimiento}" if act.fecha_vencimiento else ""
                ctx += f"  • [{act.curso.codigo}] {act.titulo}{vence}\n"
                if act.descripcion:
                    ctx += f"    {act.descripcion}\n"

        return ctx
    except Exception:
        return ""


def responder_con_ia(usuario_id, role, mensaje, historial):
    """
    Llama a Groq (Llama) con contexto académico e historial de conversación.

    historial: list of {'role': 'user'|'assistant', 'content': str}
    Retorna: str con la respuesta.
    """
    try:
        client = _get_client()
    except ValueError:
        return (
            "El asistente con IA no está disponible en este momento. "
            "Escribe **ayuda** para ver las consultas académicas disponibles."
        )

    if role == 'estudiante':
        system = SYSTEM_PROMPT_ESTUDIANTE
        contexto = _construir_contexto_estudiante(usuario_id)
        if contexto:
            system += f"\n\nCONTEXTO ACTUAL DEL ESTUDIANTE:\n{contexto}"
    elif role == 'docente':
        system = SYSTEM_PROMPT_DOCENTE
    else:
        system = SYSTEM_PROMPT_DEFAULT

    messages = [{'role': 'system', 'content': system}]
    messages += (historial or [])[-10:]
    messages.append({'role': 'user', 'content': mensaje})

    try:
        response = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=messages,
            max_tokens=450,
            temperature=0.7,
        )
        return response.choices[0].message.content
    except Exception:
        return (
            "Lo siento, tuve un problema al procesar tu mensaje. "
            "Intenta de nuevo o escribe **ayuda** para ver las opciones disponibles."
        )
