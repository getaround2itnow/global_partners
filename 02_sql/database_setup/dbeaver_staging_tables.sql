CREATE TABLE dbo.date_dim_staging (
    date_key VARCHAR(10),
    year VARCHAR(4),
    month VARCHAR(2),
    week VARCHAR(2),
    day_of_week VARCHAR(10),
    is_weekend VARCHAR(5),
    is_holiday VARCHAR(5),
    holiday_name VARCHAR(50)
);

CREATE TABLE dbo.order_items_staging (
	APP_NAME VARCHAR(50),
	RESTAURANT_ID VARCHAR(50),
	CREATION_TIME_UTC VARCHAR(50),
	ORDER_ID VARCHAR(50),
	USER_ID VARCHAR(50),
	PRINTED_CARD_NUMBER VARCHAR(50),
	IS_LOYALTY VARCHAR(5),
	CURRENCY VARCHAR(5),
	LINEITEM_ID VARCHAR(75),
	ITEM_CATEGORY VARCHAR(50),
	ITEM_NAME VARCHAR(50),
	ITEM_PRICE DECIMAL(10, 2),
	ITEM_QUANTITY INT
	)
	
CREATE TABLE dbo.order_items_options_staging (
	ORDER_ID VARCHAR(255),
	LINEITEM_ID VARCHAR(255),
	OPTION_GROUP_NAME VARCHAR(255),
	OPTION_NAME VARCHAR(255),
	OPTION_PRICE DECIMAL(10, 2),
	OPTION_QUANTITY INT
	)
	
ALTER TABLE dbo.order_items_staging
ALTER COLUMN ITEM_CATEGORY VARCHAR(255);

SELECT TOP 20
	LEN(ITEM_CATEGORY) AS category_length,
	ITEM_CATEGORY
FROM dbo.order_items_staging
ORDER BY
	LEN(ITEM_CATEGORY) DESC;

SELECT
	COUNT(*) AS rows_with_urls
FROM
	dbo.order_items_staging
WHERE 
	ITEM_CATEGORY
LIKE
	'%http%';

SELECT COUNT(*) AS row_count
FROM dbo.order_items_staging;

SELECT
    MAX(LEN(ITEM_CATEGORY)) AS max_item_category_length,
    MAX(LEN(ITEM_NAME)) AS max_item_name_length
FROM dbo.order_items_staging;

TRUNCATE TABLE
	dbo.order_items_staging

SELECT
	*
FROM
	dbo.order_items_options;

SELECT
	COUNT(*) AS row_count
FROM
	dbo.order_items_options_staging;

SELECT 	
	MAX(LEN(ORDER_ID)) AS max_order_id_length,
	MAX(LEN(LINEITEM_ID)) AS max_lineitem_id_length,
	MAX(LEN(OPTION_GROUP_NAME)) AS max_option_group_name_length,
	MAX(LEN(OPTION_NAME)) AS max_option_name_length
FROM
	dbo.order_items_options_staging;

SELECT
	MIN(OPTION_PRICE) AS min_option_price,
	MAX(OPTION_PRICE) AS max_option_price,
	MIN(OPTION_QUANTITY) AS min_option_quantity,
	MAX(OPTION_QUANTITY) AS max_option_quantity
FROM
	dbo.order_items_options_staging;	

SELECT
	COUNT(*) as row_count
FROM
	dbo.order_items_staging;

SELECT TOP 10
	CREATION_TIME_UTC
FROM
	dbo.order_items_staging;

SELECT
    IS_LOYALTY,
    COUNT(*) AS row_count
FROM dbo.order_items_staging
GROUP BY IS_LOYALTY;
	
CREATE TABLE dbo.order_items_options_staging (
	ORDER_ID VARCHAR(50),
	LINEITEM_ID VARCHAR(50),
	OPTION_GROUP_NAME VARCHAR(75),
	OPTION_NAME VARCHAR(50),
	OPTION_PRICE DECIMAL(10, 2),
	OPTION_QUANTITY INT
	)
SELECT
	*
FROM
	order_items_staging;

DROP TABLE 
	dbo.order_items_options_staging;

SELECT
	*
FROM 	
	dbo.order_items;

SELECT TOP 10
	CREATION_TIME_UTC,
	CONVERT(DATETIME2, CREATION_TIME_UTC, 127) AS converted_creation_time,
	IS_LOYALTY,
	CASE
		WHEN IS_LOYALTY = 'TRUE' THEN 1
		WHEN IS_LOYALTY = 'FALSE' THEN 0
		ELSE NULL
	END as converted_is_loyalty
FROM
	dbo.order_items_staging;

SELECT COUNT(*) AS row_count
FROM dbo.order_items_options;

SELECT
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_SCHEMA = 'dbo'
  AND TABLE_NAME = 'order_items_options'
ORDER BY ORDINAL_POSITION;

ALTER TABLE dbo.order_items_options
ALTER COLUMN OPTION_GROUP_NAME VARCHAR(255);

ALTER TABLE dbo.order_items_options
ALTER COLUMN OPTION_NAME VARCHAR(255);
	

INSERT INTO dbo.date_dim (
    date_key,
    year,
    month,
    week,
    day_of_week,
    is_weekend,
    is_holiday,
    holiday_name
)
SELECT
    CONVERT(DATE, date_key, 105),
    CAST(year AS INT),
    CAST(month AS INT),
    CAST(week AS INT),
    CAST(day_of_week AS VARCHAR(20)),
    CASE
        WHEN is_weekend = 'TRUE' THEN 1
        WHEN is_weekend = 'FALSE' THEN 0
    END,
    CASE
        WHEN is_holiday = 'TRUE' THEN 1
        WHEN is_holiday = 'FALSE' THEN 0
    END,
    holiday_name
FROM dbo.date_dim_staging;

INSERT INTO order_items (
	APP_NAME,
	RESTAURANT_ID,
	CREATION_TIME_UTC,
	ORDER_ID,
	USER_ID,
	PRINTED_CARD_NUMBER,
	IS_LOYALTY,
	CURRENCY,
	LINEITEM_ID,
	ITEM_CATEGORY,
	ITEM_NAME,
	ITEM_PRICE,
	ITEM_QUANTITY
) 
SELECT
	CAST(APP_NAME AS VARCHAR(255)),
	CAST(RESTAURANT_ID AS VARCHAR(255)),
	CONVERT(DATETIME2, CREATION_TIME_UTC, 127),
	CAST(ORDER_ID AS VARCHAR(255)),
	CAST(USER_ID AS VARCHAR(255)),
	CAST(PRINTED_CARD_NUMBER AS VARCHAR(255)),
	CASE
		WHEN IS_LOYALTY = 'TRUE' THEN 1
		WHEN IS_LOYALTY = 'FALSE' THEN 0
		ELSE NULL
	END,
	CAST(CURRENCY AS VARCHAR(10)),
	CAST(LINEITEM_ID AS VARCHAR(255)),
	CAST(ITEM_CATEGORY AS VARCHAR(255)),
	CAST(ITEM_NAME AS VARCHAR(255)),
	ITEM_PRICE,
	ITEM_QUANTITY
FROM
	dbo.order_items_staging;

INSERT INTO dbo.order_items_options (
    ORDER_ID,
    LINEITEM_ID,
    OPTION_GROUP_NAME,
    OPTION_NAME,
    OPTION_PRICE,
    OPTION_QUANTITY
)
SELECT
    ORDER_ID,
    LINEITEM_ID,
    OPTION_GROUP_NAME,
    OPTION_NAME,
    OPTION_PRICE,
    OPTION_QUANTITY
FROM dbo.order_items_options_staging;

