import os
import urllib.parse
from io import BytesIO

from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
import pandas as pd

app = Flask(__name__)
# Permite peticiones desde tu front en 4150, sin credenciales
CORS(app, resources={r"/*": {"origins": ["http://intranet.puntamedica.com:4150"]}})

# ---------- Rutas de archivos ----------
EXCEL_PATH   = r"C:\inetpub\intranet.puntamedica.com\App Hospital\App Pantallas\backend\DIRECTORIO.xlsx"
USERS_PATH   = "usuarios.xlsx"   # Excel con columnas 'user' y 'password'
SHEET_NAME   = "Super correccion ultima nuevo"
FOTOS_FOLDER = r"C:\inetpub\intranet.puntamedica.com\App Hospital\App Pantallas\frontend\public\Medicos"
CHECKMARK    = "✓"

os.makedirs(FOTOS_FOLDER, exist_ok=True)

# ---------- Utilidades ----------
def ensure_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    - Convierte nombres de columnas a str y les hace strip().
    - Se asegura de que existan las columnas requeridas que usa el código.
    """
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]

    REQUIRED = ["Nombre", "Apellido Paterno", "Apellido Materno", "Foto"]
    for col in REQUIRED:
        if col not in df.columns:
            df[col] = ""

    return df


def build_encoded_basename(first_name: str, paterno: str, materno: str) -> str:
    """
    Regresa el basename con:
    - todo en minúsculas
    - nombres y apellidos sin espacios
    - separador "_"
    - conserva acentos y eñes
    - elimina caracteres prohibidos en Windows
    """
    def norm_no_spaces(s: str) -> str:
        return "".join((s or "").split()).lower()

    def sanitize_component_for_windows(s: str) -> str:
        if s is None:
            return ""
        forbidden = set('\\/:*?"<>|')
        s = "".join(ch for ch in s if ch not in forbidden)
        s = s.rstrip(" .")
        return s

    first = sanitize_component_for_windows(norm_no_spaces(first_name))
    pat   = sanitize_component_for_windows(norm_no_spaces(paterno))
    mat   = sanitize_component_for_windows(norm_no_spaces(materno))

    parts = [p for p in [first, pat, mat] if p]
    return "_".join(parts)


# ---------- Rutas ----------
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    user = data.get("user", "")
    pw   = data.get("password", "")
    try:
        df = pd.read_excel(USERS_PATH, dtype=str)
        df.columns = [str(c).strip() for c in df.columns]
        ok = not df[(df.get("user", "") == user) & (df.get("password", "") == pw)].empty
    except Exception:
        ok = False
    if ok:
        return jsonify({"success": True}), 200
    else:
        return jsonify({"success": False, "message": "Credenciales inválidas"}), 401


@app.route("/data", methods=["GET"])
def get_data():
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, dtype=str)
    df = ensure_columns(df)
    return jsonify({
        "columns": list(df.columns),
        "rows":    df.fillna("").values.tolist()
    })


@app.route("/save", methods=["POST"])
def save_data():
    payload = request.get_json() or {}
    columns = payload.get("columns", [])
    rows    = payload.get("rows", [])

    # Asegurar tipos string
    df = pd.DataFrame(rows, columns=columns).astype(str)
    df = ensure_columns(df)

    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl",
                        mode="a", if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name=SHEET_NAME, index=False)
    return jsonify({"success": True})


@app.route("/upload-photo", methods=["POST"])
def upload_photo():
    if "photo" not in request.files:
        return jsonify({"success": False, "message": "Falta archivo 'photo'."}), 400

    file    = request.files["photo"]
    first   = request.form.get("firstName", "")
    paterno = request.form.get("paterno", "")
    materno = request.form.get("materno", "")

    # Construye el basename codificado según el patrón deseado
    encoded_base = build_encoded_basename(first, paterno, materno)

    # Usa la extensión original (en minúsculas); si no hay, default .webp
    ext = os.path.splitext(file.filename)[1].lower() or ".webp"

    # Borra fotos previas que comiencen con el mismo basename codificado
    for f in os.listdir(FOTOS_FOLDER):
        if f.startswith(encoded_base + ".") or f.startswith(encoded_base + "_"):
            try:
                os.remove(os.path.join(FOTOS_FOLDER, f))
            except OSError:
                pass

    filename = encoded_base + ext
    path     = os.path.join(FOTOS_FOLDER, filename)
    file.save(path)

    # Actualiza el Excel con el nombre de archivo codificado
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, dtype=str)
    df = ensure_columns(df)
    mask = (
        (df["Nombre"] == str(first)) &
        (df["Apellido Paterno"] == str(paterno)) &
        (df["Apellido Materno"] == str(materno))
    )
    df.loc[mask, "Foto"] = filename

    with pd.ExcelWriter(EXCEL_PATH, engine="openpyxl",
                        mode="a", if_sheet_exists="replace") as w:
        df.to_excel(w, sheet_name=SHEET_NAME, index=False)

    return jsonify({"success": True, "filename": filename})


@app.route("/download", methods=["GET"])
def download_excel():
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, dtype=str)
    df = ensure_columns(df)
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, sheet_name=SHEET_NAME, index=False)
    out.seek(0)
    return send_file(
        out,
        as_attachment=True,
        download_name="DIRECTORIO.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6100)
