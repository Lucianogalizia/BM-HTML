from flask import Flask, render_template, request, redirect, url_for
import os
import pandas as pd

app = Flask(__name__)

# Directorio donde se encuentran los archivos Excel
BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "materiales")

# Variable global para almacenar los resultados finales (en este ejemplo, solo el flujo A)
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

# FLUJO A: Ajuste de medida
@app.route("/flujo_a", methods=["GET", "POST"])
def flujo_a():
    if request.method == "POST":
        # Se recibe la opción SI o NO
        ajuste = request.form.get("ajuste")
        if ajuste == "NO":
            # En este ejemplo, si se responde NO se muestra un mensaje y se detiene
            return "Flujo A: No se seleccionó ajuste. (Aquí se redirigiría a otro flujo en la app completa)"
        elif ajuste == "SI":
            # Se reciben los valores seleccionados para DIÁMETRO
            selected_diametros = request.form.getlist("diametros")
            try:
                file_path = os.path.join(BASE_DIR, "ajuste de medida.xlsx")
                df = pd.read_excel(file_path)
                df.columns = df.columns.str.strip()
                df["DIÁMETRO"] = df["DIÁMETRO"].astype(str).str.strip()
            except Exception as e:
                return f"Error al cargar el Excel: {e}"
            # Filtra según los diámetros seleccionados (si hay alguno)
            if selected_diametros:
                df = df[df["DIÁMETRO"].isin(selected_diametros)]
            df = renombrar_columnas(df)
            materiales_finales.append(("FLUJO A", df))
            # Muestra el resultado en una página (aquí se podría redirigir a la siguiente sección)
            return f"<h1>Flujo A completado</h1>{df.to_html(classes='table table-bordered', index=False)}"
    else:
        # Método GET: carga los valores únicos de DIÁMETRO para mostrarlos en el formulario
        try:
            file_path = os.path.join(BASE_DIR, "ajuste de medida.xlsx")
            df = pd.read_excel(file_path)
            df.columns = df.columns.str.strip()
            unique_diametros = sorted(df["DIÁMETRO"].dropna().unique().tolist())
        except Exception as e:
            unique_diametros = []
        return render_template("flujo_a.html", unique_diametros=unique_diametros)

if __name__ == "__main__":
    app.run(debug=True)
