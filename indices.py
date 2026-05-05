import sqlite3
import time  # para medir el tiempo de ejecución y comparar con/sin índice

conexion = sqlite3.connect("commerce.db")
cursor = conexion.cursor()
cursor.execute("PRAGMA foreign_keys = ON")

# ─────────────────────────────────────────────────────────────
# Medimos el tiempo de una consulta ANTES de crear índices
# Esto cumple el bonus de comparación de performance
# ─────────────────────────────────────────────────────────────

def medir(descripcion, sql):
    inicio = time.time()          # guardamos el tiempo antes de ejecutar
    cursor.execute(sql)
    cursor.fetchall()             # fetchall fuerza que SQLite procese todos los resultados
    fin = time.time()             # guardamos el tiempo después
    duracion = (fin - inicio) * 1000  # convertimos a milisegundos
    print(f"  {descripcion}: {duracion:.2f} ms")

print("=== Sin índices ===")
medir("orders por customer_id",
    "SELECT * FROM orders WHERE customer_id = 5000")
medir("payments por order_id",
    "SELECT * FROM payments WHERE order_id = 50000")
medir("order_items por order_id",
    "SELECT * FROM order_items WHERE order_id = 50000")
medir("order_status_history por order_id",
    "SELECT * FROM order_status_history WHERE order_id = 50000")

# ─────────────────────────────────────────────────────────────
# Creamos los índices en las FK y columnas de búsqueda frecuente
# IF NOT EXISTS: no falla si el índice ya existe
# ─────────────────────────────────────────────────────────────

print("\nCreando índices...")

# Índices en FK de orders — la tabla más consultada
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_orders_customer_id
    ON orders(customer_id)
""")
# idx_ es la convención de nombre: idx_tabla_columna

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_orders_current_status
    ON orders(current_status)
""")
# current_status aparece en casi todos los WHERE de navegación

# Índices en FK de order_items — tabla con más filas (360k)
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_order_items_order_id
    ON order_items(order_id)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_order_items_product_id
    ON order_items(product_id)
""")

# Índices en FK de las tablas de auditoría e historial
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_payments_order_id
    ON payments(order_id)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_order_status_history_order_id
    ON order_status_history(order_id)
""")

cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_order_audit_order_id
    ON order_audit(order_id)
""")

# Índice en email de customers — columna UNIQUE que se usa para login
cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_customers_email
    ON customers(email)
""")

conexion.commit()
print("Índices creados.")

# ─────────────────────────────────────────────────────────────
# Medimos el tiempo DESPUÉS de crear índices — comparación
# ─────────────────────────────────────────────────────────────

print("\n=== Con índices ===")
medir("orders por customer_id",
    "SELECT * FROM orders WHERE customer_id = 5000")
medir("payments por order_id",
    "SELECT * FROM payments WHERE order_id = 50000")
medir("order_items por order_id",
    "SELECT * FROM order_items WHERE order_id = 50000")
medir("order_status_history por order_id",
    "SELECT * FROM order_status_history WHERE order_id = 50000")

conexion.close()