"""Blueprint: Solver de Programación Lineal (Pro_Lineal integrado)"""
from flask import Blueprint, render_template, request, session, redirect, url_for
from functools import wraps
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from itertools import combinations

pro_lineal_bp = Blueprint('pro_lineal', __name__, url_prefix='/pro-lineal')


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────────────────────────────────────────
#  MÉTODO GRÁFICO
# ─────────────────────────────────────────────────────────────────────────────
def metodo_grafico(c, A, b, tipo):
    from scipy.spatial import ConvexHull

    m = len(b)

    candidatos = [0]
    for i in range(m):
        if abs(A[i, 0]) > 1e-10:
            candidatos.append(abs(b[i] / A[i, 0]))
        if abs(A[i, 1]) > 1e-10:
            candidatos.append(abs(b[i] / A[i, 1]))
    lim = max(candidatos) * 1.4 if candidatos else 20
    lim = max(lim, 5)
    x1_range = np.linspace(0, lim, 800)

    A_ext = np.vstack([A, [-1, 0], [0, -1]])
    b_ext = np.append(b, [0, 0])

    vertices = []
    iteraciones_vertices = []

    for (i, j) in combinations(range(len(b_ext)), 2):
        A2 = np.array([A_ext[i], A_ext[j]], dtype=float)
        b2 = np.array([b_ext[i], b_ext[j]], dtype=float)
        try:
            if abs(np.linalg.det(A2)) < 1e-10:
                iteraciones_vertices.append({
                    "restricciones": [i+1, j+1],
                    "punto": None,
                    "razon": "Determinante cercano a cero (rectas paralelas)"
                })
                continue
            punto = np.linalg.solve(A2, b2)
            if punto[0] < -1e-8 or punto[1] < -1e-8:
                iteraciones_vertices.append({
                    "restricciones": [i+1, j+1],
                    "punto": [round(float(punto[0]), 4), round(float(punto[1]), 4)],
                    "razon": "Punto con coordenada negativa (no factible)"
                })
                continue
            if np.all(A_ext @ punto <= b_ext + 1e-8):
                vertices.append(tuple(np.round(punto, 8)))
                iteraciones_vertices.append({
                    "restricciones": [i+1, j+1],
                    "punto": [round(float(punto[0]), 4), round(float(punto[1]), 4)],
                    "razon": "Vértice factible encontrado"
                })
            else:
                iteraciones_vertices.append({
                    "restricciones": [i+1, j+1],
                    "punto": [round(float(punto[0]), 4), round(float(punto[1]), 4)],
                    "razon": "Punto no satisface todas las restricciones"
                })
        except np.linalg.LinAlgError:
            iteraciones_vertices.append({
                "restricciones": [i+1, j+1],
                "punto": None,
                "razon": "Error en resolución del sistema"
            })
            continue

    vertices = list(set(vertices))
    vertices = [np.array(v) for v in vertices]

    punto_optimo = None
    valor_optimo = None
    info_vertices = []
    iteraciones_evaluacion = []

    for idx, v in enumerate(vertices):
        z = float(c @ v)
        info_vertices.append((v, z))

        es_mejor = False
        if valor_optimo is None:
            valor_optimo = z
            punto_optimo = v
            es_mejor = True
        else:
            if (tipo == 'max' and z > valor_optimo) or \
               (tipo == 'min' and z < valor_optimo):
                valor_optimo = z
                punto_optimo = v
                es_mejor = True

        iteraciones_evaluacion.append({
            "iteracion": idx + 1,
            "punto": [round(float(v[0]), 4), round(float(v[1]), 4)],
            "z": round(z, 4),
            "es_mejor": es_mejor,
            "mejor_z_hasta_ahora": round(float(valor_optimo), 4) if valor_optimo else None
        })

    poligono = None
    if len(vertices) >= 3:
        pts = np.array(vertices)
        try:
            hull = ConvexHull(pts)
            poligono = pts[hull.vertices]
        except Exception:
            poligono = pts

    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(10, 8))
    fig.patch.set_facecolor('#0f1117')
    ax.set_facecolor('#1a1d27')

    colores = ['#4f8ef7', '#f7654f', '#4fcf8e', '#c084fc', '#fb923c', '#38bdf8']

    for i in range(m):
        color = colores[i % len(colores)]
        if abs(A[i, 1]) > 1e-10:
            x2_vals = (b[i] - A[i, 0] * x1_range) / A[i, 1]
            mask = (x2_vals >= -lim * 0.1) & (x2_vals <= lim * 1.2)
            ax.plot(x1_range[mask], x2_vals[mask], color=color, linewidth=2.2,
                    label=f'R{i+1}: {A[i,0]:g}x₁ + {A[i,1]:g}x₂ ≤ {b[i]:g}',
                    zorder=3)
        else:
            xv = b[i] / A[i, 0] if abs(A[i, 0]) > 1e-10 else 0
            ax.axvline(x=xv, color=color, linewidth=2.2,
                       label=f'R{i+1}: x₁ ≤ {xv:g}', zorder=3)

    if poligono is not None and len(poligono) >= 3:
        from matplotlib.patches import Polygon as MplPolygon
        poly = MplPolygon(poligono, closed=True,
                          facecolor='#4f8ef718', edgecolor='#4f8ef755',
                          linewidth=1, zorder=2)
        ax.add_patch(poly)

    for v, z in info_vertices:
        es_optimo = punto_optimo is not None and np.allclose(v, punto_optimo)
        ax.plot(v[0], v[1], 'o',
                color='#f7c84f' if es_optimo else 'white',
                markersize=9 if es_optimo else 6,
                zorder=5, markeredgecolor='#0f1117', markeredgewidth=1)
        ax.annotate(f'({v[0]:.2f}, {v[1]:.2f})\nZ={z:.2f}',
                    xy=(v[0], v[1]), xytext=(10, 8),
                    textcoords='offset points', fontsize=8.5, color='#e8eaf0',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='#222535',
                              edgecolor='#f7c84f' if es_optimo else '#2e3148',
                              alpha=0.92),
                    zorder=6)

    if punto_optimo is not None:
        ax.plot(punto_optimo[0], punto_optimo[1], '*',
                color='#f7c84f', markersize=20, zorder=7,
                markeredgecolor='#0f1117', markeredgewidth=1,
                label=f'★ Óptimo: Z={valor_optimo:.4f}')
        if abs(c[1]) > 1e-10:
            x2_fo = (valor_optimo - c[0] * x1_range) / c[1]
            mask = (x2_fo >= -lim * 0.05) & (x2_fo <= lim * 1.2)
            ax.plot(x1_range[mask], x2_fo[mask],
                    color='#f7c84f', linewidth=1.8, linestyle='--', alpha=0.65,
                    label=f'F.O. óptima: Z={valor_optimo:.2f}', zorder=4)

    ax.axhline(0, color='#3a3f5c', linewidth=1)
    ax.axvline(0, color='#3a3f5c', linewidth=1)
    ax.set_xlim(-lim * 0.04, lim)
    ax.set_ylim(-lim * 0.04, lim)
    ax.set_xlabel('x₁', fontsize=13, color='#8b90a8')
    ax.set_ylabel('x₂', fontsize=13, color='#8b90a8')
    ax.tick_params(colors='#8b90a8')
    for spine in ax.spines.values():
        spine.set_edgecolor('#2e3148')
    ax.grid(True, color='#2e3148', linewidth=0.7, linestyle='--', alpha=0.6)
    titulo = (f"Método Gráfico — {'Maximizar' if tipo=='max' else 'Minimizar'} "
              f"Z = {c[0]:g}x₁ + {c[1]:g}x₂")
    ax.set_title(titulo, fontsize=13, color='#e8eaf0', pad=14, fontweight='bold')
    ax.legend(loc='upper right', fontsize=9,
              facecolor='#1a1d27', edgecolor='#2e3148', labelcolor='#e8eaf0')

    plt.tight_layout()
    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=130, facecolor=fig.get_facecolor())
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close()

    info_fmt = sorted([
        {"x1": round(float(v[0]), 4),
         "x2": round(float(v[1]), 4),
         "z":  round(float(z), 4),
         "optimo": punto_optimo is not None and np.allclose(v, punto_optimo)}
        for v, z in info_vertices
    ], key=lambda d: (not d["optimo"], d["x1"]))

    sol = punto_optimo if punto_optimo is not None else np.zeros(2)
    val = float(valor_optimo) if valor_optimo is not None else 0.0

    return img_base64, info_fmt, sol, val, iteraciones_vertices, iteraciones_evaluacion


