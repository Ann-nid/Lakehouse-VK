"""Шаг 5. Подставляет реальные результаты (stats, бенчмарк, лог части 2, docker ps) в README.md.
Исходный шаблон хранится в README.template.md, поэтому скрипт можно запускать повторно."""
import csv, os, re, shutil, subprocess
from common import ROOT, RESULTS

tpl = os.path.join(ROOT, "README.template.md")
out = os.path.join(ROOT, "README.md")
if not os.path.exists(tpl):
    shutil.copy(out, tpl)
text = open(tpl, encoding="utf-8").read()


def read(name):
    p = os.path.join(RESULTS, name)
    return open(p, encoding="utf-8").read().strip() if os.path.exists(p) else None


# 1. stats.md -> {{R:слой.таблица}} и {{MB:слой.таблица}}
stats = read("stats.md")
if stats:
    for line in stats.splitlines():
        c = [x.strip() for x in line.strip("|").split("|")]
        if len(c) == 5 and c[2].isdigit():
            key = f"{c[0]}.{c[1]}"
            text = text.replace("{{R:%s}}" % key, f"{int(c[2]):,}".replace(",", " "))
            text = text.replace("{{MB:%s}}" % key, c[4])
else:
    print("! нет results/stats.md (запусти шаг 3)")

# 2. бенчмарк -> таблица и автоматический вывод из цифр
bench = read("benchmark.md")
if bench:
    text = text.replace("{{BENCH}}", bench)
    rows = list(csv.DictReader(open(os.path.join(RESULTS, "benchmark.csv"), encoding="utf-8")))
    H = list(rows[0].keys())
    name = lambda r: f"{r[H[0]]}+{r[H[1]]}"
    val = lambda r, i: float(r[H[i]])
    best = lambda i: min(rows, key=lambda r: val(r, i))
    worst_size = max(rows, key=lambda r: val(r, 2))
    parts = [f"наименьший размер Bronze — {name(best(2))} ({val(best(2),2)} МБ), наибольший — {name(worst_size)} ({val(worst_size,2)} МБ)",
             f"самая быстрая запись — {name(best(3))} ({val(best(3),3)} с)",
             f"самый быстрый Q18 — {name(best(4))} ({val(best(4),4)} с)",
             f"самая быстрая агрегация — {name(best(5))} ({val(best(5),5)} с)"]
    d = {name(r): r for r in rows}
    if "PARQUET+NONE" in d and "PARQUET+ZSTD" in d:
        n, z = d["PARQUET+NONE"], d["PARQUET+ZSTD"]
        parts.append(f"ZSTD уменьшает размер в {val(n,2)/val(z,2):.1f} раза относительно несжатого Parquet, "
                     f"при этом запись медленнее в {val(z,3)/val(n,3):.2f} раза, а Q18 — в {val(z,4)/val(n,4):.2f} раза")
    if "PARQUET+GZIP" in d and "PARQUET+ZSTD" in d:
        g, z = d["PARQUET+GZIP"], d["PARQUET+ZSTD"]
        parts.append(f"GZIP относительно ZSTD: размер ×{val(g,2)/val(z,2):.2f}, запись ×{val(g,3)/val(z,3):.2f}")
    text = text.replace("{{BENCH_AUTO}}", "; ".join(parts) + ".")
else:
    print("! нет results/benchmark.md (запусти шаг 4)")

# 3. лог части 2
log = read("part2_log.txt")
if log:
    text = text.replace("{{PART2_LOG}}", log)
else:
    print("! нет results/part2_log.txt (запусти шаг 5)")

# 4. docker ps
try:
    ps = subprocess.run(["docker", "ps", "--format", "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"],
                        capture_output=True, text=True, timeout=30).stdout.strip()
    text = text.replace("{{DOCKER_PS}}", ps)
except Exception as e:
    print("! docker ps не удался:", e)

open(out, "w", encoding="utf-8").write(text)
left = sorted(set(re.findall(r"\{\{[^}]+\}\}", text)))
print("Готово: README.md обновлён.", "Незаполненные поля: " + ", ".join(left) if left else "Все поля заполнены.")
