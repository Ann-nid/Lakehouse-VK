"""Шаг 3. Бенчмарк форматов и сжатия: размер, время записи, скорость запросов.
Запуск: python scripts/03_benchmark.py [--keep] [--quick]   (--keep = не удалять тестовые таблицы, --quick = быстрее)"""
import csv, os, statistics, sys
from common import run, table_size, RESULTS

COMBOS = [("PARQUET", "NONE"), ("PARQUET", "SNAPPY"), ("PARQUET", "GZIP"),
          ("PARQUET", "ZSTD"), ("ORC", "SNAPPY"), ("ORC", "ZSTD")]
TABLES = ["customer", "orders", "lineitem"]
REPEATS = 3
if "--quick" in sys.argv:        # быстрый режим: только Parquet, 2 замера
    COMBOS = [c for c in COMBOS if c[0] == "PARQUET"]
    REPEATS = 2

Q18 = """SELECT c.name, c.custkey, o.orderkey, o.orderdate, o.totalprice, sum(l.quantity)
FROM lakehouse.{s}.customer c JOIN lakehouse.{s}.orders o ON c.custkey = o.custkey
JOIN lakehouse.{s}.lineitem l ON o.orderkey = l.orderkey
WHERE o.orderkey IN (SELECT orderkey FROM lakehouse.{s}.lineitem GROUP BY orderkey HAVING sum(quantity) > 300)
GROUP BY c.name, c.custkey, o.orderkey, o.orderdate, o.totalprice
ORDER BY o.totalprice DESC, o.orderdate LIMIT 100"""

AGG = """SELECT returnflag, linestatus, count(*), sum(quantity), sum(extendedprice * (1 - discount)), avg(discount)
FROM lakehouse.{s}.lineitem GROUP BY returnflag, linestatus"""


def drop(schema):
    for t in TABLES:
        run(f"DROP TABLE IF EXISTS lakehouse.{schema}.{t}")
    run(f"DROP SCHEMA IF EXISTS lakehouse.{schema}")


def timed(sql):
    run(sql)  # прогрев (не учитывается)
    return statistics.median(run(sql)[1] for _ in range(REPEATS))


keep = "--keep" in sys.argv
results = []
for fmt, codec in COMBOS:
    schema = f"bench_{fmt.lower()}_{codec.lower()}"
    print(f"\n=== {fmt} + {codec} ===")
    drop(schema)
    run(f"CREATE SCHEMA lakehouse.{schema}")
    write_ms = 0
    for t in TABLES:
        _, ms = run(f"CREATE TABLE lakehouse.{schema}.{t} WITH (format = '{fmt}') AS SELECT * FROM tpch.sf1.{t}",
                    session={"lakehouse.compression_codec": codec})
        write_ms += ms
    size = sum(table_size(schema, t)[0] for t in TABLES)
    q18 = timed(Q18.format(s=schema))
    agg = timed(AGG.format(s=schema))
    print(f"запись {write_ms/1000:.1f} c | размер {size:.1f} МБ | Q18 {q18/1000:.2f} c | агрегация {agg/1000:.2f} c")
    results.append((fmt, codec, round(size, 1), round(write_ms / 1000, 1), round(q18 / 1000, 2), round(agg / 1000, 2)))
    if not keep:
        drop(schema)

head = ["Формат", "Сжатие", "Размер Bronze, МБ", "Время записи, c", "Q18 (медиана), c", "Агрегация lineitem, c"]
with open(os.path.join(RESULTS, "benchmark.csv"), "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(head); w.writerows(results)
md = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
md += ["| " + " | ".join(map(str, r)) + " |" for r in results]
open(os.path.join(RESULTS, "benchmark.md"), "w", encoding="utf-8").write("\n".join(md) + "\n")
print("\n" + "\n".join(md))
