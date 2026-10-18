"""Шаг 4 (часть 2). Демонстрация schema evolution и time travel на Silver. Лог -> results/part2_log.txt"""
import os
from common import run, RESULTS

T = "lakehouse.silver.large_order_lines"
log = open(os.path.join(RESULTS, "part2_log.txt"), "w", encoding="utf-8")


def say(*a):
    s = " ".join(str(x) for x in a); print(s); log.write(s + "\n")


def q(sql):
    rows, _ = run(sql); say(">>", sql); [say("  ", r) for r in rows[:8]]; return rows


say("### SCHEMA EVOLUTION")
q(f"SELECT count(*) FROM {T}")
q(f"ALTER TABLE {T} ADD COLUMN note varchar")
q(f"SELECT orderkey, quantity, note FROM {T} LIMIT 3")        # у старых строк note = NULL, файлы не переписаны
q(f"ALTER TABLE {T} RENAME COLUMN note TO remark")
q(f"SELECT orderkey, quantity, remark FROM {T} LIMIT 3")      # данные доступны под новым именем

say("\n### TIME TRAVEL (откат после 'случайного' удаления)")
q(f'SELECT snapshot_id, committed_at, operation FROM lakehouse.silver."large_order_lines$snapshots" ORDER BY committed_at')
snap = run(f'SELECT snapshot_id FROM lakehouse.silver."large_order_lines$snapshots" ORDER BY committed_at DESC LIMIT 1')[0][0][0]
before = q(f"SELECT count(*) FROM {T}")[0][0]
say("Запомнили снапшот:", snap, "строк:", before)
q(f"DELETE FROM {T} WHERE order_year = 1992")                 # 'авария'
after = q(f"SELECT count(*) FROM {T}")[0][0]
say("После удаления строк:", after)
q(f"SELECT count(*) FROM {T} FOR VERSION AS OF {snap}")      # смотрим прошлое, не откатывая
q(f"CALL lakehouse.system.rollback_to_snapshot('silver', 'large_order_lines', {snap})")  # восстановление
restored = q(f"SELECT count(*) FROM {T}")[0][0]
say("После отката строк:", restored, "- совпало с исходным:", restored == before)
log.close()
