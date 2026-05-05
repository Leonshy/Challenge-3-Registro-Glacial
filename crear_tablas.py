import sqlite3  # módulo estándar de Python, no requiere instalación externa

# Conectamos a la base — si commerce.db no existe, SQLite lo crea automáticamente
conexion = sqlite3.connect("commerce.db")

# El cursor es el objeto que ejecuta sentencias SQL dentro de la conexión
cursor = conexion.cursor()

# las FK están desactivadas por defecto. Esta línea debe ejecutarse en cada conexión nueva
cursor.execute("PRAGMA foreign_keys = ON")

# ─────────────────────────────────────────────────────────────
# Tabla: customers
# Entidad maestra — existe por sí sola, no depende de nadie
# ─────────────────────────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS customers (
        customer_id  INTEGER  PRIMARY KEY,
        full_name    TEXT     NOT NULL,
        email        TEXT     NOT NULL UNIQUE,       -- dos clientes no pueden tener el mismo email
        phone        TEXT,                           -- opcional
        city         TEXT,                           -- opcional
        segment      TEXT     NOT NULL               -- valores: retail, wholesale, vip, online_only
                     CHECK (segment IN ('retail', 'wholesale', 'vip', 'online_only')),
        created_at   DATETIME NOT NULL,
        is_active    INTEGER  NOT NULL DEFAULT 1     -- soft delete: 1 = activo, 0 = dado de baja
                     CHECK (is_active IN (0, 1)),
        deleted_at   DATETIME                        -- NULL si el cliente sigue activo
    )
""")

# ─────────────────────────────────────────────────────────────
# Tabla: products
# Entidad maestra — existe por sí sola, no depende de nadie
# ─────────────────────────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id   INTEGER  PRIMARY KEY,
        sku          TEXT     NOT NULL UNIQUE,        -- código de producto, no puede repetirse
        product_name TEXT     NOT NULL,
        category     TEXT     NOT NULL
                     CHECK (category IN (
                         'automotive','beauty','books','electronics',
                         'fashion','grocery','home','office','sports','toys'
                     )),
        brand        TEXT,
        unit_price   REAL     NOT NULL CHECK (unit_price > 0),   -- precio de venta, siempre positivo
        unit_cost    REAL     NOT NULL CHECK (unit_cost > 0),    -- costo interno, siempre positivo
        created_at   DATETIME NOT NULL,
        is_active    INTEGER  NOT NULL DEFAULT 1
                     CHECK (is_active IN (0, 1)),
        deleted_at   DATETIME
    )
""")

# ─────────────────────────────────────────────────────────────
# Tabla: orders
# Núcleo transaccional — depende de customers (FK)
# ─────────────────────────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS orders (
        order_id       INTEGER  PRIMARY KEY,
        customer_id    INTEGER  NOT NULL
                       REFERENCES customers(customer_id),  -- FK: el cliente debe existir
        order_datetime DATETIME NOT NULL,
        channel        TEXT     NOT NULL
                       CHECK (channel IN ('web', 'mobile', 'store', 'phone')),
        currency       TEXT     NOT NULL
                       CHECK (currency IN ('PYG', 'USD')),
        current_status TEXT     NOT NULL
                       CHECK (current_status IN (
                           'created','packed','shipped','delivered',
                           'cancelled','paid','refunded'
                       )),
        order_total    REAL     NOT NULL CHECK (order_total >= 0),
        is_active      INTEGER  NOT NULL DEFAULT 1
                       CHECK (is_active IN (0, 1)),
        deleted_at     DATETIME
    )
""")

# ─────────────────────────────────────────────────────────────
# Tabla: payments
# Registra los pagos asociados a un pedido
# Un pedido puede tener varios pagos (ej: un rechazo y luego una aprobación)
# ─────────────────────────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        payment_id       INTEGER  PRIMARY KEY,
        order_id         INTEGER  NOT NULL
                         REFERENCES orders(order_id),   -- FK: el pedido debe existir
        payment_datetime DATETIME NOT NULL,
        method           TEXT     NOT NULL
                         CHECK (method IN ('card', 'cash', 'transfer', 'wallet')),
        payment_status   TEXT     NOT NULL
                         CHECK (payment_status IN ('approved', 'pending', 'rejected', 'refunded')),
        amount           REAL     NOT NULL CHECK (amount > 0),  -- el monto siempre es positivo
        currency         TEXT     NOT NULL
                         CHECK (currency IN ('PYG', 'USD'))
    )
""")

# ─────────────────────────────────────────────────────────────
# Tabla: order_status_history
# Registra cada cambio de estado de un pedido — la historia completa
# current_status en orders es solo la foto actual, esta tabla es la película
# ─────────────────────────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_status_history (
        status_history_id INTEGER  PRIMARY KEY,
        order_id          INTEGER  NOT NULL
                          REFERENCES orders(order_id),  -- FK: el pedido debe existir
        status            TEXT     NOT NULL
                          CHECK (status IN (
                              'created','packed','shipped','delivered',
                              'cancelled','paid','refunded'
                          )),
        changed_at        DATETIME NOT NULL,
        changed_by        TEXT     NOT NULL
                          CHECK (changed_by IN (
                              'user','system','ops','warehouse','payment_gateway'
                          )),
        reason            TEXT     -- opcional, puede ser NULL
    )
