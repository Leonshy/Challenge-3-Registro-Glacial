import sqlite3  # para conectarnos a la base
import csv      # para leer los archivos CSV
import os       # para construir rutas de archivo de forma segura

# ─────────────────────────────────────────────────────────────
# Configuración — ajustá estas rutas a tu estructura de carpetas
# ─────────────────────────────────────────────────────────────

# Ruta a la base de datos
DB_PATH = "commerce.db"

# Carpeta donde están los CSV — os.path.join construye la ruta correcta
# en cualquier sistema operativo (Mac, Windows, Linux)
CSV_DIR = os.path.join(os.path.dirname(__file__), "data")

# ─────────────────────────────────────────────────────────────
# Funciones auxiliares para convertir tipos
# csv.DictReader devuelve todo como string — hay que convertir
# ─────────────────────────────────────────────────────────────

def texto_o_none(valor):
    # si el campo está vacío en el CSV, devolvemos None (NULL en SQLite)
    return valor if valor.strip() != "" else None

def entero_o_none(valor):
    # convertimos a int, o None si está vacío
    v = texto_o_none(valor)
    return int(v) if v is not None else None

def flotante_o_none(valor):
    # convertimos a float, o None si está vacío
    v = texto_o_none(valor)
    return float(v) if v is not None else None

# ─────────────────────────────────────────────────────────────
# Función principal de carga
# Recibe el cursor, la sentencia INSERT y un generador de filas
# Registra cuántos registros se insertaron y cuántos fallaron
# ─────────────────────────────────────────────────────────────
def cargar_tabla(cursor, nombre_tabla, sentencia_insert, generador_filas):
    insertados = 0
    errores = 0

    for fila in generador_filas:
        try:
            cursor.execute(sentencia_insert, fila)
            insertados += 1
        except sqlite3.IntegrityError as e:
            mensaje = str(e)
            if "UNIQUE" in mensaje:
                pass
            else:
                errores += 1
                print(f"  [VIOLACIÓN] {mensaje} → {fila}")

    print(f"  {nombre_tabla}: {insertados} insertados, {errores} errores")
    return insertados, errores

# ─────────────────────────────────────────────────────────────
# Generadores de filas — uno por tabla
# Cada función lee su CSV y transforma las filas al formato
# que espera el INSERT (tupla con los valores en el orden correcto)
# ─────────────────────────────────────────────────────────────

def filas_customers(csv_dir):
    # abrimos el CSV con encoding utf-8 para manejar caracteres especiales
    with open(os.path.join(csv_dir, "customers.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            yield (                              # yield convierte la función en un generador
                int(fila["customer_id"]),        # INTEGER — siempre presente
                fila["full_name"],               # TEXT NOT NULL
                fila["email"],                   # TEXT NOT NULL UNIQUE
                texto_o_none(fila["phone"]),     # TEXT opcional
                texto_o_none(fila["city"]),      # TEXT opcional
                fila["segment"],                 # TEXT NOT NULL con CHECK
                fila["created_at"],              # DATETIME NOT NULL
                int(fila["is_active"]),          # INTEGER 0 o 1
                texto_o_none(fila["deleted_at"]) # DATETIME opcional (soft delete)
            )

def filas_products(csv_dir):
    with open(os.path.join(csv_dir, "products.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            yield (
                int(fila["product_id"]),
                fila["sku"],
                fila["product_name"],
                fila["category"],
                texto_o_none(fila["brand"]),
                float(fila["unit_price"]),
                float(fila["unit_cost"]),
                fila["created_at"],
                int(fila["is_active"]),
                texto_o_none(fila["deleted_at"])
            )

def filas_orders(csv_dir):
    with open(os.path.join(csv_dir, "orders.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            yield (
                int(fila["order_id"]),
                int(fila["customer_id"]),        # FK → customers
                fila["order_datetime"],
                fila["channel"],
                fila["currency"],
                fila["current_status"],
                float(fila["order_total"]),
                int(fila["is_active"]),
                texto_o_none(fila["deleted_at"])
            )

def filas_order_items(csv_dir):
    with open(os.path.join(csv_dir, "order_items.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            yield (
                int(fila["order_item_id"]),
                int(fila["order_id"]),           # FK → orders
                int(fila["product_id"]),          # FK → products
                int(fila["quantity"]),
                float(fila["unit_price"]),
                float(fila["discount_rate"]),
                float(fila["line_total"])
            )

def filas_payments(csv_dir):
    with open(os.path.join(csv_dir, "payments.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            yield (
                int(fila["payment_id"]),
                int(fila["order_id"]),           # FK → orders
                fila["payment_datetime"],
                fila["method"],
                fila["payment_status"],
                float(fila["amount"]),
                fila["currency"]
            )

def filas_order_status_history(csv_dir):
    with open(os.path.join(csv_dir, "order_status_history.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            yield (
                int(fila["status_history_id"]),
                int(fila["order_id"]),           # FK → orders
                fila["status"],
                fila["changed_at"],
                fila["changed_by"],
                texto_o_none(fila["reason"])     # opcional
            )

def filas_order_audit(csv_dir):
    with open(os.path.join(csv_dir, "order_audit.csv"), encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            yield (
                int(fila["audit_id"]),
                int(fila["order_id"]),           # FK → orders
                fila["field_name"],
                texto_o_none(fila["old_value"]), # puede ser NULL
                texto_o_none(fila["new_value"]), # puede ser NULL
                fila["changed_at"],
                fila["changed_by"]
            )

# ─────────────────────────────────────────────────────────────
# Ejecución principal
# ─────────────────────────────────────────────────────────────
print("Iniciando carga de datos...\n")

conexion = sqlite3.connect(DB_PATH)
cursor = conexion.cursor()
cursor.execute("PRAGMA foreign_keys = ON")  # activamos FK — obligatorio en cada conexión

# Cargamos en orden lógico: primero las tablas padre, luego las hijas
# Si invertimos el orden, las FK van a rechazar los inserts

cargar_tabla(cursor, "customers", """
    INSERT OR IGNORE INTO customers
    VALUES (?,?,?,?,?,?,?,?,?)
""", filas_customers(CSV_DIR))
conexion.commit()  # commit después de cada tabla — si algo falla no perdemos lo anterior

cargar_tabla(cursor, "products", """
    INSERT OR IGNORE INTO products
    VALUES (?,?,?,?,?,?,?,?,?,?)
""", filas_products(CSV_DIR))
conexion.commit()

cargar_tabla(cursor, "orders", """
    INSERT OR IGNORE INTO orders
    VALUES (?,?,?,?,?,?,?,?,?)
""", filas_orders(CSV_DIR))
conexion.commit()

cargar_tabla(cursor, "order_items", """
    INSERT OR IGNORE INTO order_items
    VALUES (?,?,?,?,?,?,?)
""", filas_order_items(CSV_DIR))
conexion.commit()

cargar_tabla(cursor, "payments", """
    INSERT OR IGNORE INTO payments
    VALUES (?,?,?,?,?,?,?)
""", filas_payments(CSV_DIR))
conexion.commit()

cargar_tabla(cursor, "order_status_history", """
    INSERT OR IGNORE INTO order_status_history
    VALUES (?,?,?,?,?,?)
""", filas_order_status_history(CSV_DIR))
conexion.commit()

cargar_tabla(cursor, "order_audit", """
    INSERT OR IGNORE INTO order_audit
    VALUES (?,?,?,?,?,?,?)
""", filas_order_audit(CSV_DIR))
conexion.commit()

print("\nCarga completa.")
conexion.close()