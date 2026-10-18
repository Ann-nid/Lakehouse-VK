"""Шаг 2. Строит Bronze -> Silver -> Gold, проверяет результат против эталона, собирает статистику."""
import os
from common import run, run_file, table_size, ROOT, RESULTS

SQL = os.path.join(ROOT, "sql")


def clean():
    for schema, tables in {"gold": ["top_large_volume_customers"],
                           "silver": ["large_order_lines", "large_orders"],
                           "bronze": ["lineitem", "orders", "customer"]}.items():
        for t in tables:
            run(f"DROP TABLE IF EXISTS lakehouse.{schema}.{t}")


def verify():
    gold_sql = ("SELECT name, custkey, orderkey, cast(orderdate AS varchar), totalprice, total_quantity "
                "FROM lakehouse.gold.top_large_volume_customers ORDER BY totalprice DESC, orderdate")
    orig_sql = open(os.path.join(SQL, "q18_original.sql"), encoding="utf-8").read()
    norm = lambda rows: [(r[0], r[1], r[2], str(r[3]), round(float(r[4]), 2), round(float(r[5]), 2)) for r in rows]
    g, _ = run(gold_sql)
    o, _ = run(orig_sql.replace("o.orderdate, o.totalprice, sum(l.quantity) AS total_quantity",
                                "cast(o.orderdate AS varchar), o.totalprice, sum(l.quantity) AS total_quantity", 1), catalog="tpch")
    same = norm(g) == norm(o)
    print(f"Проверка: Gold = {len(g)} строк, эталонный Q18 = {len(o)} строк, совпадают: {same}")
    return same


def stats():
    tables = [("bronze", "customer"), ("bronze", "orders"), ("bronze", "lineitem"),
              ("silver", "large_orders"), ("silver", "large_order_lines"),
              ("gold", "top_large_volume_customers")]
    lines = ["| Слой | Таблица | Строк | Файлов | Вес, МБ |", "|---|---|---|---|---|"]
    for s, t in tables:
        cnt, _ = run(f"SELECT count(*) FROM lakehouse.{s}.{t}")
        mb, files = table_size(s, t)
        lines.append(f"| {s} | {t} | {cnt[0][0]} | {files} | {mb:.3f} |")
    text = "\n".join(lines)
    open(os.path.join(RESULTS, "stats.md"), "w", encoding="utf-8").write(text + "\n")
    print(text)


if __name__ == "__main__":
    print("Чищу старое (если запускаешь повторно)..."); clean()
    for f in ("01_bronze.sql", "02_silver.sql", "03_gold.sql"):
        print(f"== {f}"); run_file(os.path.join(SQL, f))
    verify()
    print("\nСтатистика (скопируй в отчёт):"); stats()
