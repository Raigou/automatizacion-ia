CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    texto TEXT NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    urgente BOOLEAN NOT NULL DEFAULT FALSE,
    resumen TEXT,
    solucion_sugerida TEXT,
    creado_en TIMESTAMP DEFAULT NOW()
);