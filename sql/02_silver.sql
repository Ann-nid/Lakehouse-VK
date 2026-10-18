-- SILVER: очищенные и обогащённые данные
CREATE SCHEMA IF NOT EXISTS lakehouse.silver;

-- Шаг 1: "крупные" заказы (суммарное количество товара > 300) - это подзапрос из Q18
CREATE TABLE lakehouse.silver.large_orders WITH (format = 'PARQUET') AS
SELECT orderkey, sum(quantity) AS total_quantity
FROM lakehouse.bronze.lineitem
GROUP BY orderkey
HAVING sum(quantity) > 300;

-- Шаг 2: джойн клиент <-> заказ <-> позиции только для крупных заказов
-- Чистка: trim имени, отсев пустых/некорректных значений. Обогащение: order_year.
CREATE TABLE lakehouse.silver.large_order_lines WITH (format = 'PARQUET') AS
SELECT
    c.custkey,
    trim(c.name)      AS customer_name,
    o.orderkey,
    o.orderdate,
    year(o.orderdate) AS order_year,
    o.totalprice,
    l.linenumber,
    l.quantity
FROM lakehouse.bronze.customer AS c
JOIN lakehouse.bronze.orders   AS o  ON c.custkey = o.custkey
JOIN lakehouse.bronze.lineitem AS l  ON l.orderkey = o.orderkey
JOIN lakehouse.silver.large_orders AS lo ON lo.orderkey = o.orderkey
WHERE c.name IS NOT NULL
  AND o.totalprice > 0
  AND l.quantity > 0
