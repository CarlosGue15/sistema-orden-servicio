import os
import json
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
# CORS abierto para permitir llamadas desde Vercel o local
CORS(app)

# Toma la URL de conexión desde la variable de entorno configurada en Render
DATABASE_URL = os.environ.get("DATABASE_URL")

# Lista de campos que se guardan como columnas en PostgreSQL
CAMPOS_FIJOS = [
    "numOR", "fecha", "hora", "km", "cliente", "placa", "bateria",
    "inventarioRecepcion", "inventarioEntrega", "condicionLimpieza",
    "sujecionRecepcion", "sujecionEntrega",
    "pintura", "rines", "tapiceria", "obsInspVisual", "nivelGasolina",
    "observacionesGenerales",
]


def get_connection():
    """Establece conexión a la base de datos Supabase forzando SSL"""
    if not DATABASE_URL:
        raise ValueError("La variable de entorno DATABASE_URL no está configurada.")
    
    # Supabase requiere sslmode='require'
    return psycopg2.connect(DATABASE_URL, sslmode="require")


@app.route("/", methods=["GET"])
def health_check():
    """Ruta simple para verificar que la API está encendida en Render"""
    return jsonify({
        "status": "online",
        "message": "Servidor Backend para Órdenes de Servicio activo"
    }), 200


@app.route("/api/ordenes", methods=["POST"])
def crear_orden():
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "No se recibió un JSON válido en la petición"}), 400

    # Extrae los campos fijos y agrupa todos los demás en 'detalles'
    fijo = {campo: (data.get(campo) or None) for campo in CAMPOS_FIJOS}
    detalles = {k: v for k, v in data.items() if k not in CAMPOS_FIJOS}

    sql = """
        INSERT INTO ordenes_servicio (
            num_or, fecha, hora, km, cliente, placa, bateria,
            inventario_recepcion, inventario_entrega, condicion_limpieza,
            sujecion_recepcion, sujecion_entrega,
            pintura, rines, tapiceria, obs_insp_visual, nivel_gasolina,
            observaciones_generales, detalles_json
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        RETURNING id;
    """
    
    valores = (
        fijo["numOR"], fijo["fecha"], fijo["hora"], fijo["km"],
        fijo["cliente"], fijo["placa"], fijo["bateria"],
        fijo["inventarioRecepcion"], fijo["inventarioEntrega"], fijo["condicionLimpieza"],
        fijo["sujecionRecepcion"], fijo["sujecionEntrega"],
        fijo["pintura"], fijo["rines"], fijo["tapiceria"],
        fijo["obsInspVisual"], fijo["nivelGasolina"],
        fijo["observacionesGenerales"],
        json.dumps(detalles, ensure_ascii=False)
    )

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(sql, valores)
        nuevo_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Error en la base de datos: {str(e)}"}), 500

    return jsonify({"status": "ok", "id": nuevo_id}), 201


@app.route("/api/ordenes", methods=["GET"])
def listar_ordenes():
    """Consulta opcional para ver todas las órdenes registradas"""
    try:
        conn = get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM ordenes_servicio ORDER BY created_at DESC;")
        filas = cursor.fetchall()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({"error": f"Error en la base de datos: {str(e)}"}), 500

    return jsonify(filas), 200


if __name__ == "__main__":
    # Permite ejecutar de manera local para pruebas en puerto 5000
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)