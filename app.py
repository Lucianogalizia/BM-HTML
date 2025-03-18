from flask import Flask, render_template, request, redirect, url_for
import os
import pandas as pd
import json

app = Flask(__name__)

# Directorio de archivos Excel
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "materiales")

# Variable global para almacenar resultados de cada flujo
materiales_finales = []

# Función auxiliar para renombrar columnas
def renombrar_columnas(df):
    df_renombrado = df.rename(
        columns={
            "1. Cód.SAP": "Cód.SAP",
            "2. MATERIAL": "MATERIAL",
            "3. Descripción": "Descripción",
            "5.CONDICIÓN": "CONDICIÓN"
        }
    )
    columnas = ["Cód.SAP", "MATERIAL", "Descripción", "4.CANTIDAD", "CONDICIÓN"]
    columnas_presentes = [col for col in columnas if col in df_renombrado.columns]
    return df_renombrado[columnas_presentes]

# ===================================
# Página de Inicio
# ===================================
@app.route("/")
def index():
    return render_template("index.html")

# ===================================
# FLUJO A: Ajuste de medida
# ===================================
@app.route("/flujo_a", methods=["GET"])
def flujo_a():
    return render_template("flujo_a_inicial.html")

@app.route("/flujo_a/decidir", methods=["POST"])
def flujo_a_decidir():
    ajuste = request.form.get("ajuste")
    if ajuste == "NO":
        return redirect(url_for("flujo_b"))
    elif ajuste == "SI":
        return redirect(url_for("flujo_a_seleccion"))
    else:
        return "Por favor seleccione una opción.", 400

