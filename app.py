from flask import Flask, render_template, request, redirect, url_for
import os
import pandas as pd

app = Flask(__name__)

# Directorio donde se encuentran los archivos Excel
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "materiales")

# Variable global para almacenar los DataFrames finales de cada flujo
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

# ----------------------------------
# Página de Inicio
# ----------------------------------
@app.route("/")
def index():
    return render_template("index.html")

# ==================================
# FLUJO A: Ajuste de medida
# ==================================
# Paso 1: Preguntar si se requiere ajuste de medida
@app.route("/flujo_a", methods=["GET"])
def flujo_a():
    return render_template("flujo_a_inicial.html")

# Paso 2: Procesar la respuesta del Flujo A
@app.route("/flujo_a/decidir", methods=["POST"])
def flujo_a_decidir():
    ajuste = request.form.get("ajuste")
    if ajuste == "NO":
        # Si se responde NO en el Flujo A, se pasa al Flujo B
        return redirect(url_for("flujo_b"))
    elif ajuste == "SI":
        # Si se responde SI, se pasa a la selección de DIÁMETRO(s)
        return redirect(url_for("flujo_a_seleccion"))
    else:
        return "Por favor selecciona una opción.", 400

# Paso 3: Selección de DIÁMETRO(s) en Flujo A
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
        selected_diametros = request.form.getlist("diametros")
        diametros_str = ",".join(selected_diametros)
        return redirect(url_for("flujo_a_filtros", diametros=diametros_str))
    else:
        return render_template("flujo_a_seleccion.html", unique_diametros=unique_diametros)

# Paso 4: Configuración de filtros en Flujo A
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
        return f"Error al cargar Excel: {e}"
    
    # Para cada DIÁMETRO seleccionado, se calculan las opciones de filtro
    filtros = {}
    for diam in selected_diametros:
        subset = df[df["DIÁMETRO"] == diam]
        tipos = sorted([x for x in subset["TIPO"].dropna().unique() if x.upper() != "TODOS"])
        if not tipos:
            tipos = ["TODOS"]
        acero = sorted([x for x in subset["GRADO DE ACERO"].dropna().unique() if str(x).upper() != "TODOS"]) if "GRADO DE ACERO" in subset.columns else ["Seleccionar"]
        acero_cup = sorted([x for x in subset["GRADO DE ACERO CUPLA"].dropna().unique() if str(x).upper() != "TODOS"]) if "GRADO DE ACERO CUPLA" in subset.columns else ["Seleccionar"]
        tipo_cup = sorted([x for x in subset["TIPO DE CUPLA"].dropna().unique() if str(x).upper() != "TODOS"]) if "TIPO DE CUPLA" in subset.columns else ["Seleccionar"]
        filtros[diam] = {
            "tipos": tipos,
            "acero": acero if acero else ["Seleccionar"],
            "acero_cup": acero_cup if acero_cup else ["Seleccionar"],
            "tipo_cup": tipo_cup if tipo_cup else ["Seleccionar"]
        }
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
            all_filters[diam] = {
                "tipo_list": tipo_sel,
                "acero_list": acero_list,
                "acero_cup_list": acero_cup_list,
                "tipo_cup_list": tipo_cup_list
            }
        final_condition = pd.Series([False] * len(df))
        for diam_value, fdict in all_filters.items():
            temp_cond_diam = pd.Series([False] * len(df))
            for tipo_val in fdict["tipo_list"]:
                cond = (
                    df["DIÁMETRO"].isin([diam_value, "TODOS"]) &
                    df["TIPO"].isin([tipo_val, "TODOS"]) &
                    df["GRADO DE ACERO"].isin(fdict["acero_list"]) &
                    df["GRADO DE ACERO CUPLA"].isin(fdict["acero_cup_list"]) &
                    df["TIPO DE CUPLA"].isin(fdict["tipo_cup_list"])
                )
                temp_cond_diam = temp_cond_diam | cond
            final_condition = final_condition | temp_cond_diam
        final_df = df[final_condition]
        final_df_renombrado = renombrar_columnas(final_df)
        materiales_finales.append(("FLUJO A", final_df_renombrado))
        # Por este ejemplo, redirigimos a una ruta que muestra el resultado
        return redirect(url_for("flujo_h"))
    else:
        return render_template("flujo_a_filtros.html", selected_diametros=selected_diametros, filtros=filtros)

