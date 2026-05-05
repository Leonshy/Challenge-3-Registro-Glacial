# 🗄️ TRANSACT SQL — Núcleo Transaccional de Penguin Academy

Una base de datos relacional funcional construida en Python + SQLite como parte del challenge **Penguin Academy — Sistema de Registro Glacial**.

---

## 🎯 Descripción

El sistema modela el núcleo transaccional de un comercio electrónico paraguayo. A partir de 7 archivos CSV con ~988 000 filas, se construyó un modelo relacional con integridad referencial real, consultas estructurales que navegan el modelo, y detección de inconsistencias en los datos.

El sistema responde la pregunta del enunciado: **"¿Quién modificó esto y cuándo?"** — a través de las tablas `order_status_history` y `order_audit`.

---

## 🚀 Cómo ejecutar

Requiere Python 3.10 o superior. No requiere dependencias externas.

**1. Crear las tablas:**
```bash
python3 crear_tablas.py
```

**2. Cargar los datos desde CSV:**
```bash
python3 cargar_datos.py
```

**3. Ejecutar las consultas:**
```bash
python3 consultas.py
```

**4. Crear índices y medir performance:**
```bash
python3 indices.py
```

Los CSV deben estar en la carpeta `data/` dentro del proyecto.

---

## 🏗️ Estructura del proyecto

```
Challenge-3-Registro-Glacial/
├── data/                         → archivos CSV originales (7 archivos)
│   ├── customers.csv             → 30 000 clientes
│   ├── products.csv              → 8 000 productos
│   ├── orders.csv                → 120 000 pedidos
│   ├── order_items.csv           → 360 000 items de pedido
│   ├── payments.csv              → 140 000 pagos
│   ├── order_status_history.csv  → 250 000 cambios de estado
│   └── order_audit.csv           → 80 000 registros de auditoría
├── crear_tablas.py               → crea las 7 tablas con todos los constraints
├── cargar_datos.py               → carga los CSV respetando orden de inserción
├── consultas.py                  → 12 consultas estructurales del challenge
├── indices.py                    → crea índices y mide comparación de performance
├── commerce.db                   → base de datos SQLite generada
└── README.md
```

---

## 🧱 Modelo relacional

El modelo se divide en tres grupos lógicos:

**Entidades maestras** — existen por sí solas, no dependen de nadie:
- `customers` — clientes con soft delete (`is_active` + `deleted_at`)
- `products` — catálogo de productos con soft delete

**Núcleo transaccional** — el eje del sistema:
- `orders` — pedidos (FK → customers)
- `order_items` — tabla intermedia N:M entre pedidos y productos (FK → orders, products)

**Auditoría e historial** — todo depende de un pedido:
- `payments` — pagos asociados a un pedido (FK → orders)
- `order_status_history` — historial completo de estados (FK → orders)
- `order_audit` — registro de cambios de campos específicos (FK → orders)

### Diagrama de relaciones

```
customers ──(1:N)──> orders ──(1:N)──> order_items <──(1:N)── products
                        │
                        ├──(1:N)──> payments
                        ├──(1:N)──> order_status_history
                        └──(1:N)──> order_audit
```

---

## 🔐 Integridad y restricciones

Cada tabla tiene constraints que reflejan las reglas reales del dominio:

| Constraint | Ejemplo aplicado |
|---|---|
| `PRIMARY KEY` | Todas las tablas |
| `FOREIGN KEY` | `orders.customer_id` → `customers.customer_id` |
| `NOT NULL` | `full_name`, `email`, `order_datetime`, etc. |
| `UNIQUE` | `customers.email`, `products.sku` |
| `CHECK` | `segment IN ('retail','wholesale','vip','online_only')` |
| `CHECK` | `is_active IN (0, 1)` |
| `CHECK` | `unit_price > 0`, `quantity > 0` |
| `CHECK` | `discount_rate >= 0 AND discount_rate <= 1` |
| `DEFAULT` | `is_active DEFAULT 1` |

Las FK están activadas explícitamente en cada conexión:
```sql
PRAGMA foreign_keys = ON
```

---

## 📖 Consultas estructurales

Las 12 consultas están organizadas en tres bloques en `consultas.py`:

