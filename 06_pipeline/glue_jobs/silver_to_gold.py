import sys

from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F
from pyspark.sql.window import Window


# ============================================================
# 1. Initialize AWS Glue / Spark
# ============================================================

args = getResolvedOptions(sys.argv, ["JOB_NAME"])

sc = SparkContext()
glueContext = GlueContext(sc)
spark = glueContext.spark_session

job = Job(glueContext)
job.init(args["JOB_NAME"], args)


# ============================================================
# 2. Use UTC explicitly
# ============================================================

spark.conf.set("spark.sql.session.timeZone", "UTC")


# ============================================================
# 3. S3 locations
# ============================================================

SILVER_BASE = "s3://global-partners-project-refined/silver"
GOLD_BASE = "s3://global-partners-project-curated/gold"


# ============================================================
# 4. Read Silver datasets
# ============================================================

silver_order_items = spark.read.parquet(
    f"{SILVER_BASE}/order_items/"
)

silver_order_item_options = spark.read.parquet(
    f"{SILVER_BASE}/order_item_options/"
)

silver_date_dim = spark.read.parquet(
    f"{SILVER_BASE}/date_dim/"
)


# ============================================================
# 5. Basic source validation
# ============================================================

order_items_count = silver_order_items.count()
options_count = silver_order_item_options.count()
date_dim_count = silver_date_dim.count()

print(f"Silver order_items rows: {order_items_count}")
print(f"Silver order_item_options rows: {options_count}")
print(f"Silver date_dim rows: {date_dim_count}")

silver_order_items.printSchema()
silver_order_item_options.printSchema()
silver_date_dim.printSchema()


# ============================================================
# 6. Validate Silver order_items grain
# ============================================================

duplicate_order_lines = (
    silver_order_items
    .groupBy(
        "ORDER_ID",
        "LINEITEM_ID"
    )
    .count()
    .filter(F.col("count") > 1)
)

duplicate_order_line_count = duplicate_order_lines.count()

print(
    f"Duplicate Silver order lines: "
    f"{duplicate_order_line_count}"
)

if duplicate_order_line_count > 0:
    raise ValueError(
        "Silver order_items contains duplicate "
        "ORDER_ID + LINEITEM_ID combinations."
    )


# ============================================================
# 7. Prepare reusable order-level aggregates
# ============================================================

order_summary = (
    silver_order_items
    .groupBy("ORDER_ID")
    .agg(
        F.first("APP_NAME", ignorenulls=True).alias("APP_NAME"),
        F.first("RESTAURANT_ID", ignorenulls=True).alias("RESTAURANT_ID"),
        F.first("ORDER_DATE", ignorenulls=True).alias("ORDER_DATE"),
        F.sum("TOTAL_LINE_REVENUE").alias("ORDER_TOTAL"),
        F.sum("ITEM_QUANTITY").alias("ORDER_TOTAL_ITEMS")
    )
)


# ============================================================
# 8. Gold dataset: sales_hourly
#
# Grain:
# 1 row = 1 app + restaurant + date + hour
# ============================================================

sales_hourly = (
    silver_order_items
    .groupBy(
        "APP_NAME",
        "RESTAURANT_ID",
        "ORDER_DATE",
        "ORDER_HOUR_UTC",
        "TIME_OF_DAY_UTC",
        "IS_WEEKEND"
    )
    .agg(
        F.countDistinct("ORDER_ID").alias("ORDER_COUNT"),

        F.count("*").alias("LINE_ITEM_COUNT"),

        F.sum("ITEM_QUANTITY").alias("ITEM_QUANTITY"),

        F.sum("ITEM_REVENUE").alias("ITEM_REVENUE"),

        F.sum("OPTION_REVENUE").alias("OPTION_REVENUE"),

        F.sum("TOTAL_LINE_REVENUE").alias("TOTAL_REVENUE")
    )
    .withColumn(
        "AVERAGE_ORDER_VALUE",
        F.when(
            F.col("ORDER_COUNT") > 0,
            F.col("TOTAL_REVENUE") / F.col("ORDER_COUNT")
        )
        .otherwise(F.lit(0))
    )
)