@app.route("/flujo_a/seleccion", methods=["GET", "POST"])
def flujo_a_seleccion():
    try:
        file_path = os.path.join(BASE_DIR, "ajuste de medida.xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        df["DIÁMETRO"] = df["DIÁMETRO"].astype(str).str.strip()
        unique_diametros = sorted([x for x in df["DIÁMETRO"].dropna().unique() if x.upper() != "TODOS"])
    except Exception as e:
        return f"Error al cargar el Excel: {e}"
    if request.method == "POST":
        selected = request.form.getlist("diametros")
        diametros_str = ",".join(selected)
        return redirect(url_for("flujo_a_filtros", diametros=diametros_str))
    else:
        return render_template("flujo_a_seleccion.html", unique_diametros=unique_diametros)

@app.route("/flujo_a/filtros", methods=["GET", "POST"])
def flujo_a_filtros():
    diametros_str = request.args.get("diametros", "")
    selected_diametros = diametros_str.split(",") if diametros_str else []
    try:
        file_path = os.path.join(BASE_DIR, "ajuste de medida.xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        df["DIÁMETRO"] = df["DIÁMETRO"].astype(str).str.strip()
    except Exception as e:
        return f"Error al cargar el Excel: {e}"
    filtros = {}
    for diam in selected_diametros:
        subset = df[df["DIÁMETRO"] == diam]
        tipos = sorted([x for x in subset["TIPO"].dropna().unique() if x.upper() != "TODOS"])
        if not tipos:
            tipos = ["TODOS"]
        acero = sorted([x for x in subset["GRADO DE ACERO"].dropna().unique() if str(x).upper() != "TODOS"]) if "GRADO DE ACERO" in subset.columns else ["Seleccionar"]
        acero_cup = sorted([x for x in subset["GRADO DE ACERO CUPLA"].dropna().unique() if str(x).upper() != "TODOS"]) if "GRADO DE ACERO CUPLA" in subset.columns else ["Seleccionar"]
        tipo_cup = sorted([x for x in subset["TIPO DE CUPLA"].dropna().unique() if str(x).upper() != "TODOS"]) if "TIPO DE CUPLA" in subset.columns else ["Seleccionar"]
        filtros[diam] = {"tipos": tipos, "acero": acero, "acero_cup": acero_cup, "tipo_cup": tipo_cup}
    if request.method == "POST":
        all_filters = {}
        for diam in selected_diametros:
            tipo_sel = request.form.getlist(f"tipo_{diam}")
            if not tipo_sel:
                tipo_sel = ["TODOS"]
            else:
                tipo_sel.append("TODOS")
            ac = request.form.get(f"acero_{diam}", "Seleccionar")
            ac_cup = request.form.get(f"acero_cup_{diam}", "Seleccionar")
            t_cup = request.form.get(f"tipo_cup_{diam}", "Seleccionar")
            acero_list = ["TODOS"] if ac == "Seleccionar" else [ac, "TODOS"]
            acero_cup_list = ["TODOS"] if ac_cup == "Seleccionar" else [ac_cup, "TODOS"]
            tipo_cup_list = ["TODOS"] if t_cup == "Seleccionar" else [t_cup, "TODOS"]
            all_filters[diam] = {"tipo_list": tipo_sel, "acero_list": acero_list,
                                 "acero_cup_list": acero_cup_list, "tipo_cup_list": tipo_cup_list}
        final_condition = pd.Series([False] * len(df))
        for diam_value, fdict in all_filters.items():
            temp = pd.Series([False] * len(df))
            for tipo_val in fdict["tipo_list"]:
                cond = (df["DIÁMETRO"].isin([diam_value, "TODOS"]) &
                        df["TIPO"].isin([tipo_val, "TODOS"]) &
                        df["GRADO DE ACERO"].isin(fdict["acero_list"]) &
                        df["GRADO DE ACERO CUPLA"].isin(fdict["acero_cup_list"]) &
                        df["TIPO DE CUPLA"].isin(fdict["tipo_cup_list"]))
                temp = temp | cond
            final_condition = final_condition | temp
        final_df = df[final_condition]
        final_df_renombrado = renombrar_columnas(final_df)
        materiales_finales.append(("FLUJO A", final_df_renombrado))
        return redirect(url_for("flujo_h"))
    else:
        return render_template("flujo_a_filtros.html", selected_diametros=selected_diametros, filtros=filtros)

# ===================================
# FLUJO B: Saca Tubing
# ===================================
@app.route("/flujo_b", methods=["GET", "POST"])
def flujo_b():
    if request.method == "POST":
        saca = request.form.get("saca_tubing")
        if saca == "NO":
            return redirect(url_for("flujo_c"))
        elif saca == "SI":
            return redirect(url_for("flujo_b_seleccion"))
        else:
            return "Selecciona una opción.", 400
    return render_template("flujo_b.html")

@app.route("/flujo_b/seleccion", methods=["GET", "POST"])
def flujo_b_seleccion():
    try:
        file_path = os.path.join(BASE_DIR, "saca tubing.xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        unique_diametros = sorted([d for d in df["DIÁMETRO"].dropna().unique() if d.upper() != "TODOS"])
    except Exception as e:
        return f"Error al cargar el Excel: {e}"
    if request.method == "POST":
        selected = request.form.getlist("diametros")
        if not selected:
            return "Selecciona al menos un DIÁMETRO.", 400
        diametros_str = ",".join(selected)
        return redirect(url_for("flujo_b_cantidades", diametros=diametros_str))
    else:
        return render_template("flujo_b_seleccion.html", unique_diametros=unique_diametros)

@app.route("/flujo_b/cantidades", methods=["GET", "POST"])
def flujo_b_cantidades():
    diametros_str = request.args.get("diametros", "")
    selected = diametros_str.split(",") if diametros_str else []
    if request.method == "POST":
        quantities = {}
        for diam in selected:
            qty = request.form.get(f"qty_{diam}", type=float)
            quantities[diam] = qty
        try:
            file_path = os.path.join(BASE_DIR, "saca tubing.xlsx")
            df = pd.read_excel(file_path)
            df.columns = df.columns.str.strip()
        except Exception as e:
            return f"Error: {e}"
        df_filtered = df[(df["DIÁMETRO"].isin(selected)) | (df["DIÁMETRO"].str.upper() == "TODOS")].copy()
        for diam, qty in quantities.items():
            mask = (df_filtered["DIÁMETRO"] == diam) & (df_filtered["4.CANTIDAD"].isna())
            df_filtered.loc[mask, "4.CANTIDAD"] = qty
        df_filtered_renombrado = renombrar_columnas(df_filtered)
        materiales_finales.append(("FLUJO B", df_filtered_renombrado))
        return redirect(url_for("flujo_c"))
    else:
        return render_template("flujo_b_cantidades.html", selected_diametros=selected)

# ===================================
# FLUJO C: Tubería de Baja
# ===================================
from flask import json  # (o usa json estándar)

@app.route("/flujo_c", methods=["GET"])
def flujo_c():
    # Muestra la página inicial del Flujo C (pregunta si baja tubing)
    return render_template("flujo_c.html")

@app.route("/flujo_c/decidir", methods=["POST"])
def flujo_c_decidir():
    baja = request.form.get("baja_tubing")
    if baja == "NO":
        # Si el usuario responde NO, se continúa (por ejemplo, al Flujo D)
        return redirect(url_for("flujo_d"))
    elif baja == "SI":
        return redirect(url_for("flujo_c_seleccion"))
    else:
        return "Selecciona una opción.", 400

@app.route("/flujo_c/seleccion", methods=["GET", "POST"])
def flujo_c_seleccion():
    try:
        file_path = os.path.join(BASE_DIR, "baja tubing.xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        # Se extraen los DIÁMETRO únicos (excluyendo "TODOS")
        unique_diametros = sorted([x for x in df["DIÁMETRO"].dropna().unique() if x != "TODOS"])
    except Exception as e:
        return f"Error al cargar el Excel: {e}"
    
    if request.method == "POST":
        selected = request.form.getlist("diametros")
        if not selected:
            return "Selecciona al menos un DIÁMETRO.", 400
        diametros_str = ",".join(selected)
        return redirect(url_for("flujo_c_tipo", diametros=diametros_str))
    else:
        return render_template("flujo_c_seleccion.html", unique_diametros=unique_diametros)

@app.route("/flujo_c/tipo", methods=["GET", "POST"])
def flujo_c_tipo():
    diametros_str = request.args.get("diametros", "")
    selected_diametros = diametros_str.split(",") if diametros_str else []
    try:
        file_path = os.path.join(BASE_DIR, "baja tubing.xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
    except Exception as e:
        return f"Error: {e}"
    # Para cada DIÁMETRO, extraemos las opciones de TIPO (excluyendo "TODOS")
    filtros = {}
    for diam in selected_diametros:
        subset = df[df["DIÁMETRO"] == diam]
        tipos = sorted([x for x in subset["TIPO"].dropna().unique() if x != "TODOS"])
        if not tipos:
            tipos = ["TODOS"]
        filtros[diam] = tipos
    if request.method == "POST":
        selected_tipos_dict = {}
        for diam in selected_diametros:
            sel = request.form.getlist(f"tipo_{diam}")
            if not sel:
                sel = ["TODOS"]
            selected_tipos_dict[diam] = sel
        tipos_json = json.dumps(selected_tipos_dict)
        return redirect(url_for("flujo_c_diacsg", diametros=diametros_str, tipos=tipos_json))
    else:
        return render_template("flujo_c_tipo.html", selected_diametros=selected_diametros, filtros=filtros)

@app.route("/flujo_c/diacsg", methods=["GET", "POST"])
def flujo_c_diacsg():
    diametros_str = request.args.get("diametros", "")
    selected_diametros = diametros_str.split(",") if diametros_str else []
    tipos_json = request.args.get("tipos", "{}")
    selected_tipos_dict = json.loads(tipos_json)
    try:
        file_path = os.path.join(BASE_DIR, "baja tubing.xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
    except Exception as e:
        return f"Error: {e}"
    # Se calcula la unión de los TIPO seleccionados, agregando "TODOS"
    union_tipos = set()
    for sel in selected_tipos_dict.values():
        if sel == ["TODOS"]:
            union_tipos.add("TODOS")
        else:
            union_tipos.update(sel)
            union_tipos.add("TODOS")
    diam_filter = ["TODOS"] if selected_diametros == ["TODOS"] else selected_diametros + ["TODOS"]
    df_filtered = df[df["DIÁMETRO"].isin(diam_filter) & df["TIPO"].isin(union_tipos)]
    unique_csg = sorted([x for x in df_filtered["DIÁMETRO CSG"].dropna().unique() if x != "TODOS"])
    if not unique_csg:
        # Si no hay valores para DIÁMETRO CSG, se continúa automáticamente usando "TODOS"
        return redirect(url_for("flujo_c_cantidades", diametros=diametros_str, tipos=tipos_json, diacsg="TODOS"))
    if request.method == "POST":
        selected_csg = request.form.get("diacsg")
        if not selected_csg:
            selected_csg = "TODOS"
        # Se fuerza el filtrado: si se selecciona un valor, se usa [valor, "TODOS"]
        return redirect(url_for("flujo_c_cantidades", diametros=diametros_str, tipos=tipos_json, diacsg=selected_csg))
    else:
        return render_template("flujo_c_diacsg.html", unique_csg=unique_csg)

@app.route("/flujo_c/cantidades", methods=["GET", "POST"])
def flujo_c_cantidades():
    diametros_str = request.args.get("diametros", "")
    selected_diametros = diametros_str.split(",") if diametros_str else []
    tipos_json = request.args.get("tipos", "{}")
    selected_tipos_dict = json.loads(tipos_json)
    # Aquí se recibe el valor seleccionado en DIÁMETRO CSG; se utiliza para filtrar
    diacsg = request.args.get("diacsg", "TODOS")
    try:
        file_path = os.path.join(BASE_DIR, "baja tubing.xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
    except Exception as e:
        return f"Error: {e}"
    if request.method == "POST":
        quantities = {}
        for diam in selected_diametros:
            for tipo in selected_tipos_dict.get(diam, []):
                qty = request.form.get(f"qty_{diam}_{tipo}", type=float)
                quantities[(diam, tipo)] = qty
        # Ahora, se aplica el filtrado incluyendo DIÁMETRO, TIPO y DIÁMETRO CSG
        for (diam, tipo), qty in quantities.items():
            condition = (
                df["DIÁMETRO"].isin([diam, "TODOS"]) &
                df["TIPO"].isin([tipo, "TODOS"]) &
                df["DIÁMETRO CSG"].isin([diacsg, "TODOS"])
            )
            df.loc[condition & df["4.CANTIDAD"].isna(), "4.CANTIDAD"] = qty
        final_condition = pd.Series([False]*len(df))
        for diam_value, fdict in selected_tipos_dict.items():
            temp = pd.Series([False]*len(df))
            for tipo_val in fdict:
                cond = (
                    df["DIÁMETRO"].isin([diam_value, "TODOS"]) &
                    df["TIPO"].isin([tipo_val, "TODOS"]) &
                    df["DIÁMETRO CSG"].isin([diacsg, "TODOS"])
                )
                temp = temp | cond
            final_condition = final_condition | temp
        final_df = df[final_condition]
        final_df_renombrado = renombrar_columnas(final_df)
        materiales_finales.append(("FLUJO C", final_df_renombrado))
        return redirect(url_for("flujo_d"))
    else:
        # Prepara una lista de combinaciones para mostrar los campos de cantidad
        combos = []
        for diam in selected_diametros:
            for tipo in selected_tipos_dict.get(diam, []):
                combos.append((diam, tipo))
        return render_template("flujo_c_cantidades.html", combos=combos)

# ===================================
# FLUJO D: Profundiza
# ===================================
@app.route("/flujo_d", methods=["GET"])
def flujo_d():
    return render_template("flujo_d.html")

@app.route("/flujo_d/decidir", methods=["POST"])
def flujo_d_decidir():
    profundizar = request.form.get("profundizar")
    if profundizar == "NO":
        return redirect(url_for("flujo_e"))
    elif profundizar == "SI":
        return redirect(url_for("flujo_d_seleccion"))
    else:
        return "Selecciona una opción.", 400

@app.route("/flujo_d/seleccion", methods=["GET", "POST"])
def flujo_d_seleccion():
    file_path = os.path.join(BASE_DIR, "profundiza.xlsx")
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        for col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.strip()
        # Reemplazar valores 'nan'
        if 'TIPO' in df.columns:
            df['TIPO'] = df['TIPO'].replace('nan', '').fillna('')
        if 'DIÁMETRO CSG' in df.columns:
            df['DIÁMETRO CSG'] = df['DIÁMETRO CSG'].replace('nan', '').fillna('')
    except Exception as e:
        return f"Error al cargar el Excel: {e}"
    
    # Elegir la columna a usar: si existe "DIÁMETRO", se usa; sino, "DIÁMETRO CSG"
    if "DIÁMETRO" in df.columns:
        col = "DIÁMETRO"
    elif "DIÁMETRO CSG" in df.columns:
        col = "DIÁMETRO CSG"
    else:
        return "La columna de DIÁMETRO no se encontró en el Excel."
    
    unique_values = sorted(df[col].dropna().unique().tolist())
    if request.method == "POST":
        selected = request.form.getlist("valores")
        if not selected:
            return "No se seleccionaron valores.", 400
        selected_str = ",".join(selected)
        # Redirigir a la página de ingreso de cantidades, pasando la columna y los valores seleccionados
        return redirect(url_for("flujo_d_cantidades", valores=selected_str, col=col))
    else:
        return render_template("flujo_d_seleccion.html", unique_values=unique_values, col=col)

@app.route("/flujo_d/cantidades", methods=["GET", "POST"])
def flujo_d_cantidades():
    valores_str = request.args.get("valores", "")
    col = request.args.get("col", "")
    selected_values = valores_str.split(",") if valores_str else []
    file_path = os.path.join(BASE_DIR, "profundiza.xlsx")
    try:
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = df[c].astype(str).str.strip()
    except Exception as e:
        return f"Error al cargar el Excel: {e}"
    if request.method == "POST":
        quantities = {}
        for val in selected_values:
            qty = request.form.get(f"qty_{val}", type=float)
            quantities[val] = qty
        # Filtrar el DataFrame según la columna y los valores seleccionados
        filtered_df = df[df[col].isin(selected_values)]
        for val, qty in quantities.items():
            mask = (filtered_df[col] == val) & (filtered_df["4.CANTIDAD"].isna())
            filtered_df.loc[mask, "4.CANTIDAD"] = qty
        final_df_renombrado = renombrar_columnas(filtered_df)
        materiales_finales.append(("FLUJO D", final_df_renombrado))
        return redirect(url_for("flujo_e"))
    else:
        # Preparar lista de valores para mostrar los campos de cantidad
        combos = selected_values  # Cada valor seleccionado se usará para ingresar cantidad
        return render_template("flujo_d_cantidades.html", combos=combos, col=col)

# ===================================
# FLUJO E: Baja Varillas
# ===================================
@app.route("/flujo_e", methods=["GET"])
def flujo_e():
    return render_template("flujo_e.html")

@app.route("/flujo_e/decidir", methods=["POST"])
def flujo_e_decidir():
    baja_varilla = request.form.get("baja_varilla")
    if baja_varilla == "NO":
        return redirect(url_for("flujo_f"))
    elif baja_varilla == "SI":
        return redirect(url_for("flujo_e_seleccion"))
    else:
        return "Selecciona una opción.", 400

@app.route("/flujo_e/seleccion", methods=["GET", "POST"])
def flujo_e_seleccion():
    try:
        file_path = os.path.join(BASE_DIR, "baja varillas.xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        df["DIÁMETRO"] = df["DIÁMETRO"].astype(str).str.strip()
        unique_diametros = sorted([x for x in df["DIÁMETRO"].dropna().unique() if x.upper() != "TODOS"])
    except Exception as e:
        return f"Error al cargar el Excel: {e}"
    if request.method == "POST":
        selected = request.form.getlist("diametros")
        if not selected:
            return "Selecciona al menos un DIÁMETRO.", 400
        diametros_str = ",".join(selected)
        return redirect(url_for("flujo_e_filtros", diametros=diametros_str))
    else:
        return render_template("flujo_e_seleccion.html", unique_diametros=unique_diametros)

@app.route("/flujo_e/filtros", methods=["GET", "POST"])
def flujo_e_filtros():
    diametros_str = request.args.get("diametros", "")
    selected_diametros = diametros_str.split(",") if diametros_str else []
    try:
        file_path = os.path.join(BASE_DIR, "baja varillas.xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        df["DIÁMETRO"] = df["DIÁMETRO"].astype(str).str.strip()
    except Exception as e:
        return f"Error al cargar el Excel: {e}"
    filtros = {}
    for diam in selected_diametros:
        subset = df[df["DIÁMETRO"] == diam]
        tipos = sorted([x for x in subset["TIPO"].dropna().unique() if x.upper() != "TODOS"])
        if not tipos:
            tipos = ["TODOS"]
        acero = sorted([x for x in subset["GRADO DE ACERO"].dropna().unique() if str(x).upper() != "TODOS"]) if "GRADO DE ACERO" in subset.columns else ["Seleccionar"]
        acero_cup = sorted([x for x in subset["GRADO DE ACERO CUPLA"].dropna().unique() if str(x).upper() != "TODOS"]) if "GRADO DE ACERO CUPLA" in subset.columns else ["Seleccionar"]
        tipo_cup = sorted([x for x in subset["TIPO DE CUPLA"].dropna().unique() if str(x).upper() != "TODOS"]) if "TIPO DE CUPLA" in subset.columns else ["Seleccionar"]
        filtros[diam] = {"tipos": tipos, "acero": acero, "acero_cup": acero_cup, "tipo_cup": tipo_cup}
    if request.method == "POST":
        all_filters = {}
        for diam in selected_diametros:
            tipo_sel = request.form.getlist(f"tipo_{diam}")
            if not tipo_sel:
                tipo_sel = ["TODOS"]
            else:
                tipo_sel.append("TODOS")
            ac = request.form.get(f"acero_{diam}", "Seleccionar")
            ac_cup = request.form.get(f"acero_cup_{diam}", "Seleccionar")
            t_cup = request.form.get(f"tipo_cup_{diam}", "Seleccionar")
            acero_list = ["TODOS"] if ac == "Seleccionar" else [ac, "TODOS"]
            acero_cup_list = ["TODOS"] if ac_cup == "Seleccionar" else [ac_cup, "TODOS"]
            tipo_cup_list = ["TODOS"] if t_cup == "Seleccionar" else [t_cup, "TODOS"]
            all_filters[diam] = {"tipo_list": tipo_sel, "acero_list": acero_list,
                                 "acero_cup_list": acero_cup_list, "tipo_cup_list": tipo_cup_list}
        final_condition = pd.Series([False]*len(df))
        for diam_value, fdict in all_filters.items():
            temp = pd.Series([False]*len(df))
            for tipo_val in fdict["tipo_list"]:
                cond = (df["DIÁMETRO"].isin([diam_value, "TODOS"]) &
                        df["TIPO"].isin([tipo_val, "TODOS"]) &
                        df["GRADO DE ACERO"].isin(fdict["acero_list"]) &
                        df["GRADO DE ACERO CUPLA"].isin(fdict["acero_cup_list"]) &
                        df["TIPO DE CUPLA"].isin(fdict["tipo_cup_list"]))
                temp = temp | cond
            final_condition = final_condition | temp
        final_df = df[final_condition]
        final_df_renombrado = renombrar_columnas(final_df)
        materiales_finales.append(("FLUJO E", final_df_renombrado))
        return redirect(url_for("flujo_g"))
    else:
        return render_template("flujo_e_filtros.html", selected_diametros=selected_diametros, filtros=filtros)

# ===================================
# Dummy FLUJO F
# ===================================
@app.route("/flujo_f")
def flujo_f():
    return "<h1>Flujo F: (Pendiente de implementación)</h1>"

# ===================================
# Dummy FLUJO G
# ===================================
@app.route("/flujo_g")
def flujo_g():
    return "<h1>Flujo G: (Pendiente de implementación)</h1>"

# ===================================
# FLUJO H: Mostrar Resultados Acumulados
# ===================================
@app.route("/flujo_h")
def flujo_h():
    resultado = "<h1>Flujo H: Resultados Acumulados</h1>"
    for flow, df in materiales_finales:
        resultado += f"<h2>{flow}</h2>" + df.to_html(classes='table table-bordered', index=False)
    return resultado

if __name__ == "__main__":
    app.run(debug=True)


