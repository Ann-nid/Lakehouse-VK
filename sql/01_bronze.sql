-- BRONZE: сырые копии 3 таблиц TPC-H (sf1) как есть, без изменений
CREATE SCHEMA IF NOT EXISTS lakehouse.bronze;
CREATE TABLE lakehouse.bronze.customer WITH (format = 'PARQUET') AS SELECT * FROM tpch.sf1.customer;
CREATE TABLE lakehouse.bronze.orders   WITH (format = 'PARQUET') AS SELECT * FROM tpch.sf1.orders;
CREATE TABLE lakehouse.bronze.lineitem WITH (format = 'PARQUET') AS SELECT * FROM tpch.sf1.lineitem