""")

# ─────────────────────────────────────────────────────────────
# Tabla: order_audit
# Registra cambios en campos específicos de un pedido
# Responde: ¿quién modificó qué campo, cuándo y a qué valor?
# ─────────────────────────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_audit (
        audit_id   INTEGER  PRIMARY KEY,
        order_id   INTEGER  NOT NULL
                   REFERENCES orders(order_id),         -- FK: el pedido debe existir
        field_name TEXT     NOT NULL
                   CHECK (field_name IN (
                       'current_status','order_total',
                       'shipping_address','customer_phone','notes'
                   )),
        old_value  TEXT,    -- valor anterior, puede ser NULL si era un campo vacío
        new_value  TEXT,    -- valor nuevo, puede ser NULL si se borró el campo
        changed_at DATETIME NOT NULL,
        changed_by TEXT     NOT NULL
                   CHECK (changed_by IN ('system', 'support', 'ops'))
    )
""")

# ─────────────────────────────────────────────────────────────
# Tabla: orders_items
# Núcleo transaccional — depende de order y product (FK)
# ─────────────────────────────────────────────────────────────
cursor.execute("""
    CREATE TABLE IF NOT EXISTS order_items (
        order_item_id   INTEGER  PRIMARY KEY,
        order_id        INTEGER  NOT NULL 
                        REFERENCES orders(order_id),  
        product_id      INTEGER NOT NULL
                        REFERENCES products(product_id),
        quantity        INTEGER NOT NULL CHECK (quantity > 0),
        unit_price      REAL    NOT NULL CHECK (unit_price > 0),
        discount_rate   REAL NOT NULL CHECK (discount_rate >= 0 AND discount_rate <= 1),
        line_total      REAL NOT NULL CHECK (line_total >= 0)
    )
""")

# Persistimos las tablas creadas hasta ahora
conexion.commit()

# ─────────────────────────────────────────────────────────────
# Insertamos datos de prueba respetando el orden lógico:
# primero el cliente, luego el pedido que lo referencia
# ─────────────────────────────────────────────────────────────

# Insertamos un cliente usando ? para evitar SQL Injection y facilitar la lectura
cursor.execute("""
    INSERT OR IGNORE INTO customers
        (customer_id, full_name, email, phone, city, segment, created_at, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (1, "Luis Fernandez", "luis@mail.com", "+595992795509", "Asunción", "retail", "2023-08-13T18:40:42", 1))
# OR IGNORE: si el customer_id ya existe, no falla — útil al re-ejecutar el script

# Primero insertamos un producto de prueba (si no existe ya)
cursor.execute("""
    INSERT OR IGNORE INTO products
        (product_id, sku, product_name, category, brand, unit_price, unit_cost, created_at, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (1, "SKU-658EDSCIEQ", "Mares fashion RIYK", "fashion", "Mares", 366.0, 298.81, "2023-05-03T23:21:51", 1))

# Insertamos un pedido que referencia al cliente anterior
cursor.execute("""
    INSERT OR IGNORE INTO orders
        (order_id, customer_id, order_datetime, channel, currency, current_status, order_total, is_active)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
""", (1, 1, "2024-10-04T13:09:18", "mobile", "PYG", "shipped", 4364.24, 1))


# Ahora sí podemos insertar un order_item que referencia order_id=1 y product_id=1
cursor.execute("""
    INSERT OR IGNORE INTO order_items
        (order_item_id, order_id, product_id, quantity, unit_price, discount_rate, line_total)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", (1, 1, 1, 2, 366.0, 0.05, 732.0))

conexion.commit()

# ─────────────────────────────────────────────────────────────
# Probamos que la FK funciona — esto debe fallar con un error
# ─────────────────────────────────────────────────────────────
print("Probando integridad referencial...")
try:
    cursor.execute("""
        INSERT INTO orders (order_id, customer_id, order_datetime, channel, currency, current_status, order_total, is_active)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (999, 99999, "2024-01-01T00:00:00", "web", "PYG", "created", 100.0, 1))
    # customer_id 99999 no existe — con PRAGMA foreign_keys ON, esto debe lanzar una excepción
    conexion.commit()
    print("ERROR: la FK no está funcionando — revisá el PRAGMA")
except sqlite3.IntegrityError as e:
    print(f"Correcto — la base rechazó el pedido: {e}")
    # IntegrityError es la excepción que lanza SQLite cuando se viola una constraint

# ─────────────────────────────────────────────────────────────
# Consulta básica con JOIN — relacionamos orders con customers
# JOIN une las filas de dos tablas donde la condición se cumple
# ─────────────────────────────────────────────────────────────
cursor.execute("""
    SELECT
        o.order_id,           -- columna de la tabla orders
        c.full_name,          -- columna de la tabla customers
        o.current_status,
        o.order_total
    FROM orders o             -- "o" es un alias para no escribir "orders" cada vez
    JOIN customers c          -- "c" es un alias para customers
        ON o.customer_id = c.customer_id   -- condición de unión: la FK coincide con la PK
    ORDER BY o.order_id
""")

print("\nPedidos con nombre de cliente:")
for fila in cursor.fetchall():
    print(fila)  # cada fila: (order_id, full_name, current_status, order_total)

# Verificamos qué tablas existen en la base
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
print("\nTablas creadas:", cursor.fetchall())

conexion.close()  # liberamos el archivo .db