# ─────────────────────────────────────────────────────────────────────────────
#  MÉTODO SIMPLEX
# ─────────────────────────────────────────────────────────────────────────────
def simplex(c, A, b, tipo):
    m, n = A.shape

    if np.any(b < -1e-8):
        return [], np.zeros(n), None, [], "⚠ Simplex estándar requiere b ≥ 0. Use Dos Fases."

    c_trabajo = -c.copy() if tipo == 'min' else c.copy()

    tabla = np.zeros((m + 1, n + m + 1))
    tabla[:m, :n] = A
    tabla[:m, n:n + m] = np.eye(m)
    tabla[:m, -1] = b
    tabla[-1, :n] = -c_trabajo

    var_basicas = list(range(n, n + m))

    def nombre_var(idx):
        return f"x{idx+1}" if idx < n else f"s{idx-n+1}"

    headers = [nombre_var(j) for j in range(n + m)] + ["RHS"]

    iteraciones = [{
        "paso": 0,
        "es_inicial": True,
        "tabla": tabla.copy().tolist(),
        "estado_anterior": None,
        "col_pivote": None,
        "fila_pivote": None,
        "var_entrante": None,
        "var_saliente": None,
        "elemento_pivote": None,
        "cocientes": None,
        "var_basicas": [nombre_var(v) for v in var_basicas],
        "operaciones": [
            "Tabla inicial: se agrega variables de holgura para convertir a forma estándar.",
            f"Función objetivo: {'Maximizar' if tipo == 'max' else 'Minimizar'} Z = {' + '.join(f'{c[i]:g}x{i+1}' for i in range(n) if c[i] != 0) or '0'}",
            f"Base inicial: {', '.join([nombre_var(v) for v in var_basicas])} = {b.tolist()}"
        ],
        "num_vars": n,
        "num_slack": m,
        "num_art": 0,
        "fase": "Simplex",
        "headers": headers,
        "valor_z": round(float(tabla[-1, -1]), 6),
        "criterio": "Todos los coeficientes de la fila Z deben ser ≥ 0 para optimalidad"
    }]
    paso = 1

    while True:
        coef_z = tabla[-1, :-1]
        negativos = coef_z[coef_z < -1e-10]

        if len(negativos) == 0:
            break

        col = int(np.argmin(tabla[-1, :-1]))

        cocientes = []
        for i in range(m):
            if tabla[i, col] > 1e-10:
                cocientes.append(tabla[i, -1] / tabla[i, col])
            else:
                cocientes.append(np.inf)

        if all(v == np.inf for v in cocientes):
            iteraciones.append({
                "paso": paso,
                "es_inicial": False,
                "fase": "Simplex",
                "tabla": tabla.copy().tolist(),
                "estado_anterior": tabla.copy().tolist(),
                "col_pivote": col,
                "fila_pivote": None,
                "var_entrante": nombre_var(col),
                "var_saliente": None,
                "elemento_pivote": None,
                "cocientes": ["∞"] * m,
                "var_basicas": [nombre_var(v) for v in var_basicas],
                "operaciones": [
                    f"Columna pivote: {nombre_var(col)} (coeficiente más negativo: {tabla[-1, col]:.4f})",
                    "Todos los cocientes son ∞ → Problema no acotado"
                ],
                "num_vars": n,
                "num_slack": m,
                "num_art": 0,
                "headers": headers,
                "valor_z": round(float(tabla[-1, -1]), 6),
                "es_no_acotado": True
            })
            valor_optimo = tabla[-1, -1] if tipo == 'max' else -tabla[-1, -1]
            return iteraciones, np.zeros(n), valor_optimo, var_basicas, "⚠ Solución no acotada"

        fila = int(np.argmin(cocientes))

        var_entrante = nombre_var(col)
        var_saliente = nombre_var(var_basicas[fila])
        elemento_pivote = tabla[fila, col]
        estado_anterior = tabla.copy().tolist()
        cocientes_display = [f"{v:.4f}" if v != np.inf else "∞" for v in cocientes]

        operaciones = [
            f"Coeficientes en fila Z: {['%.4f' % x for x in tabla[-1, :-1]]}",
            f"El más negativo está en columna {col} ({nombre_var(col)}): {tabla[-1, col]:.4f}",
            f"Cocientes: {cocientes_display}",
            f"Mínimo cociente en fila {fila+1} → {var_saliente} sale de la base",
            f"Elemento pivote: {elemento_pivote:.4f}",
            "─" * 40
        ]

        tabla[fila, :] /= elemento_pivote
        operaciones.append(f"F{fila+1}' = F{fila+1} ÷ {elemento_pivote:.4f}  → (normalizar fila pivote)")

        for i in range(m + 1):
            if i != fila:
                factor = tabla[i, col]
                if abs(factor) > 1e-12:
                    tabla[i, :] -= factor * tabla[fila, :]
                    signo = "-" if factor > 0 else "+"
                    operaciones.append(f"F{i+1}' = F{i+1} {signo} {abs(factor):.4f} · F{fila+1}'")

        var_basicas[fila] = col

        iteraciones.append({
            "paso": paso,
            "es_inicial": False,
            "fase": "Simplex",
            "tabla": tabla.copy().tolist(),
            "estado_anterior": estado_anterior,
            "col_pivote": col,
            "fila_pivote": fila,
            "var_entrante": var_entrante,
            "var_saliente": var_saliente,
            "elemento_pivote": float(elemento_pivote),
            "cocientes": cocientes_display,
            "var_basicas": [nombre_var(v) for v in var_basicas],
            "operaciones": operaciones,
            "num_vars": n,
            "num_slack": m,
            "num_art": 0,
            "headers": headers,
            "valor_z": round(float(tabla[-1, -1]), 6),
        })
        paso += 1

    solucion = np.zeros(n)
    for j in range(n):
        col_vals = tabla[:m, j]
        if np.isclose(col_vals, 0).sum() == m - 1 and np.isclose(col_vals, 1).sum() == 1:
            fila_sol = int(np.where(np.isclose(col_vals, 1))[0][0])
            solucion[j] = tabla[fila_sol, -1]

    valor_optimo = tabla[-1, -1]
    if tipo == 'min':
        valor_optimo = -valor_optimo

    iteraciones[-1]["operaciones"].append(f"★ ÓPTIMO ALCANZADO: Z = {valor_optimo:.4f}")

    return iteraciones, solucion, valor_optimo, var_basicas, None


