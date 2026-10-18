"""Шаг 1. Один раз инициализирует Lakekeeper и создаёт warehouse 'lakehouse' (связывает с MinIO)."""
import datetime, hashlib, hmac, json, time, urllib.request, urllib.error

LK = "http://localhost:8181"


def call(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(LK + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()
    except Exception as e:
        return 0, str(e)


def make_bucket(name, endpoint="http://localhost:9000", ak="minioadmin", sk="minioadmin", region="us-east-1"):
    """Создаёт бакет в MinIO (S3 API, подпись SigV4) - вместо отдельного контейнера mc."""
    host = endpoint.split("//")[1]
    now = datetime.datetime.now(datetime.timezone.utc)
    amz, day = now.strftime("%Y%m%dT%H%M%SZ"), now.strftime("%Y%m%d")
    ph = hashlib.sha256(b"").hexdigest()
    signed = "host;x-amz-content-sha256;x-amz-date"
    canon = (f"PUT\n/{name}\n\nhost:{host}\nx-amz-content-sha256:{ph}\nx-amz-date:{amz}\n\n{signed}\n{ph}")
    scope = f"{day}/{region}/s3/aws4_request"
    sts = f"AWS4-HMAC-SHA256\n{amz}\n{scope}\n{hashlib.sha256(canon.encode()).hexdigest()}"
    h = lambda k, m: hmac.new(k, m.encode(), hashlib.sha256).digest()
    key = h(h(h(h(("AWS4" + sk).encode(), day), region), "s3"), "aws4_request")
    sig = hmac.new(key, sts.encode(), hashlib.sha256).hexdigest()
    headers = {"x-amz-date": amz, "x-amz-content-sha256": ph,
               "Authorization": f"AWS4-HMAC-SHA256 Credential={ak}/{scope}, SignedHeaders={signed}, Signature={sig}"}
    req = urllib.request.Request(f"{endpoint}/{name}", method="PUT", headers=headers)
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code          # 409 = бакет уже существует
    except Exception as e:
        return str(e)


print("Создаю бакет lakehouse в MinIO...")
for _ in range(30):
    code = make_bucket("lakehouse")
    if code in (200, 409):
        break
    time.sleep(2)
print("бакет:", code, "(200 - создан, 409 - уже был)")
if code not in (200, 409):
    raise SystemExit("Не удалось создать бакет. Проверь: docker logs lakehouse-minio")

print("Жду, пока Lakekeeper запустится...")
for _ in range(60):
    if call("GET", "/health")[0] == 200:
        break
    time.sleep(2)
else:
    raise SystemExit("Lakekeeper не отвечает. Смотри: docker logs lakekeeper")

print("bootstrap:", call("POST", "/management/v1/bootstrap", {"accept-terms-of-use": True})[0],
      "(200/204 - ок, 4xx - уже сделано раньше)")

for flavor in ("s3-compat", "minio"):
    body = {
        "warehouse-name": "lakehouse",
        "storage-profile": {
            "type": "s3", "bucket": "lakehouse", "key-prefix": "",
            "endpoint": "http://minio:9000", "region": "local-01",
            "path-style-access": True, "flavor": flavor, "sts-enabled": False,
        },
        "storage-credential": {
            "type": "s3", "credential-type": "access-key",
            "aws-access-key-id": "minioadmin", "aws-secret-access-key": "minioadmin",
        },
    }
    code, text = call("POST", "/management/v1/warehouse", body)
    print(f"warehouse (flavor={flavor}):", code, text[:200])
    if code in (200, 201, 409):
        break
print("Готово. Ждать ещё ~20 секунд, пока Trino поднимется, потом шаг 2.")