# ==================================
# FLUJO B: Saca Tubing
# ==================================
# Paso 1: Preguntar si se saca Tubing
@app.route("/flujo_b", methods=["GET", "POST"])
def flujo_b():
    if request.method == "POST":
        saca_tubing = request.form.get("saca_tubing")
        if saca_tubing == "NO":
            return redirect(url_for("flujo_c"))
        elif saca_tubing == "SI":
            return redirect(url_for("flujo_b_seleccion"))
        else:
            return "Por favor seleccione una opción.", 400
    return render_template("flujo_b.html")

# Paso 2: Selección de DIÁMETRO(s) para Saca Tubing
@app.route("/flujo_b/seleccion", methods=["GET", "POST"])
def flujo_b_seleccion():
    try:
        file_path = os.path.join(BASE_DIR, "saca tubing.xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        unique_diametros = sorted([d for d in df["DIÁMETRO"].dropna().unique() if d.upper() != "TODOS"])
    except Exception as e:
        return f"Error al cargar saca tubing: {e}"
    
    if request.method == "POST":
        selected_diametros = request.form.getlist("diametros")
        if not selected_diametros:
            return "Por favor, seleccione al menos un DIÁMETRO.", 400
        diametros_str = ",".join(selected_diametros)
        return redirect(url_for("flujo_b_cantidades", diametros=diametros_str))
    else:
        return render_template("flujo_b_seleccion.html", unique_diametros=unique_diametros)

# Paso 3: Ingreso de Cantidades para cada DIÁMETRO seleccionado
@app.route("/flujo_b/cantidades", methods=["GET", "POST"])
def flujo_b_cantidades():
    diametros_str = request.args.get("diametros", "")
    selected_diametros = diametros_str.split(",") if diametros_str else []
    if request.method == "POST":
        quantities = {}
        for diam in selected_diametros:
            qty = request.form.get(f"qty_{diam}", type=float)
            quantities[diam] = qty
        try:
            file_path = os.path.join(BASE_DIR, "saca tubing.xlsx")
            df = pd.read_excel(file_path)
            df.columns = df.columns.str.strip()
        except Exception as e:
            return f"Error al cargar saca tubing: {e}"
        df_filtered = df[(df["DIÁMETRO"].isin(selected_diametros)) | (df["DIÁMETRO"].str.upper() == "TODOS")].copy()
        for diam, qty in quantities.items():
            mask = (df_filtered["DIÁMETRO"] == diam) & (df_filtered["4.CANTIDAD"].isna())
            df_filtered.loc[mask, "4.CANTIDAD"] = qty
        df_filtered_renombrado = renombrar_columnas(df_filtered)
        materiales_finales.append(("FLUJO B", df_filtered_renombrado))
        return redirect(url_for("flujo_c"))
    else:
        return render_template("flujo_b_cantidades.html", selected_diametros=selected_diametros)

# ==================================
# Flujo C: (Dummy para redirección)
# ==================================
@app.route("/flujo_c")
def flujo_c():
    return "<h1>Flujo C: (Pendiente de implementación)</h1>"

# ==================================
# Flujo H: Mostrar Resultados (Continuación)
# ==================================
@app.route("/flujo_h")
def flujo_h():
    resultado = "<h1>Continuación: Flujo H</h1>"
    for flow, df in materiales_finales:
        resultado += f"<h2>{flow}</h2>"
        resultado += df.to_html(classes='table table-bordered', index=False)
    return resultado

if __name__ == "__main__":
    app.run(debug=True)