# ─────────────────────────────────────────────────────────────────────────────
#  MÉTODO DE LAS DOS FASES
# ─────────────────────────────────────────────────────────────────────────────
def dos_fases(c, A_orig, b_orig, tipo, tipos_restriccion):
    m, n = A_orig.shape
    A = A_orig.copy().astype(float)
    b = b_orig.copy().astype(float)
    tipos_r = list(tipos_restriccion)

    for i in range(m):
        if b[i] < 0:
            A[i, :] *= -1
            b[i] *= -1
            if tipos_r[i] == '<=':
                tipos_r[i] = '>='
            elif tipos_r[i] == '>=':
                tipos_r[i] = '<='

    n_slack = sum(1 for t in tipos_r if t in ('<=', '>='))
    n_art   = sum(1 for t in tipos_r if t in ('>=', '='))

    if n_art == 0:
        A_simplex = A.copy()
        b_simplex = b.copy()
        iters, sol, z, vb, msg = simplex(c, A_simplex, b_simplex, tipo)
        if msg:
            return iters, [], sol, z, msg
        for it in iters:
            it["fase"] = "Dos Fases (directo)"
        return iters, [], sol, z, "✓ Óptimo encontrado (sin artificiales necesarias)."

    s_info = []
    a_info = []
    col_ptr = n

    for i in range(m):
        if tipos_r[i] in ('<=', '>='):
            sg = +1 if tipos_r[i] == '<=' else -1
            s_info.append((i, col_ptr, sg))
            col_ptr += 1

    for i in range(m):
        if tipos_r[i] in ('>=', '='):
            a_info.append((i, col_ptr))
            col_ptr += 1

    total_f1 = col_ptr
    art_col_idx = [ci for (_, ci) in a_info]

    def nv_f1(idx):
        if idx < n:
            return f"x{idx+1}"
        for k, (fi, ci, sg) in enumerate(s_info):
            if ci == idx:
                return f"s{k+1}"
        for k, (fi, ci) in enumerate(a_info):
            if ci == idx:
                return f"a{k+1}"
        return f"v{idx}"

    def nv_f2(idx):
        if idx < n:
            return f"x{idx+1}"
        for k, (fi, ci, sg) in enumerate(s_info):
            if ci == idx:
                return f"s{k+1}"
        return f"v{idx}"

    T1 = np.zeros((m + 1, total_f1 + 1))
    T1[:m, :n] = A
    T1[:m, -1] = b
    vb = [None] * m

    for (fi, ci, sg) in s_info:
        T1[fi, ci] = sg
        if sg == +1:
            vb[fi] = ci

    for (fi, ci) in a_info:
        T1[fi, ci] = +1
        vb[fi] = ci

    T1[-1, :] = 0
    for i in range(m):
        if vb[i] in art_col_idx:
            T1[-1, :] -= T1[i, :]

    headers_f1 = [nv_f1(j) for j in range(total_f1)] + ["RHS"]

    ops_inicial_f1 = [
        "═══ FASE 1: Encontrar solución básica factible ═══",
        f"Variables artificiales necesarias: {n_art} ({', '.join([nv_f1(ci) for ci in art_col_idx])})",
        "Función objetivo Fase 1: Minimizar W = Σ(artificiales)",
        "Se forma la fila Z restando las filas con artificiales básicas",
        f"W inicial = {abs(T1[-1, -1]):.4f}"
    ]

    fase1_iters = [{
        "paso": 0,
        "es_inicial": True,
        "fase": "Fase 1",
        "tabla": T1.copy().tolist(),
        "estado_anterior": None,
        "col_pivote": None,
        "fila_pivote": None,
        "var_entrante": None,
        "var_saliente": None,
        "elemento_pivote": None,
        "cocientes": None,
        "var_basicas": [nv_f1(v) if v is not None else "?" for v in vb],
        "operaciones": ops_inicial_f1,
        "num_vars": n,
        "num_slack": n_slack,
        "num_art": n_art,
        "headers": headers_f1,
        "valor_z": round(float(T1[-1, -1]), 6),
    }]

    def pivotear(T, vb, fase, nv_fn, paso_inicio, n_art_lbl, headers, es_min=True, excluir_cols=None):
        iters = []
        paso = paso_inicio
        nf = T.shape[0] - 1

        while True:
            coef_z = T[-1, :-1]
            coef_sel = coef_z.copy()
            if excluir_cols:
                for ec in excluir_cols:
                    if ec < len(coef_sel):
                        coef_sel[ec] = 0.0

            negativos = coef_sel[coef_sel < -1e-10]
            if len(negativos) == 0:
                break
            col = int(np.argmin(coef_sel))

            rats = [
                T[i, -1] / T[i, col] if T[i, col] > 1e-10 else np.inf
                for i in range(nf)
            ]
            if all(r == np.inf for r in rats):
                iters.append({
                    "paso": paso,
                    "es_inicial": False,
                    "fase": fase,
                    "tabla": T.copy().tolist(),
                    "estado_anterior": T.copy().tolist(),
                    "col_pivote": col,
                    "fila_pivote": None,
                    "var_entrante": nv_fn(col),
                    "var_saliente": None,
                    "elemento_pivote": None,
                    "cocientes": ["∞"] * nf,
                    "var_basicas": [nv_fn(v) if v is not None else "?" for v in vb],
                    "operaciones": ["Problema no acotado en esta fase"],
                    "num_vars": n,
                    "num_slack": n_slack,
                    "num_art": n_art_lbl,
                    "headers": headers,
                    "valor_z": round(float(T[-1, -1]), 6),
                    "es_no_acotado": True
                })
                break

            fila = int(np.argmin(rats))
            ve = nv_fn(col)
            vs = nv_fn(vb[fila]) if vb[fila] is not None else "?"
            ep = T[fila, col]
            ea = T.copy().tolist()
            rd = [f"{r:.4f}" if r != np.inf else "∞" for r in rats]
            ops = [
                f"Coeficientes en fila Z: {['%.4f' % x for x in T[-1, :-1]]}",
                f"Columna pivote: {col} ({ve}) con coeficiente {T[-1, col]:.4f}",
                f"Cocientes: {rd}",
                f"Fila pivote: {fila+1} (mínimo cociente: {rats[fila]:.4f})",
                f"{vs} sale, {ve} entra. Pivote: {ep:.4f}",
                "─" * 40
            ]

            T[fila, :] /= ep
            ops.append(f"F{fila+1}' = F{fila+1} ÷ {ep:.4f}")

            for i in range(nf + 1):
                if i != fila:
                    f = T[i, col]
                    if abs(f) > 1e-12:
                        T[i, :] -= f * T[fila, :]
                        s = "-" if f > 0 else "+"
                        ops.append(f"F{i+1}' = F{i+1} {s} {abs(f):.4f} · F{fila+1}'")

            vb[fila] = col

            iters.append({
                "paso": paso,
                "es_inicial": False,
                "fase": fase,
                "tabla": T.copy().tolist(),
                "estado_anterior": ea,
                "col_pivote": col,
                "fila_pivote": fila,
                "var_entrante": ve,
                "var_saliente": vs,
                "elemento_pivote": float(ep),
                "cocientes": rd,
                "var_basicas": [nv_fn(v) if v is not None else "?" for v in vb],
                "operaciones": ops,
                "num_vars": n,
                "num_slack": n_slack,
                "num_art": n_art_lbl,
                "headers": headers,
                "valor_z": round(float(T[-1, -1]), 6),
            })
            paso += 1

        return iters, vb, paso

    f1_iters, vb, paso_sig = pivotear(
        T1, vb, 'Fase 1', nv_f1, paso_inicio=1,
        n_art_lbl=n_art, headers=headers_f1, es_min=True,
        excluir_cols=art_col_idx
    )
    fase1_iters.extend(f1_iters)

    w_final = T1[-1, -1]
    art_en_base = [i for i in range(m) if vb[i] in art_col_idx]

    if abs(w_final) > 1e-6:
        fase1_iters[-1]["operaciones"].append(
             f"⚠ Fase 1 terminó con W* = {w_final:.6f} ≠ 0 → SIN SOLUCIÓN FACTIBLE"
        )
        return (fase1_iters, [], np.zeros(n), None,
                "⚠ Sin solución factible (W*≠0).")

    for i in art_en_base:
        if abs(T1[i, -1]) < 1e-6:
            pivoteado = False
            for j in range(total_f1):
                if j not in art_col_idx and abs(T1[i, j]) > 1e-10:
                    ep = T1[i, j]
                    T1[i, :] /= ep
                    for k in range(m + 1):
                        if k != i and abs(T1[k, j]) > 1e-12:
                            T1[k, :] -= T1[k, j] * T1[i, :]
                    vb[i] = j
                    fase1_iters.append({
                        "paso": paso_sig,
                        "es_inicial": False,
                        "fase": "Fase 1 (limpieza)",
                        "tabla": T1.copy().tolist(),
                        "estado_anterior": T1.copy().tolist(),
                        "col_pivote": j,
                        "fila_pivote": i,
                        "var_entrante": nv_f1(j),
                        "var_saliente": nv_f1(art_col_idx[art_en_base.index(i)]) if i in art_en_base else "?",
                        "elemento_pivote": float(ep),
                        "cocientes": None,
                        "var_basicas": [nv_f1(v) if v is not None else "?" for v in vb],
                        "operaciones": [
                            f"Artificial {nv_f1(vb[i])} en base con valor 0. Se pivotea fuera.",
                            f"Entra {nv_f1(j)}, sale artificial."
                        ],
                        "num_vars": n,
                        "num_slack": n_slack,
                        "num_art": n_art,
                        "headers": headers_f1,
                        "valor_z": round(float(T1[-1, -1]), 6),
                    })
                    paso_sig += 1
                    pivoteado = True
                    break

    for i in art_en_base:
        if T1[i, -1] > 1e-6:
            fase1_iters[-1]["operaciones"].append(
                f"⚠ Artificial {nv_f1(vb[i])} permanece en base con valor {T1[i, -1]:.6f} > 0"
            )
            return (fase1_iters, [], np.zeros(n), None,
                    "⚠ Sin solución factible (artificial en base con valor positivo).")

    fase1_iters[-1]["operaciones"].append(
        f"✓ Fase 1 completada: W* = {w_final:.6f} ≈ 0 → Solución factible encontrada"
    )

    keep = [j for j in range(total_f1) if j not in art_col_idx] + [total_f1]
    col_to_new = {orig: new for new, orig in enumerate(keep)}

    T2 = np.vstack([T1[:m, :][:, keep].copy(), np.zeros((1, len(keep)))])
    headers_f2 = [nv_f1(keep[j]) for j in range(len(keep) - 1)] + ["RHS"]

    vb2 = []
    for i, v in enumerate(vb):
        if v in col_to_new:
            vb2.append(col_to_new[v])
        else:
            found = -1
            for jj, orig in enumerate(keep[:-1]):
                cv = T2[:m, jj]
                if abs(cv[i] - 1) < 1e-8 and np.sum(np.abs(cv)) < 1 + 1e-8:
                    found = jj
                    break
            vb2.append(found if found >= 0 else 0)

    if tipo == 'max':
        c_fo = -c.copy()
    else:
        c_fo = c.copy()

    T2[-1, :n] = c_fo

    ops_f2_init = [
        "═══ FASE 2: Optimizar función objetivo original ═══",
        f"Se eliminan columnas de artificiales",
        f"Función objetivo: {'Maximizar' if tipo == 'max' else 'Minimizar'} Z = {' + '.join(f'{c[i]:g}x{i+1}' for i in range(n) if c[i] != 0) or '0'}",
        f"Fila Z inicial (antes de ajustar): {['%.4f' % x for x in T2[-1, :]]}"
    ]

    for i in range(m):
        col_base = vb2[i]
        if col_base is not None and 0 <= col_base < len(keep) - 1:
            coef = T2[-1, col_base]
            if abs(coef) > 1e-12:
                T2[-1, :] -= coef * T2[i, :]
                ops_f2_init.append(f"Se resta {coef:.4f} × F{i+1} de la fila Z (para eliminar {nv_f2(keep[col_base])})")

    ops_f2_init.append(f"Fila Z ajustada: {['%.4f' % x for x in T2[-1, :]]}")
    ops_f2_init.append(f"Z inicial = {T2[-1, -1]:.4f}")

    fase2_iters = [{
        "paso": 0,
        "es_inicial": True,
        "fase": "Fase 2",
        "tabla": T2.copy().tolist(),
        "estado_anterior": None,
        "col_pivote": None,
        "fila_pivote": None,
        "var_entrante": None,
        "var_saliente": None,
        "elemento_pivote": None,
        "cocientes": None,
        "var_basicas": [nv_f2(keep[v]) if 0 <= v < len(keep) - 1 else "?" for v in vb2],
        "operaciones": ops_f2_init,
        "num_vars": n,
        "num_slack": n_slack,
        "num_art": 0,
        "headers": headers_f2,
        "valor_z": round(float(T2[-1, -1]), 6),
    }]

    f2_iters, vb2, _ = pivotear(
        T2, vb2, 'Fase 2', nv_f2, paso_inicio=1,
        n_art_lbl=0, headers=headers_f2, es_min=False
    )
    fase2_iters.extend(f2_iters)

    solucion = np.zeros(n)
    for j in range(n):
        cv = T2[:m, j]
        if np.isclose(cv, 0).sum() == m - 1 and np.isclose(cv, 1).sum() == 1:
            fs = int(np.where(np.isclose(cv, 1))[0][0])
            solucion[j] = T2[fs, -1]

    valor_optimo = T2[-1, -1]
    if tipo == 'min':
        valor_optimo = -valor_optimo

    if fase2_iters:
        fase2_iters[-1]["operaciones"].append(f"★ ÓPTIMO ALCANZADO: Z = {valor_optimo:.4f}")

    return fase1_iters, fase2_iters, solucion, valor_optimo, "✓ Óptimo encontrado."


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER
# ─────────────────────────────────────────────────────────────────────────────
def _normalizar_iter(it):
    defaults = {
        "col_pivote": None, "fila_pivote": None, "var_entrante": None,
        "var_saliente": None, "elemento_pivote": None, "cocientes": None,
        "num_vars": 0, "num_slack": 0, "num_art": 0, "headers": [],
        "valor_z": 0.0, "holguras": [], "complementaria_ok": False,
        "z_igual_w": False, "es_no_acotado": False,
        "tabla": None, "var_basicas": None, "operaciones": [], "es_inicial": False,
    }
    for k, v in defaults.items():
        if k not in it:
            it[k] = v
    return it


