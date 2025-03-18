from flask import Flask, render_template, request, redirect, url_for
import os
import pandas as pd

app = Flask(__name__)

# Directorio donde se encuentran los Excel
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Materiales")

# Variable global para almacenar los resultados finales
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

# Página de inicio
@app.route("/")
def index():
    return render_template("index.html")

# --- Paso 1: Preguntar si se requiere Ajuste de Medida ---
@app.route("/flujo_a", methods=["GET"])
def flujo_a():
    return render_template("flujo_a_inicial.html")

# --- Paso 2: Procesar respuesta inicial ---
@app.route("/flujo_a/decidir", methods=["POST"])
def flujo_a_decidir():
    ajuste = request.form.get("ajuste")
    if ajuste == "NO":
        # Aquí se redirige a otro flujo (por ejemplo, flujo B)
        return "Flujo A: Se respondió NO. (Aquí se redirigiría a flujo B)"
    elif ajuste == "SI":
        # Si se responde SI, se pasa a la selección de DIÁMETRO
        return redirect(url_for("flujo_a_seleccion"))
    else:
        return "Por favor selecciona una opción.", 400

# --- Paso 3: Selección de DIÁMETRO(s) ---
@app.route("/flujo_a/seleccion", methods=["GET", "POST"])
def flujo_a_seleccion():
    try:
        file_path = os.path.join(BASE_DIR, "ajuste de medida(2).xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        df["DIÁMETRO"] = df["DIÁMETRO"].astype(str).str.strip()
        # Excluir "TODOS" si aparece
        unique_diametros = sorted([x for x in df["DIÁMETRO"].dropna().unique() if x.upper() != "TODOS"])
    except Exception as e:
        return f"Error al cargar el Excel: {e}"

    if request.method == "POST":
        selected_diametros = request.form.getlist("diametros")
        # Pasar la selección en la URL (se separan por coma)
        diametros_str = ",".join(selected_diametros)
        return redirect(url_for("flujo_a_filtros", diametros=diametros_str))
    else:
        return render_template("flujo_a_seleccion.html", unique_diametros=unique_diametros)

# --- Paso 4: Mostrar filtros para cada DIÁMETRO seleccionado ---
@app.route("/flujo_a/filtros", methods=["GET", "POST"])
def flujo_a_filtros():
    # Recuperar los diámetros seleccionados (pasados como parámetro)
    diametros_str = request.args.get("diametros", "")
    selected_diametros = diametros_str.split(",") if diametros_str else []
    try:
        file_path = os.path.join(BASE_DIR, "ajuste de medida(2).xlsx")
        df = pd.read_excel(file_path)
        df.columns = df.columns.str.strip()
        df["DIÁMETRO"] = df["DIÁMETRO"].astype(str).str.strip()
    except Exception as e:
        return f"Error al cargar Excel: {e}"
    
    # Para cada DIÁMETRO, obtener las opciones de filtros
    filtros = {}
    for diam in selected_diametros:
        subset = df[df["DIÁMETRO"] == diam]
        # Opciones para TIPO (excluyendo "TODOS")
        tipos = sorted([x for x in subset["TIPO"].dropna().unique() if x.upper() != "TODOS"])
        if not tipos:
            tipos = ["TODOS"]
        # Opciones para GRADO DE ACERO, GRADO DE ACERO CUPLA, TIPO DE CUPLA
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
        # Recoger filtros de cada DIÁMETRO
        all_filters = {}
        for diam in selected_diametros:
            # Para TIPO, se espera selección múltiple
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
        # Aplicar los filtros a todo el DataFrame
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
        # Para efectos de este ejemplo, redirigimos a flujo H (o se puede mostrar el resultado)
        return redirect(url_for("flujo_h"))
    else:
        # Mostrar el formulario de filtros
        return render_template("flujo_a_filtros.html", selected_diametros=selected_diametros, filtros=filtros)

# --- Paso 5: Continuación (Flujo H: Material de agregación) ---
@app.route("/flujo_h")
def flujo_h():
    resultado = "<h1>Continuación: Flujo H</h1>"
    for flow, df in materiales_finales:
        resultado += f"<h2>{flow}</h2>"
        resultado += df.to_html(classes="table table-bordered", index=False)
    return resultado

if __name__ == "__main__":
    app.run(debug=True)

