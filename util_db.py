from db import get_conn     # o desde donde tengas get_conn()

def stock_creditos(sistema):

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(creditos),0)
        FROM movimientos_creditos
        WHERE sistema=?
    """,(sistema,))

    stock = cur.fetchone()[0]

    conn.close()

    return stock


def stock_todos():

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT sistema,
               COALESCE(SUM(creditos),0)
        FROM movimientos_creditos
        GROUP BY sistema
    """)

    datos = dict(cur.fetchall())

    conn.close()

    return datos