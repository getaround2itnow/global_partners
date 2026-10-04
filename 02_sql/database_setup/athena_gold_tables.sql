-- ============================================================
-- Athena Gold Layer External Tables
-- Database: global_partners
-- Region: us-east-2
-- ============================================================


-- ============================================================
-- 1. sales_hourly
-- ============================================================

CREATE EXTERNAL TABLE IF NOT EXISTS `global_partners`.`sales_hourly` (
  `app_name` string,
  `restaurant_id` string,
  `order_date` date,
  `order_hour_utc` int,
  `time_of_day_utc` string,
  `is_weekend` boolean,
  `order_count` bigint,
  `line_item_count` bigint,
  `item_quantity` bigint,
  `item_revenue` decimal(38, 2),
  `option_revenue` decimal(38, 2),
  `total_revenue` decimal(38, 2),
  `average_order_value` decimal(38, 2)
)
COMMENT "Hourly sales metrics by app, restaurant, date, and UTC hour."
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION 's3://global-partners-project-curated/gold/sales_hourly/'
TBLPROPERTIES ('classification' = 'parquet');


-- ============================================================
-- 2. restaurant_daily
-- ============================================================

CREATE EXTERNAL TABLE IF NOT EXISTS `global_partners`.`restaurant_daily` (
  `app_name` string,
  `restaurant_id` string,
  `order_date` date,
  `day_of_week` string,
  `is_weekend` boolean,
  `is_holiday` boolean,
  `holiday_name` string,
  `order_count` bigint,
  `customer_count` bigint,
  `line_item_count` bigint,
  `item_revenue` decimal(38, 2),
  `option_revenue` decimal(38, 2),
  `total_revenue` decimal(38, 2),
  `average_order_value` decimal(38, 2)
)
COMMENT "Daily restaurant sales and customer metrics by app, restaurant, and date."
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION 's3://global-partners-project-curated/gold/restaurant_daily/'
TBLPROPERTIES ('classification' = 'parquet');


-- ============================================================
-- 3. item_daily
-- ============================================================

CREATE EXTERNAL TABLE IF NOT EXISTS `global_partners`.`item_daily` (
  `app_name` string,
  `restaurant_id` string,
  `order_date` date,
  `item_category` string,
  `item_name` string,
  `quantity_sold` bigint,
  `order_count` bigint,
  `item_revenue` decimal(38, 2),
  `average_item_price` decimal(38, 2)
)
COMMENT "Daily item sales metrics by app, restaurant, date, category, and item."
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION 's3://global-partners-project-curated/gold/item_daily/'
TBLPROPERTIES ('classification' = 'parquet');


-- ============================================================
-- 4. option_daily
-- ============================================================

CREATE EXTERNAL TABLE IF NOT EXISTS `global_partners`.`option_daily` (
  `app_name` string,
  `restaurant_id` string,
  `order_date` date,
  `option_group_name` string,
  `option_name` string,
  `option_quantity` bigint,
  `option_revenue` decimal(38, 2),
  `order_count` bigint,
  `average_option_price` decimal(38, 2),
  `free_option_quantity` bigint,
  `paid_option_quantity` bigint,
  `free_option_order_count` bigint,
  `paid_option_order_count` bigint,
  `paid_option_revenue` decimal(38, 2)
)
COMMENT "Daily option usage and revenue metrics by app, restaurant, date, option group, and option."
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION 's3://global-partners-project-curated/gold/option_daily/'
TBLPROPERTIES ('classification' = 'parquet');


-- ============================================================
-- 5. customer_summary
-- ============================================================

CREATE EXTERNAL TABLE IF NOT EXISTS `global_partners`.`customer_summary` (
  `user_id` string,
  `order_count` bigint,
  `item_count` bigint,
  `total_item_revenue` decimal(38, 2),
  `total_option_revenue` decimal(38, 2),
  `total_revenue` decimal(38, 2),
  `average_order_value` decimal(38, 2),
  `first_order_date` date,
  `last_order_date` date,
  `loyalty_order_count` bigint,
  `loyalty_revenue` decimal(38, 2)
)
COMMENT "Historical customer-level sales, loyalty, and order summary metrics."
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION 's3://global-partners-project-curated/gold/customer_summary/'
TBLPROPERTIES ('classification' = 'parquet');


-- ============================================================
-- 6. order_detail
-- ============================================================

CREATE EXTERNAL TABLE IF NOT EXISTS `global_partners`.`order_detail` (
  `app_name` string,
  `restaurant_id` string,
  `order_date` date,
  `order_id` string,
  `lineitem_id` string,
  `user_id` string,
  `item_category` string,
  `item_name` string,
  `is_loyalty` boolean,
  `card_status` string,
  `time_of_day_utc` string,
  `item_price` decimal(38, 2),
  `item_quantity` bigint,
  `item_revenue` decimal(38, 2),
  `option_revenue` decimal(38, 2),
  `total_line_revenue` decimal(38, 2)
)
COMMENT "Curated order line-item detail for drill-down analysis."
ROW FORMAT SERDE 'org.apache.hadoop.hive.ql.io.parquet.serde.ParquetHiveSerDe'
STORED AS INPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.parquet.MapredParquetOutputFormat'
LOCATION 's3://global-partners-project-curated/gold/order_detail/'
TBLPROPERTIES ('classification' = 'parquet');