# ============================================================
# 9. Gold dataset: restaurant_daily
#
# Grain:
# 1 row = 1 app + restaurant + date
# ============================================================

restaurant_daily = (
    silver_order_items
    .groupBy(
        "APP_NAME",
        "RESTAURANT_ID",
        "ORDER_DATE",
        "DAY_OF_WEEK",
        "IS_WEEKEND",
        "IS_HOLIDAY",
        "HOLIDAY_NAME"
    )
    .agg(
        F.countDistinct("ORDER_ID").alias("ORDER_COUNT"),

        F.countDistinct(
            F.when(
                F.col("CUSTOMER_TYPE") == "IDENTIFIED",
                F.col("USER_ID")
            )
        ).alias("CUSTOMER_COUNT"),

        F.count("*").alias("LINE_ITEM_COUNT"),

        F.sum("ITEM_REVENUE").alias("ITEM_REVENUE"),

        F.sum("OPTION_REVENUE").alias("OPTION_REVENUE"),

        F.sum("TOTAL_LINE_REVENUE").alias("TOTAL_REVENUE")
    )
    .withColumn(
        "AVERAGE_ORDER_VALUE",
        F.when(
            F.col("ORDER_COUNT") > 0,
            F.col("TOTAL_REVENUE") / F.col("ORDER_COUNT")
        )
        .otherwise(F.lit(0))
    )
)


# ============================================================
# 10. Gold dataset: item_daily
#
# Grain:
# 1 row = 1 app + restaurant + date + item
# ============================================================

item_daily = (
    silver_order_items
    .groupBy(
        "APP_NAME",
        "RESTAURANT_ID",
        "ORDER_DATE",
        "ITEM_CATEGORY",
        "ITEM_NAME"
    )
    .agg(
        F.sum("ITEM_QUANTITY").alias("QUANTITY_SOLD"),

        F.sum("ITEM_REVENUE").alias("ITEM_REVENUE"),

        F.countDistinct("ORDER_ID").alias("ORDER_COUNT"),

        F.avg("ITEM_PRICE").alias("AVERAGE_ITEM_PRICE")
    )
)


# ============================================================
# 11. Prepare options with order context
#
# Silver order_item_options does not contain:
# APP_NAME
# RESTAURANT_ID
# ORDER_DATE
#
# Therefore we obtain those attributes from Silver
# order_items using ORDER_ID + LINEITEM_ID.
# ============================================================

option_order_context = (
    silver_order_items
    .select(
        "ORDER_ID",
        "LINEITEM_ID",
        "APP_NAME",
        "RESTAURANT_ID",
        "ORDER_DATE"
    )
    .dropDuplicates(
        ["ORDER_ID", "LINEITEM_ID"]
    )
)


options_with_context = (
    silver_order_item_options
    .join(
        option_order_context,
        on=["ORDER_ID", "LINEITEM_ID"],
        how="inner"
    )
)


# ============================================================
# 12. Gold dataset: option_daily
#
# Grain:
# 1 row = 1 app + restaurant + date
#         + option group + option
# ============================================================

option_daily = (
    options_with_context
    .groupBy(
        "APP_NAME",
        "RESTAURANT_ID",
        "ORDER_DATE",
        "OPTION_GROUP_NAME",
        "OPTION_NAME"
    )
    .agg(
        F.sum("OPTION_QUANTITY").alias("OPTION_QUANTITY"),

        F.sum("OPTION_REVENUE").alias("OPTION_REVENUE"),

        F.countDistinct("ORDER_ID").alias("ORDER_COUNT"),

        F.avg("OPTION_PRICE").alias("AVERAGE_OPTION_PRICE"),

        F.sum(
            F.when(
                F.col("OPTION_PRICE") == 0,
                F.col("OPTION_QUANTITY")
            )
            .otherwise(0)
        ).alias("FREE_OPTION_QUANTITY"),

        F.sum(
            F.when(
                F.col("OPTION_PRICE") > 0,
                F.col("OPTION_QUANTITY")
            )
            .otherwise(0)
        ).alias("PAID_OPTION_QUANTITY"),

        F.countDistinct(
            F.when(
                F.col("OPTION_PRICE") == 0,
                F.col("ORDER_ID")
            )
        ).alias("FREE_OPTION_ORDER_COUNT"),

        F.countDistinct(
            F.when(
                F.col("OPTION_PRICE") > 0,
                F.col("ORDER_ID")
            )
        ).alias("PAID_OPTION_ORDER_COUNT"),

        F.sum(
            F.when(
                F.col("OPTION_PRICE") > 0,
                F.col("OPTION_REVENUE")
            )
            .otherwise(0)
        ).alias("PAID_OPTION_REVENUE")
    )
)


