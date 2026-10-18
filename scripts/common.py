"""Общие функции: отправка SQL в Trino через его HTTP API (только стандартная библиотека Python)."""
import json, os, time, urllib.request

TRINO = os.environ.get("TRINO_URL", "http://localhost:8080")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
os.makedirs(RESULTS, exist_ok=True)


def run(sql, catalog="lakehouse", session=None, user="admin"):
    """Выполняет один SQL. Возвращает (строки, время_выполнения_мс по данным самого Trino)."""
    headers = {"X-Trino-User": user, "X-Trino-Catalog": catalog}
    if session:
        headers["X-Trino-Session"] = ",".join(f"{k}={v}" for k, v in session.items())
    req = urllib.request.Request(TRINO + "/v1/statement", data=sql.encode("utf-8"),
                                 headers=headers, method="POST")
    with urllib.request.urlopen(req) as r:
        res = json.load(r)
    rows, elapsed = [], 0
    while True:
        if "error" in res:
            raise RuntimeError(res["error"]["message"] + "\nSQL: " + sql[:300])
        rows += res.get("data", [])
        elapsed = res.get("stats", {}).get("elapsedTimeMillis", elapsed)
        nxt = res.get("nextUri")
        if not nxt:
            break
        time.sleep(0.05)
        with urllib.request.urlopen(nxt) as r:
            res = json.load(r)
    return rows, elapsed


def run_file(path, **kw):
    """Выполняет файл с несколькими SQL, разделёнными ';'. Комментарии '--' вырезаются."""
    text = "\n".join(l for l in open(path, encoding="utf-8").read().splitlines()
                     if not l.strip().startswith("--"))
    total = 0
    for stmt in [s.strip() for s in text.split(";") if s.strip()]:
        _, ms = run(stmt, **kw)
        print(f"  ok ({ms/1000:.1f} c): {stmt.splitlines()[0][:90]}")
        total += ms
    return total


def table_size(schema, table):
    """Размер таблицы в МБ и число файлов - из служебной таблицы Iceberg "$files"."""
    rows, _ = run(f'SELECT coalesce(sum(file_size_in_bytes),0), count(*) '
                  f'FROM lakehouse.{schema}."{table}$files"')
    return rows[0][0] / 1024 / 1024, rows[0][1]