# ─────────────────────────────────────────────────────────────────────────────
#  DUALIDAD
# ─────────────────────────────────────────────────────────────────────────────
def dualidad(c, A_orig, b_orig, tipo, tipos_restriccion):
    m, n = A_orig.shape
    A      = A_orig.copy().astype(float)
    b      = b_orig.copy().astype(float)
    c_vec  = c.copy().astype(float)
    tipos_r = list(tipos_restriccion)

    tipo_dual = 'min' if tipo == 'max' else 'max'
    if tipo == 'max':
        tipos_dual = ['>='] * n
    else:
        tipos_dual = ['<='] * n

    c_dual = b.copy()
    A_dual = A.T.copy()
    b_dual = c_vec.copy()

    iteraciones = [{
        "paso": 0,
        "es_inicial": True,
        "fase": "Formulación Dual",
        "tipo_primal": tipo,
        "tipo_dual": tipo_dual,
        "primal_fo": f"{'Max' if tipo=='max' else 'Min'} Z = {' + '.join(f'{c_vec[i]:g}x{i+1}' for i in range(n))}",
        "dual_fo": f"{'Max' if tipo_dual=='max' else 'Min'} W = {' + '.join(f'{c_dual[i]:g}y{i+1}' for i in range(m))}",
        "primal_restricciones": [
            f"{' + '.join(f'{A[i,j]:g}x{j+1}' for j in range(n))} {tipos_r[i]} {b[i]:g}"
            for i in range(m)
        ],
        "dual_restricciones": [
            f"{' + '.join(f'{A_dual[i,j]:g}y{j+1}' for j in range(m))} {tipos_dual[i]} {b_dual[i]:g}"
            for i in range(n)
        ],
        "operaciones": [
            "═══ FORMULACIÓN DEL PROBLEMA DUAL ═══",
            f"Primal: {tipo.upper()} Z = c·x",
            f"Dual: {tipo_dual.upper()} W = b·y",
            "",
            "Reglas de transformación:",
            "• Variables del primal (n) → Restricciones del dual (n)",
            "• Restricciones del primal (m) → Variables del dual (m)",
            f"• Primal MAX con <= → Dual MIN con y >= 0",
            f"• Primal MIN con >= → Dual MAX con y >= 0",
        ],
        "tabla": None, "var_basicas": None, "col_pivote": None,
        "fila_pivote": None, "var_entrante": None, "var_saliente": None,
        "elemento_pivote": None, "cocientes": None, "num_vars": n,
        "num_slack": 0, "num_art": 0, "headers": [], "valor_z": 0.0,
        "holguras": [], "complementaria_ok": False, "z_igual_w": False,
        "es_no_acotado": False,
    }]

    tiene_artificiales = any(t in ('>=', '=') for t in tipos_r)

    if tiene_artificiales:
        primal_f1, primal_f2, primal_sol, primal_z, primal_msg = dos_fases(
            c_vec, A, b, tipo, tipos_r
        )
        primal_iters = primal_f1 + primal_f2
    else:
        primal_iters, primal_sol, primal_z, _, primal_msg = simplex(c_vec, A, b, tipo)

    if primal_sol is None or primal_z is None:
        for it in primal_iters:
            it["fase"] = f"Primal - {it.get('fase', 'Primal')}"
        iteraciones.extend([_normalizar_iter(it) for it in primal_iters])
        iteraciones.append({
            "paso": len(iteraciones), "es_inicial": False, "fase": "Verificación Final",
            "operaciones": ["═══ RESULTADO ═══", "", f"El problema primal NO tiene solución óptima.", f"Motivo: {primal_msg}"],
            "tabla": None, "var_basicas": None, "holguras": [],
            "complementaria_ok": False, "z_igual_w": False, "col_pivote": None,
            "fila_pivote": None, "var_entrante": None, "var_saliente": None,
            "elemento_pivote": None, "cocientes": None, "num_vars": n,
            "num_slack": 0, "num_art": 0, "headers": [], "valor_z": 0.0,
            "es_no_acotado": False,
        })
        dual_info = {
            "tipo_primal": tipo, "tipo_dual": tipo_dual, "n_primal": n, "m_primal": m,
            "c_primal": c_vec.tolist(), "A_primal": A.tolist(), "b_primal": b.tolist(),
            "tipos_primal": tipos_r, "c_dual": c_dual.tolist(), "A_dual": A_dual.tolist(),
            "b_dual": b_dual.tolist(), "tipos_dual": tipos_dual, "primal_sol": None,
            "primal_z": None, "dual_sol": None, "dual_z": None, "holguras": [],
            "complementaria_ok": False, "z_igual_w": False, "mensaje": primal_msg,
        }
        return dual_info, None, None, None, None, primal_msg, iteraciones

    for it in primal_iters:
        it["fase"] = f"Primal - {it.get('fase', 'Primal')}"
    iteraciones.extend([_normalizar_iter(it) for it in primal_iters])

    A_dual_std = A_dual.copy()
    b_dual_std = b_dual.copy()
    tipos_dual_std = tipos_dual.copy()

    for i in range(n):
        if b_dual_std[i] < 0:
            A_dual_std[i, :] *= -1
            b_dual_std[i] *= -1
            if tipos_dual_std[i] == '<=':
                tipos_dual_std[i] = '>='
            elif tipos_dual_std[i] == '>=':
                tipos_dual_std[i] = '<='

    dual_tiene_artificiales = any(t in ('>=', '=') for t in tipos_dual_std)

    if dual_tiene_artificiales:
        dual_f1, dual_f2, dual_sol, dual_z, dual_msg = dos_fases(
            c_dual, A_dual_std, b_dual_std, tipo_dual, tipos_dual_std
        )
        dual_iters = dual_f1 + dual_f2
    else:
        dual_iters, dual_sol, dual_z, _, dual_msg = simplex(
            c_dual, A_dual_std, b_dual_std, tipo_dual
        )

    if dual_sol is None or dual_z is None:
        for it in dual_iters:
            it["fase"] = f"Dual - {it.get('fase', 'Dual')}"
        iteraciones.extend([_normalizar_iter(it) for it in dual_iters])
        iteraciones.append({
            "paso": len(iteraciones), "es_inicial": False, "fase": "Verificación Final",
            "operaciones": [
                "═══ RESULTADO ═══", "",
                f"Solución Primal: x = {[round(float(x), 4) for x in primal_sol]}",
                f"Valor Primal: Z = {primal_z:.4f}", "",
                f"El problema dual NO tiene solución óptima.", f"Motivo: {dual_msg}",
            ],
            "tabla": None, "var_basicas": None, "holguras": [],
            "complementaria_ok": False, "z_igual_w": False, "col_pivote": None,
            "fila_pivote": None, "var_entrante": None, "var_saliente": None,
            "elemento_pivote": None, "cocientes": None, "num_vars": n,
            "num_slack": 0, "num_art": 0, "headers": [],
            "valor_z": float(primal_z) if primal_z is not None else 0.0,
            "es_no_acotado": False,
        })
        dual_info = {
            "tipo_primal": tipo, "tipo_dual": tipo_dual, "n_primal": n, "m_primal": m,
            "c_primal": c_vec.tolist(), "A_primal": A.tolist(), "b_primal": b.tolist(),
            "tipos_primal": tipos_r, "c_dual": c_dual.tolist(), "A_dual": A_dual.tolist(),
            "b_dual": b_dual.tolist(), "tipos_dual": tipos_dual,
            "primal_sol": primal_sol.tolist(), "primal_z": primal_z,
            "dual_sol": None, "dual_z": None, "holguras": [],
            "complementaria_ok": False, "z_igual_w": False, "mensaje": dual_msg,
        }
        return dual_info, primal_sol, None, primal_z, None, f"Primal Z={primal_z:.4f} | Dual sin solución: {dual_msg}", iteraciones

    for it in dual_iters:
        it["fase"] = f"Dual - {it.get('fase', 'Dual')}"
    iteraciones.extend([_normalizar_iter(it) for it in dual_iters])

    holguras = []
    complementaria_ok = True

    for i in range(m):
        actividad = float(A[i] @ primal_sol)
        if tipos_r[i] == '>=':
            holgura_p = actividad - float(b[i])
        else:
            holgura_p = float(b[i]) - actividad
        y_i = float(dual_sol[i]) if i < len(dual_sol) else 0.0
        prod = holgura_p * y_i
        ok = abs(prod) < 1e-6
        if not ok:
            complementaria_ok = False
        holguras.append({
            "restriccion": i + 1, "actividad": round(actividad, 4),
            "rhs": round(float(b[i]), 4), "holgura_p": round(holgura_p, 4),
            "holgura": round(holgura_p, 4), "y_dual": round(y_i, 4),
            "complementaria": round(prod, 6), "valor": round(prod, 6),
            "producto": round(prod, 6), "ok": ok,
        })

    z_igual_w = abs(primal_z - dual_z) < 1e-4

    iteraciones.append({
        "paso": len(iteraciones), "es_inicial": False, "fase": "Verificación Final",
        "operaciones": [
            "═══ VERIFICACIÓN DE HOLGURA COMPLEMENTARIA ═══", "",
            f"Solución Primal: x = {[round(float(x), 4) for x in primal_sol]}",
            f"Valor Primal: Z = {primal_z:.4f}", "",
            f"Solución Dual: y = {[round(float(y), 4) for y in dual_sol]}",
            f"Valor Dual: W = {dual_z:.4f}", "",
            f"¿Z = W? {'SÍ ✓' if z_igual_w else 'NO ✗'}",
            f"¿Holgura complementaria satisfecha? {'SÍ ✓' if complementaria_ok else 'NO ✗'}",
            "", "Holguras complementarias:",
        ] + [
            f"  R{i+1}: actividad={h['actividad']:.4f}, holgura={h['holgura_p']:.4f}, "
            f"y={h['y_dual']:.4f}, producto={h['complementaria']:.6f} {'✓' if h['ok'] else '✗'}"
            for i, h in enumerate(holguras)
        ],
        "tabla": None, "var_basicas": None, "holguras": holguras,
        "complementaria_ok": complementaria_ok, "z_igual_w": z_igual_w,
        "col_pivote": None, "fila_pivote": None, "var_entrante": None,
        "var_saliente": None, "elemento_pivote": None, "cocientes": None,
        "num_vars": n, "num_slack": 0, "num_art": 0, "headers": [],
        "valor_z": float(primal_z) if primal_z is not None else 0.0,
        "es_no_acotado": False,
    })

    dual_info = {
        "tipo_primal": tipo, "tipo_dual": tipo_dual, "n_primal": n, "m_primal": m,
        "c_primal": c_vec.tolist(), "A_primal": A.tolist(), "b_primal": b.tolist(),
        "tipos_primal": tipos_r, "c_dual": c_dual.tolist(), "A_dual": A_dual.tolist(),
        "b_dual": b_dual.tolist(), "tipos_dual": tipos_dual,
        "primal_sol": primal_sol.tolist(), "primal_z": primal_z,
        "dual_sol": dual_sol.tolist(), "dual_z": dual_z,
        "holguras": holguras, "complementaria_ok": complementaria_ok,
        "z_igual_w": z_igual_w, "mensaje": "✓ Óptimo encontrado.",
    }

    msg = "✓ Óptimo encontrado."
    if not z_igual_w:
        msg = "⚠ Z ≠ W (posible error numérico)"
    if not complementaria_ok:
        msg += " Holgura complementaria no satisfecha."

    return dual_info, primal_sol, dual_sol, primal_z, dual_z, msg, iteraciones