# ============================================================
# 13. Gold dataset: customer_summary
#
# Grain:
# 1 row = 1 identified customer
# ============================================================

identified_orders = (
    silver_order_items
    .filter(
        F.col("USER_ID").isNotNull()
        & (F.trim(F.col("USER_ID")) != "")
    )
)


customer_summary = (
    identified_orders
    .groupBy("USER_ID")
    .agg(
        F.countDistinct("ORDER_ID").alias("ORDER_COUNT"),

        F.sum("ITEM_QUANTITY").alias("ITEM_COUNT"),

        F.sum("ITEM_REVENUE").alias("TOTAL_ITEM_REVENUE"),

        F.sum("OPTION_REVENUE").alias("TOTAL_OPTION_REVENUE"),

        F.sum("TOTAL_LINE_REVENUE").alias("TOTAL_REVENUE"),

        F.min("ORDER_DATE").alias("FIRST_ORDER_DATE"),

        F.max("ORDER_DATE").alias("LAST_ORDER_DATE"),

        F.countDistinct(
            F.when(
                F.col("IS_LOYALTY") == True,
                F.col("ORDER_ID")
            )
        ).alias("LOYALTY_ORDER_COUNT"),

        F.sum(
            F.when(
                F.col("IS_LOYALTY") == True,
                F.col("TOTAL_LINE_REVENUE")
            )
            .otherwise(0)
        ).alias("LOYALTY_REVENUE")
    )
    .withColumn(
        "AVERAGE_ORDER_VALUE",
        F.when(
            F.col("ORDER_COUNT") > 0,
            F.col("TOTAL_REVENUE") / F.col("ORDER_COUNT")
        )
        .otherwise(F.lit(0))
    )
)

# ============================================================
# 14. Gold dataset: customer_ltv_daily
#
# Grain:
# 1 row = 1 identified customer + 1 order date
# ============================================================

# First, aggregate line-item revenue and distinct orders
# to one row per customer per date.
customer_daily_activity = (
    identified_orders
    .groupBy("USER_ID", "ORDER_DATE")
    .agg(
        F.sum("TOTAL_LINE_REVENUE").alias("DAILY_REVENUE"),
        F.countDistinct("ORDER_ID").alias("DAILY_ORDER_COUNT")
    )
)

# Define a running window for each customer, ordered by date.
customer_ltv_window = (
    Window
    .partitionBy("USER_ID")
    .orderBy("ORDER_DATE")
    .rowsBetween(
        Window.unboundedPreceding,
        Window.currentRow
    )
)

# Calculate cumulative lifetime value and cumulative orders.
customer_ltv_daily = (
    customer_daily_activity
    .withColumn(
        "CUMULATIVE_LTV",
        F.sum("DAILY_REVENUE").over(customer_ltv_window)
    )
    .withColumn(
        "CUMULATIVE_ORDER_COUNT",
        F.sum("DAILY_ORDER_COUNT").over(customer_ltv_window)
    )
    .select(
        "USER_ID",
        "ORDER_DATE",
        "DAILY_REVENUE",
        "CUMULATIVE_LTV",
        "DAILY_ORDER_COUNT",
        "CUMULATIVE_ORDER_COUNT"
    )
)

