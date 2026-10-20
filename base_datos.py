"""Acceso a la base de datos SQLite."""
import sqlite3
from contextlib import contextmanager

import config

ESQUEMA = """
CREATE TABLE IF NOT EXISTS solicitudes (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo             TEXT UNIQUE,
    origen             TEXT UNIQUE,            -- identifica la fila importada de Google Sheets
    fecha_creacion     TEXT NOT NULL,
    solicitante        TEXT NOT NULL,
    correo             TEXT,
    tipo_solicitante   TEXT,
    tipo_solicitud     TEXT NOT NULL,
    descripcion        TEXT,
    estado             TEXT NOT NULL DEFAULT 'Recibida',
    fecha_estado       TEXT NOT NULL,          -- desde cuándo está en el estado actual
    responsable        TEXT,
    correo_responsable TEXT,
    fecha_limite       TEXT,
    en_espera          INTEGER NOT NULL DEFAULT 0,
    motivo_espera      TEXT,
    fecha_espera       TEXT,
    respuesta          TEXT,
    fecha_cierre       TEXT
);

CREATE TABLE IF NOT EXISTS historial (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    solicitud_id   INTEGER NOT NULL REFERENCES solicitudes(id),
    fecha          TEXT NOT NULL,
    usuario        TEXT NOT NULL,
    campo          TEXT NOT NULL,
    valor_anterior TEXT,
    valor_nuevo    TEXT,
    comentario     TEXT
);

CREATE INDEX IF NOT EXISTS idx_solicitudes_estado ON solicitudes(estado);
CREATE INDEX IF NOT EXISTS idx_historial_solicitud ON historial(solicitud_id);
"""


@contextmanager
def conexion():
    """Abre una conexión; confirma los cambios al salir o los revierte si hay error."""
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    try:
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()


def inicializar():
    """Crea las tablas si no existen."""
    with conexion() as con:
        con.executescript(ESQUEMA)
