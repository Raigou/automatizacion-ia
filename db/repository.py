import psycopg2

from app.config import get_settings


def _conectar():
    s = get_settings()
    return psycopg2.connect(
        host=s.db_host,
        port=s.db_port,
        dbname=s.db_name,
        user=s.db_user,
        password=s.db_password,
    )


def guardar_ticket(
    texto: str,
    categoria: str,
    urgente: bool,
    resumen: str,
    solucion_sugerida: str | None,
) -> int:
    """Inserta un ticket y devuelve su id."""
    with _conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO tickets (texto, categoria, urgente, resumen, solucion_sugerida)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (texto, categoria, urgente, resumen, solucion_sugerida),
            )
            return cur.fetchone()[0]


def buscar_tickets_similares(texto: str, limite: int = 3) -> list[dict]:
    """Busca tickets previos cuyo texto contenga la consulta."""
    with _conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, categoria, urgente, resumen
                FROM tickets
                WHERE texto ILIKE %s
                ORDER BY creado_en DESC
                LIMIT %s
                """,
                (f"%{texto}%", limite),
            )
            columnas = ["id", "categoria", "urgente", "resumen"]
            return [dict(zip(columnas, fila)) for fila in cur.fetchall()]