order_detail = (
    silver_order_items
    .select(
        "APP_NAME",
        "RESTAURANT_ID",
        "ORDER_DATE",
        "ORDER_ID",
        "LINEITEM_ID",
        "USER_ID",
        "ITEM_CATEGORY",
        "ITEM_NAME",
        "IS_LOYALTY",
        "CARD_STATUS",
        "TIME_OF_DAY_UTC",
        "ITEM_PRICE",
        "ITEM_QUANTITY",
        "ITEM_REVENUE",
        "OPTION_REVENUE",
        "TOTAL_LINE_REVENUE"
    )
)

# ============================================================
# Validate customer_ltv_daily
# ============================================================

customer_ltv_daily_count = customer_ltv_daily.count()

print(
    f"Gold customer_ltv_daily rows: "
    f"{customer_ltv_daily_count}"
)

if customer_ltv_daily_count == 0:
    raise ValueError(
        "Gold customer_ltv_daily contains no rows."
    )

duplicate_customer_daily_rows = (
    customer_ltv_daily
    .groupBy("USER_ID", "ORDER_DATE")
    .count()
    .filter(F.col("count") > 1)
)

duplicate_customer_daily_count = (
    duplicate_customer_daily_rows.count()
)

print(
    f"Duplicate customer_ltv_daily rows: "
    f"{duplicate_customer_daily_count}"
)

if duplicate_customer_daily_count > 0:
    raise ValueError(
        "Gold customer_ltv_daily contains duplicate "
        "USER_ID + ORDER_DATE combinations."
    )

# ============================================================
# 15. Validate Gold dataset row counts
# ============================================================

sales_hourly_count = sales_hourly.count()
restaurant_daily_count = restaurant_daily.count()
item_daily_count = item_daily.count()
option_daily_count = option_daily.count()
customer_summary_count = customer_summary.count()
order_detail_count = order_detail.count()

print(f"Gold sales_hourly rows: {sales_hourly_count}")
print(f"Gold restaurant_daily rows: {restaurant_daily_count}")
print(f"Gold item_daily rows: {item_daily_count}")
print(f"Gold option_daily rows: {option_daily_count}")
print(f"Gold customer_summary rows: {customer_summary_count}")
print(f"Gold order_detail rows: {order_detail_count}")
print(f"Gold customer_ltv_daily rows: {customer_ltv_daily_count}")  


# ============================================================
# 16. Validate Gold order_detail grain
# ============================================================

duplicate_gold_order_lines = (
    order_detail
    .groupBy(
        "ORDER_ID",
        "LINEITEM_ID"
    )
    .count()
    .filter(F.col("count") > 1)
)

duplicate_gold_order_line_count = (
    duplicate_gold_order_lines.count()
)

print(
    f"Duplicate Gold order_detail rows: "
    f"{duplicate_gold_order_line_count}"
)

if duplicate_gold_order_line_count > 0:
    raise ValueError(
        "Gold order_detail contains duplicate "
        "ORDER_ID + LINEITEM_ID combinations."
    )


# ============================================================
# 17. Write Gold datasets to S3
# ============================================================

sales_hourly.write \
    .mode("overwrite") \
    .parquet(
        f"{GOLD_BASE}/sales_hourly/"
    )

restaurant_daily.write \
    .mode("overwrite") \
    .parquet(
        f"{GOLD_BASE}/restaurant_daily/"
    )

item_daily.write \
    .mode("overwrite") \
    .parquet(
        f"{GOLD_BASE}/item_daily/"
    )

option_daily.write \
    .mode("overwrite") \
    .parquet(
        f"{GOLD_BASE}/option_daily/"
    )

customer_summary.write \
    .mode("overwrite") \
    .parquet(
        f"{GOLD_BASE}/customer_summary/"
    )

order_detail.write \
    .mode("overwrite") \
    .parquet(
        f"{GOLD_BASE}/order_detail/"
    )

# ============================================================
# 17. Write customer_ltv_daily to Gold
# ============================================================

customer_ltv_daily.write \
    .mode("overwrite") \
    .parquet(
        f"{GOLD_BASE}/customer_ltv_daily/"
    )


# ============================================================
# 18. Complete Glue job
# ============================================================

job.commit()
