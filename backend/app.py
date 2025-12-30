import os
import pyodbc
from io import BytesIO
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)

# CONFIGURACIÓN CORS
CORS(app, resources={r"/*": {
    "origins": ["http://localhost:3000", "http://127.0.0.1:3000", 
                "http://localhost:4100", "http://127.0.0.1:4100"]
}})

# CONFIGURACIÓN SQL SERVER
SQL_CONN_STR = (
    "Driver={ODBC Driver 17 for SQL Server};"
    "Server=DESKTOP-EO74OCH\\SQLEXPRESS;"
    "Database=punta_medica;"
    "Trusted_Connection=yes;"
    "Encrypt=no;"
    "TrustServerCertificate=yes;"
)

FOTOS_FOLDER = r"D:\028 Punta Medica\Codigo interno Completo\Comprimido1\App Pantallas\frontend\public\Medicos"
os.makedirs(FOTOS_FOLDER, exist_ok=True)

def get_db_connection():
    return pyodbc.connect(SQL_CONN_STR)

# ---------- INICIALIZACIÓN DE TABLA MÉDICOS ----------
def init_db_directorio():
    conn = get_db_connection()
    cursor = conn.cursor()
    # Tabla Medicos (Sustituye al Excel DIRECTORIO.xlsx)
    cursor.execute('''IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='Medicos' AND xtype='U')
                      CREATE TABLE Medicos (
                          Id_Medico INT PRIMARY KEY IDENTITY(1,1),
                          Nombre VARCHAR(100),
                          Apellido_Paterno VARCHAR(100),
                          Apellido_Materno VARCHAR(100),
                          Especialidad VARCHAR(150),
                          Subespecialidad VARCHAR(150),
                          Consultorio VARCHAR(50),
                          Telefono VARCHAR(50),
                          Foto VARCHAR(255),
                          Activo BIT DEFAULT 1
                      )''')
    conn.commit()
    conn.close()

init_db_directorio()

# ---------- UTILIDADES (SANATIZACIÓN) ----------
def build_encoded_basename(first_name, paterno, materno):
    def norm_no_spaces(s): return "".join((s or "").split()).lower()
    def sanitize(s):
        if not s: return ""
        forbidden = set('\\/:*?"<>|')
        return "".join(ch for ch in s if ch not in forbidden).rstrip(" .")
    
    first = sanitize(norm_no_spaces(first_name))
    pat = sanitize(norm_no_spaces(paterno))
    mat = sanitize(norm_no_spaces(materno))
    return "_".join([p for p in [first, pat, mat] if p])

# ---------- ENDPOINTS ----------

@app.route("/login", methods=["POST"])
def login():
    """
    ANTERIOR (EXCEL):
    df = pd.read_excel(USERS_PATH, dtype=str)
    ok = not df[(df.get("user") == user) & (df.get("password") == pw)].empty
    """
    data = request.get_json() or {}
    user = data.get("user", "")
    pw = data.get("password", "")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Usuarios WHERE Username = ? AND Password = ?", (user, pw))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "message": "Credenciales inválidas"}), 401

@app.route("/data", methods=["GET"])
def get_data():
    """
    ANTERIOR (EXCEL):
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME, dtype=str)
    return jsonify({"columns": list(df.columns), "rows": df.values.tolist()})
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Medicos WHERE Activo = 1")
    columns = [column[0] for column in cursor.description]
    rows = [list(row) for row in cursor.fetchall()]
    conn.close()
    
    return jsonify({
        "columns": columns,
        "rows": rows
    })

@app.route("/save", methods=["POST"])
def save_data():
    """
    ANTERIOR (EXCEL):
    df = pd.DataFrame(rows, columns=columns)
    df.to_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
    """
    # Esta ruta ahora inserta un nuevo médico en la BD
    payload = request.get_json() or {}
    r = payload.get("data", {}) # Se espera un objeto con los campos del médico
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""INSERT INTO Medicos (Nombre, Apellido_Paterno, Apellido_Materno, Especialidad, Foto) 
                      VALUES (?, ?, ?, ?, ?)""", 
                   (r.get('Nombre'), r.get('Apellido Paterno'), r.get('Apellido Materno'), 
                    r.get('Especialidad'), r.get('Foto', '')))
    conn.commit()
    conn.close()
    return jsonify({"success": True})

@app.route("/upload-photo", methods=["POST"])
def upload_photo():
    """
    ANTERIOR (EXCEL):
    Actualizaba la celda del Excel con el nombre del archivo.
    """
    if "photo" not in request.files:
        return jsonify({"success": False, "message": "Falta archivo."}), 400

    file = request.files["photo"]
    first = request.form.get("firstName", "")
    paterno = request.form.get("paterno", "")
    materno = request.form.get("materno", "")

    encoded_base = build_encoded_basename(first, paterno, materno)
    ext = os.path.splitext(file.filename)[1].lower() or ".webp"
    filename = encoded_base + ext
    path = os.path.join(FOTOS_FOLDER, filename)
    
    # Guardar archivo físico
    file.save(path)

    # Actualizar BD en lugar de Excel
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""UPDATE Medicos SET Foto = ? 
                      WHERE Nombre = ? AND Apellido_Paterno = ? AND Apellido_Materno = ?""",
                   (filename, first, paterno, materno))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "filename": filename})

@app.route("/download", methods=["GET"])
def download_excel():
    """
    SE MANTIENE: Genera un Excel al vuelo desde la base de datos SQL 
    para reportes, sin necesidad de tener un archivo físico permanente.
    """
    import pandas as pd
    conn = get_db_connection()
    df = pd.read_sql("SELECT * FROM Medicos", conn)
    conn.close()
    
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    out.seek(0)
    return send_file(out, as_attachment=True, download_name="DIRECTORIO_EXPORTADO.xlsx",
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=6100)