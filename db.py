import sqlite3

DB_NAME = "servicio_tv.db"


def get_conn():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON") # Activa la restricción de llaves foráneas
    return conn


def crear_tablas():
    conn = get_conn()
    cur = conn.cursor()

    # =========================
    # TABLA CLIENTES
    # =========================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            direccion TEXT,
            fecha_alta TEXT DEFAULT (date('now')),
            fecha_vencimiento TEXT NOT NULL,
            importe REAL NOT NULL,
            dispositivos INTEGER DEFAULT 1,  -- <--- Agregamos este campo
            obs TEXT,
            activo INTEGER DEFAULT 1
        )
    """)

    # En db.py, dentro de crear_tablas, la tabla usuarios debería quedar así:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            sistema TEXT NOT NULL,
            usuario TEXT NOT NULL,
            fecha_vencimiento TEXT NOT NULL,
            dispositivo_id TEXT,  -- <--- NUEVA COLUMNA
            activo INTEGER DEFAULT 1,
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)

    # =========================
    # TABLA Compra Creditos
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS creditos_compras (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT NOT NULL,
            sistema TEXT NOT NULL,
            cantidad_creditos INTEGER NOT NULL,
            costo_total REAL DEFAULT 0,
            tipo_movimiento TEXT NOT NULL,
            observaciones TEXT
        )
    """)

    # =========================
    # TABLAS VENDEDORES
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS vendedores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            observaciones TEXT,
            activo INTEGER DEFAULT 1
        )
    """)

    # =========================
    # TABLAS NUEVAS
    # =========================

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cobros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            fecha TEXT NOT NULL,
            importe REAL NOT NULL,
            observaciones TEXT,

            FOREIGN KEY(cliente_id)
            REFERENCES clientes(id)
        )
        """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS renovaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            fecha_renovacion TEXT NOT NULL,
            fecha_vencimiento_anterior TEXT,
            fecha_vencimiento_nueva TEXT,
            sistema TEXT,
            creditos_consumidos INTEGER DEFAULT 1,
            observaciones TEXT,

            FOREIGN KEY(usuario_id)
            REFERENCES usuarios(id)
        )
        """)

    # =========================
    # TABLA PAGOS
    # =========================
    cur.execute("""
        CREATE TABLE IF NOT EXISTS pagos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER NOT NULL,
            fecha_pago TEXT DEFAULT (date('now')),
            mes_correspondiente TEXT NOT NULL, -- Ejemplo: "Marzo 2026"
            importe_pagado REAL NOT NULL,
            metodo_pago TEXT, -- Efectivo, Transferencia, etc.
            FOREIGN KEY (cliente_id) REFERENCES clientes(id)
        )
    """)


    conn.commit()
    conn.close()