import sqlite3

conexion = sqlite3.connect("commerce.db")
cursor = conexion.cursor()
cursor.execute("PRAGMA foreign_keys = ON")

# ─────────────────────────────────────────────────────────────
# Función auxiliar para imprimir resultados con encabezado
# ─────────────────────────────────────────────────────────────
def ejecutar(titulo, sql):
    print(f"\n{'='*60}")
    print(f"  {titulo}")
    print(f"{'='*60}")
    cursor.execute(sql)
    filas = cursor.fetchmany(10)  # mostramos solo las primeras 10 filas
    if not filas:
        print("  (sin resultados)")
    for fila in filas:
        print(" ", fila)

# ═════════════════════════════════════════════════════════════
# BLOQUE 1 — Navegación del modelo
# Consultas que recorren las relaciones entre tablas
# ═════════════════════════════════════════════════════════════

# Consulta 1: pedidos con nombre de cliente y estado actual
# JOIN simple entre orders y customers
ejecutar("Pedidos con nombre de cliente", """
    SELECT
        o.order_id,
        c.full_name,
        c.segment,
        o.current_status,
        o.order_total,
        o.order_datetime
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    ORDER BY o.order_datetime DESC
""")

# Consulta 2: detalle de un pedido — qué productos tiene y a qué precio
# JOIN entre order_items y products
ejecutar("Detalle de productos del pedido #1", """
    SELECT
        oi.order_item_id,
        p.product_name,
        p.category,
        oi.quantity,
        oi.unit_price,
        oi.discount_rate,
        oi.line_total
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    WHERE oi.order_id = 1
    ORDER BY oi.order_item_id
""")

# Consulta 3: historial completo de estados de un pedido
# muestra la "película" de un pedido, no solo la foto actual
ejecutar("Historial de estados del pedido #1", """
    SELECT
        sh.status,
        sh.changed_at,
        sh.changed_by,
        sh.reason
    FROM order_status_history sh
    WHERE sh.order_id = 1
    ORDER BY sh.changed_at ASC
""")

# Consulta 4: pagos de un pedido con su estado
ejecutar("Pagos del pedido #100", """
    SELECT
        p.payment_id,
        p.payment_datetime,
        p.method,
        p.payment_status,
        p.amount,
        p.currency
    FROM payments p
    WHERE p.order_id = 100
    ORDER BY p.payment_datetime ASC
""")

# Consulta 5: auditoría de un pedido — quién cambió qué y cuándo
ejecutar("Auditoría del pedido #1000", """
    SELECT
        a.field_name,
        a.old_value,
        a.new_value,
        a.changed_at,
        a.changed_by
    FROM order_audit a
    WHERE a.order_id = 1000
    ORDER BY a.changed_at ASC
""")

# ═════════════════════════════════════════════════════════════
# BLOQUE 2 — Rastreo de estados y eventos
# Consultas que buscan patrones específicos en los datos
# ═════════════════════════════════════════════════════════════

# Consulta 6: pedidos entregados de clientes VIP
# combina filtro por segmento y por estado
ejecutar("Pedidos entregados de clientes VIP", """
    SELECT
        o.order_id,
        c.full_name,
        o.order_total,
        o.order_datetime
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE c.segment = 'vip'
      AND o.current_status = 'delivered'
    ORDER BY o.order_total DESC
""")

# Consulta 7: pedidos con pagos rechazados
# un pedido puede tener un pago rechazado y luego uno aprobado
ejecutar("Pedidos con algún pago rechazado", """
    SELECT
        o.order_id,
        o.current_status,
        p.method,
        p.payment_status,
        p.amount
    FROM orders o
    JOIN payments p ON o.order_id = p.order_id
    WHERE p.payment_status = 'rejected'
    ORDER BY o.order_id
""")

# Consulta 8: productos con descuento aplicado en sus ventas
ejecutar("Items con descuento mayor al 20%", """
    SELECT
        oi.order_item_id,
        p.product_name,
        oi.discount_rate,
        oi.unit_price,
        oi.line_total
    FROM order_items oi
    JOIN products p ON oi.product_id = p.product_id
    WHERE oi.discount_rate > 0.20
    ORDER BY oi.discount_rate DESC
""")

# ═════════════════════════════════════════════════════════════
# BLOQUE 3 — Detección de ausencias e inconsistencias
# LEFT JOIN para encontrar registros que deberían tener algo pero no tienen
# ═════════════════════════════════════════════════════════════

# Consulta 9: pedidos sin ningún pago registrado
# LEFT JOIN + IS NULL detecta los pedidos huérfanos de pagos
ejecutar("Pedidos sin ningún pago registrado", """
    SELECT
        o.order_id,
        o.current_status,
        o.order_total,
        o.order_datetime
    FROM orders o
    LEFT JOIN payments p ON o.order_id = p.order_id
    WHERE p.payment_id IS NULL
    ORDER BY o.order_datetime DESC
""")

# Consulta 10: pedidos marcados como 'delivered' sin historial de entrega
# un pedido delivered debería tener al menos un registro 'delivered' en el historial
ejecutar("Pedidos delivered sin registro en historial", """
    SELECT
        o.order_id,
        o.current_status,
        o.order_datetime
    FROM orders o
    LEFT JOIN order_status_history sh
        ON o.order_id = sh.order_id
        AND sh.status = 'delivered'
    WHERE o.current_status = 'delivered'
      AND sh.status_history_id IS NULL
    ORDER BY o.order_id
""")

# Consulta 11: clientes activos sin ningún pedido
# detecta clientes registrados que nunca compraron
ejecutar("Clientes activos sin pedidos", """
    SELECT
        c.customer_id,
        c.full_name,
        c.segment,
        c.created_at
    FROM customers c
    LEFT JOIN orders o ON c.customer_id = o.customer_id
    WHERE c.is_active = 1
      AND o.order_id IS NULL
    ORDER BY c.created_at DESC
""")

# Consulta 12: productos activos que nunca fueron vendidos
ejecutar("Productos activos sin ventas", """
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        p.unit_price
    FROM products p
    LEFT JOIN order_items oi ON p.product_id = oi.product_id
    WHERE p.is_active = 1
      AND oi.order_item_id IS NULL
    ORDER BY p.category
""")

conexion.close()