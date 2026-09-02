-- This SQL file is for the creation of 
-- landing tables from csv to the DBeaver app

SELECT
	name,
	database_id,
	state_desc
FROM
	sys.databases
ORDER BY
	name;

SELECT
	db_id('global_partners')
AS
	database_id;
USE global_partners

CREATE TABLE dbo.order_items (
    APP_NAME VARCHAR(255),
    RESTAURANT_ID VARCHAR(255),
    CREATION_TIME_UTC DATETIME2,
    ORDER_ID VARCHAR(255),
    USER_ID VARCHAR(255),
    PRINTED_CARD_NUMBER VARCHAR(255),
    IS_LOYALTY BIT,
    CURRENCY VARCHAR(10),
    LINEITEM_ID VARCHAR(255),
    ITEM_CATEGORY VARCHAR(255),
    ITEM_NAME VARCHAR(255),
    ITEM_PRICE DECIMAL(10,2),
    ITEM_QUANTITY INT
);

USE global_partners;

CREATE TABLE dbo.order_items_options (
    ORDER_ID VARCHAR(255),
    LINEITEM_ID VARCHAR(255),
    OPTION_GROUP_NAME VARCHAR(25),
    OPTION_NAME VARCHAR(25),
    OPTION_PRICE DECIMAL(10, 2),
    OPTION_QUANTITY INT
)

CREATE TABLE dbo.date_dim (
    date_key DATE ,
    year INT,
    month INT,
    week INT,
    day_of_week VARCHAR(10),
    is_weekend BIT,
    is_holiday BIT,
    holiday_name VARCHAR (50)
);