# ─────────────────────────────────────────────────────────────────────────────
#  RUTA
# ─────────────────────────────────────────────────────────────────────────────
@pro_lineal_bp.route('/solver', methods=['GET', 'POST'])
@login_required
def solver():
    resultado = None
    pasos = []
    solucion = None
    grafica = None
    valor_optimo = None
    num_vars = 0
    vertices_grafico = None
    dual_info = None
    iteraciones_vertices = None
    iteraciones_evaluacion = None

    if request.method == 'POST':
        objetivo = request.form.get('objetivo', '').strip()
        restricciones_raw = request.form.get('restricciones', '').strip()
        metodo = request.form.get('metodo', 'simplex')
        tipo = request.form.get('tipo', 'max')

        try:
            c = np.array(list(map(float, objetivo.split())))
        except ValueError:
            resultado = "!Error: la función objetivo contiene valores no válidos."
            return render_template('pro_lineal/solver.html', resultado=resultado,
                                   vertices_grafico=None, pasos=[], solucion=None,
                                   grafica=None, valor_optimo=None, num_vars=0,
                                   dual_info=None, iteraciones_vertices=None,
                                   iteraciones_evaluacion=None)

        num_vars = len(c)
        A_list, b_list, tipos_lista = [], [], []
        error_r = False

        for linea in restricciones_raw.split('\n'):
            linea = linea.strip()
            if not linea:
                continue
            try:
                if '<=' in linea:
                    partes = linea.split('<=')
                    A_list.append(list(map(float, partes[0].split())))
                    b_list.append(float(partes[1].strip()))
                    tipos_lista.append('<=')
                elif '>=' in linea:
                    partes = linea.split('>=')
                    A_list.append(list(map(float, partes[0].split())))
                    b_list.append(float(partes[1].strip()))
                    tipos_lista.append('>=')
                elif '=' in linea:
                    partes = linea.split('=')
                    A_list.append(list(map(float, partes[0].split())))
                    b_list.append(float(partes[1].strip()))
                    tipos_lista.append('=')
                else:
                    resultado = f"!Error: restricción sin operador: '{linea}'"
                    error_r = True
                    break
            except (ValueError, IndexError):
                resultado = f"!Error al parsear: '{linea}'"
                error_r = True
                break

        if error_r:
            return render_template('pro_lineal/solver.html', resultado=resultado,
                                   vertices_grafico=None, pasos=[], solucion=None,
                                   grafica=None, valor_optimo=None, num_vars=0,
                                   dual_info=None, iteraciones_vertices=None,
                                   iteraciones_evaluacion=None)

        A = np.array(A_list)
        b = np.array(b_list)

        if A.shape[1] != num_vars:
            resultado = f"!Error: las restricciones deben tener {num_vars} coeficientes."
            return render_template('pro_lineal/solver.html', resultado=resultado,
                                   vertices_grafico=None, pasos=[], solucion=None,
                                   grafica=None, valor_optimo=None, num_vars=0,
                                   dual_info=None, iteraciones_vertices=None,
                                   iteraciones_evaluacion=None)

        if metodo == 'simplex':
            tiene_geq_o_eq = any(t in ('>=', '=') for t in tipos_lista)
            if tiene_geq_o_eq or np.any(b < -1e-8):
                resultado = "ℹ️ Simplex estándar requiere restricciones ≤. Usando Dos Fases automáticamente."
                fase1_iters, fase2_iters, sol, z, msg = dos_fases(c, A, b, tipo, tipos_lista)
                if fase2_iters:
                    fase2_iters[0]["es_inicio_fase2"] = True
                pasos = fase1_iters + fase2_iters
                solucion = sol
                valor_optimo = z
                etiqueta = "Z_max" if tipo == "max" else "Z_min"
                resultado = f"{msg} — {etiqueta} = {z:.4f}" if z is not None else msg
            else:
                iteraciones, sol, z, _, msg = simplex(c, A, b, tipo)
                pasos = iteraciones
                solucion = sol
                valor_optimo = z
                etiqueta = "Z_max" if tipo == "max" else "Z_min"
                resultado = msg if msg else f"Óptimo alcanzado. {etiqueta} = {z:.4f}"

        elif metodo == 'dos_fases':
            fase1_iters, fase2_iters, sol, z, msg = dos_fases(c, A, b, tipo, tipos_lista)
            if fase2_iters:
                fase2_iters[0]["es_inicio_fase2"] = True
            pasos = fase1_iters + fase2_iters
            solucion = sol
            valor_optimo = z
            etiqueta = "Z_max" if tipo == "max" else "Z_min"
            resultado = f"{msg} — {etiqueta} = {z:.4f}" if z is not None else msg

        elif metodo == 'dualidad':
            dual_info, ps, ds, pz, dz, msg, iters = dualidad(c, A, b, tipo, tipos_lista)
            pasos = iters
            solucion = ps
            valor_optimo = pz
            etiqueta = "Z_max" if tipo == "max" else "Z_min"
            if ps is not None and pz is not None:
                resultado = (f"{msg} — Primal {etiqueta}={pz:.4f} | "
                             f"Dual W={dz:.4f}") if ds is not None and dz is not None else f"{msg} — Primal {etiqueta}={pz:.4f}"
            else:
                resultado = msg

        elif metodo == 'grafico':
            if num_vars != 2:
                resultado = "!El método gráfico solo funciona para problemas con 2 variables."
            else:
                grafica, vertices_grafico, solucion, valor_optimo, \
                    iteraciones_vertices, iteraciones_evaluacion = \
                    metodo_grafico(c, A, b, tipo)
                etiqueta = "Z_max" if tipo == "max" else "Z_min"
                resultado = (f"Óptimo: x₁={float(solucion[0]):.4f}, "
                             f"x₂={float(solucion[1]):.4f} "
                             f"→ {etiqueta} = {valor_optimo:.4f}")

    return render_template(
        'pro_lineal/solver.html',
        resultado=resultado,
        pasos=pasos,
        solucion=solucion,
        grafica=grafica,
        valor_optimo=valor_optimo,
        num_vars=num_vars,
        vertices_grafico=vertices_grafico,
        dual_info=dual_info,
        iteraciones_vertices=iteraciones_vertices,
        iteraciones_evaluacion=iteraciones_evaluacion,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  RECURSOS ACADÉMICOS
# ─────────────────────────────────────────────────────────────────────────────
RECURSOS_ACADEMICOS = [
    {
        'id': 'solver-pl',
        'nombre': 'Calculadora de Programación Lineal',
        'descripcion': 'Optimiza funciones lineales con Simplex, Dos Fases, Método Gráfico y Dualidad. Incluye guía de uso y ejemplos.',
        'categoria': 'Optimización',
        'icono': 'fa-calculator',
        'banner': 'purple',
        'url_name': 'pro_lineal.solver',
    },
    {
        'id': 'cpm-ruta-critica',
        'nombre': 'Solucionador CPM — Ruta Crítica',
        'descripcion': 'Calcula ES, EF, LS, LF y holguras para proyectos con redes de actividades. Incluye grafo, tabla de holguras, ruta crítica y diagrama de Gantt en 3 ejercicios paso a paso.',
        'categoria': 'Gestión de Proyectos',
        'icono': 'fa-project-diagram',
        'banner': 'teal',
        'url_name': 'pro_lineal.cpm',
    },
]


@pro_lineal_bp.route('/recursos')
@login_required
def recursos():
    curso_id = request.args.get('curso_id', type=int)
    buscar = request.args.get('buscar', '').strip().lower()
    categoria = request.args.get('categoria', '').strip()

    categorias = sorted({r['categoria'] for r in RECURSOS_ACADEMICOS})

    recursos_filtrados = RECURSOS_ACADEMICOS
    if buscar:
        recursos_filtrados = [r for r in recursos_filtrados if buscar in r['nombre'].lower() or buscar in r['descripcion'].lower()]
    if categoria:
        recursos_filtrados = [r for r in recursos_filtrados if r['categoria'] == categoria]

    return render_template(
        'pro_lineal/recursos.html',
        recursos=recursos_filtrados,
        categorias=categorias,
        buscar=buscar,
        categoria_sel=categoria,
        curso_id=curso_id,
    )


@pro_lineal_bp.route('/cpm')
@login_required
def cpm():
    curso_id = request.args.get('curso_id', type=int)
    return render_template('pro_lineal/cpm.html', curso_id=curso_id)