**Bloque 1 — Navegación del modelo**
| # | Consulta |
|---|---|
| 1 | Pedidos con nombre de cliente y estado actual |
| 2 | Detalle de productos de un pedido |
| 3 | Historial completo de estados de un pedido |
| 4 | Pagos de un pedido con su estado |
| 5 | Auditoría de un pedido — quién cambió qué y cuándo |

**Bloque 2 — Rastreo de estados y eventos**
| # | Consulta |
|---|---|
| 6 | Pedidos entregados de clientes VIP |
| 7 | Pedidos con algún pago rechazado |
| 8 | Items con descuento mayor al 20% |

**Bloque 3 — Detección de ausencias e inconsistencias**
| # | Consulta |
|---|---|
| 9 | Pedidos sin ningún pago registrado |
| 10 | Pedidos `delivered` sin registro en historial |
| 11 | Clientes activos sin ningún pedido |
| 12 | Productos activos que nunca fueron vendidos |

Solo se usan `SELECT`, `JOIN`, `LEFT JOIN`, `WHERE` y `ORDER BY` — sin agregaciones.

---

## 🕵️ Inconsistencias detectadas

Las consultas del Bloque 3 revelaron inconsistencias reales en el dataset:

**Pedidos sin pago registrado** — la consulta 9 encontró pedidos con estado `paid` y `delivered` que no tienen ningún registro en `payments`. Un pedido no debería poder estar `paid` sin al menos un pago `approved`.

**Pedidos delivered sin historial** — la consulta 10 encontró pedidos cuyo `current_status` es `delivered` pero no tienen ningún registro `delivered` en `order_status_history`. El estado actual no coincide con la historia registrada.

**Ausencia de auditoría sobre productos** — el dataset incluye `order_audit` para pedidos pero no existe una tabla equivalente para cambios de precio o categoría en productos. Un sistema bien diseñado debería tener trazabilidad también sobre el catálogo.

---

## ⚡ Índices y performance

Se crearon índices en todas las FK y columnas de búsqueda frecuente:

```sql
CREATE INDEX idx_orders_customer_id       ON orders(customer_id);
CREATE INDEX idx_orders_current_status    ON orders(current_status);
CREATE INDEX idx_order_items_order_id     ON order_items(order_id);
CREATE INDEX idx_order_items_product_id   ON order_items(product_id);
CREATE INDEX idx_payments_order_id        ON payments(order_id);
CREATE INDEX idx_order_status_history_order_id ON order_status_history(order_id);
CREATE INDEX idx_order_audit_order_id     ON order_audit(order_id);
CREATE INDEX idx_customers_email          ON customers(email);
```

### Comparación de performance medida sobre el dataset real

| Consulta | Sin índice | Con índice | Mejora |
|---|---|---|---|
| `orders` por `customer_id` | 17.14 ms | 0.11 ms | 155x |
| `payments` por `order_id` | 16.66 ms | 0.03 ms | 555x |
| `order_items` por `order_id` | 32.87 ms | 0.04 ms | 820x |
| `order_status_history` por `order_id` | 26.26 ms | 0.03 ms | 875x |

`order_items` es la tabla con más filas (360 000) y la que más se beneficia del índice.

---

## 🔒 SQL Injection

### Cómo ocurre

SQL Injection ocurre cuando se construye una consulta concatenando strings con datos del usuario:

```python
# ❌ VULNERABLE
nombre = input("Nombre: ")
cursor.execute("SELECT * FROM customers WHERE full_name = '" + nombre + "'")
```

Si el usuario ingresa `' OR '1'='1`, la query devuelve todos los registros. Con variantes más agresivas puede borrar tablas o extraer datos sensibles.

### Qué la habilita

Una sola práctica: **concatenar strings para construir SQL**. No importa el lenguaje ni el motor.

### Cómo se previene

Con **consultas parametrizadas** — los valores van separados del SQL en todo momento:

```python
# ✅ SEGURO
nombre = input("Nombre: ")
cursor.execute("SELECT * FROM customers WHERE full_name = ?", (nombre,))
```

El `?` garantiza que el valor se trate siempre como dato, nunca como código SQL. Todo el pipeline de carga en `cargar_datos.py` usa esta práctica en cada `INSERT`.

