-- GOLD: витрина = ответ на Q18 (топ-100 клиентов по сумме заказа)
CREATE SCHEMA IF NOT EXISTS lakehouse.gold;
CREATE TABLE lakehouse.gold.top_large_volume_customers WITH (format = 'PARQUET') AS
SELECT
    customer_name AS name,
    custkey,
    orderkey,
    orderdate,
    totalprice,
    sum(quantity) AS total_quantity
FROM lakehouse.silver.large_order_lines
GROUP BY customer_name, custkey, orderkey, orderdate, totalprice
ORDER BY totalprice DESC, orderdate
LIMIT 100