---

## 🗄️ Justificación técnica — elección de SQLite

### 1. Ventajas en este contexto

SQLite es un motor embebido que no requiere instalar ni configurar un servidor separado. La base de datos completa vive en un único archivo `commerce.db` que puede copiarse, versionarse con Git y compartirse como cualquier otro archivo del proyecto.

La integración con Python es inmediata a través del módulo `sqlite3` de la librería estándar — sin dependencias externas. Esto permitió implementar todo el pipeline de carga (988 000 filas desde 7 CSV) en Python puro.

### 2. Manejo de integridad referencial

SQLite soporta claves foráneas pero las desactiva por defecto. Se activan explícitamente con `PRAGMA foreign_keys = ON` en cada conexión. Una vez activas, el motor rechaza cualquier inserción que viole una FK — verificado en `crear_tablas.py` con un intento de insertar un pedido con `customer_id` inexistente.

### 3. Soporte para constraints e índices

SQLite soporta todos los constraints requeridos: `PRIMARY KEY`, `FOREIGN KEY`, `NOT NULL`, `UNIQUE`, `CHECK` y `DEFAULT`. Los índices se crean con `CREATE INDEX` estándar y producen mejoras de hasta 875x en tiempo de consulta sobre el dataset real.

### 4. Comportamiento ante carga desde CSV

La carga usó `csv.DictReader` para mapear columnas directamente a parámetros del `INSERT`. El uso de generadores con `yield` garantizó que las 360 000 filas de `order_items` se procesaran sin cargar todo el dataset en memoria. La carga completa resultó en 0 violaciones de integridad.

### 5. Limitaciones relevantes

SQLite no es adecuado para producción con múltiples escrituras concurrentes — usa bloqueo a nivel de archivo. Para un sistema comercial real con usuarios simultáneos, PostgreSQL sería la elección correcta.

SQLite no soporta agregar constraints a tablas existentes con `ALTER TABLE` — requiere recrear la tabla. Los tipos de datos son dinámicos, por lo que la validación de tipos recae en los `CHECK` constraints y en el código Python de carga.

### Comparación resumida

| Criterio | SQLite | PostgreSQL |
|---|---|---|
| Instalación | Sin servidor, archivo único | Servidor separado requerido |
| FK activas por defecto | No — requiere `PRAGMA` | Sí |
| Constraints soportados | PK, FK, NOT NULL, UNIQUE, CHECK | Todos + tipos avanzados |
| Concurrencia | Escrituras serializadas | Múltiples escrituras simultáneas |
| Integración Python | `sqlite3` en librería estándar | Requiere `psycopg2` |
| Adecuado para este challenge | Sí | Sí, con mayor complejidad operativa |

**Conclusión:** SQLite fue la elección correcta para este challenge porque permite demostrar todas las habilidades requeridas sin overhead operativo. Sus limitaciones no afectan ninguno de los requisitos evaluados.

---

## ✅ Requisitos del challenge cumplidos

| Requisito | Estado | Dónde |
|---|---|---|
| Creación del modelo desde CSV | ✅ | `crear_tablas.py` |
| Inserción respetando integridad | ✅ | `cargar_datos.py` |
| Claves primarias reales | ✅ | Todas las tablas |
| Claves foráneas reales | ✅ | `orders`, `order_items`, `payments`, etc. |
| NOT NULL coherentes | ✅ | Todas las tablas |
| CHECK para valores inválidos | ✅ | `segment`, `status`, `method`, precios, etc. |
| UNIQUE cuando el dominio lo requiere | ✅ | `email`, `sku` |
| Índices en columnas críticas | ✅ | `indices.py` |
| Consultas SELECT + JOIN + WHERE + ORDER BY | ✅ | `consultas.py` — 12 consultas |
| Detección de inconsistencias estructurales | ✅ | Bloque 3 de `consultas.py` |
| Explicación de SQL Injection | ✅ | Sección de seguridad en este README |
| Justificación técnica del motor elegido | ✅ | Sección de justificación en este README |
| Comparación de performance con/sin índices | ✅ | `indices.py` + tabla en este README |

---

## 👨‍💻 Autor

Desarrollado como parte del programa de formación **Penguin Academy**.
