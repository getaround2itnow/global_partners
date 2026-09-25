import sys

from awsglue.utils import getResolvedOptions
from pyspark.context import SparkContext
from awsglue.context import GlueContext
from awsglue.job import Job
from pyspark.sql import functions as F


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

BRONZE_BASE = "s3://global-partners-project-raw/bronze"
SILVER_BASE = "s3://global-partners-project-refined/silver"


# ============================================================
# 4. Read Bronze datasets
# ============================================================

order_items = spark.read.parquet(
    f"{BRONZE_BASE}/order_items/"
)

order_item_options = spark.read.parquet(
    f"{BRONZE_BASE}/order_items_options/"
)

date_dim = spark.read.parquet(
    f"{BRONZE_BASE}/date_dim/"
)


# ============================================================
# 5. Basic source validation
# ============================================================

order_items_count = order_items.count()
options_count = order_item_options.count()
date_dim_count = date_dim.count()

print(f"Bronze order_items rows: {order_items_count}")
print(f"Bronze order_item_options rows: {options_count}")
print(f"Bronze date_dim rows: {date_dim_count}")

order_items.printSchema()
order_item_options.printSchema()
date_dim.printSchema()


# ============================================================
# 6. Calculate option revenue at line-item grain
# ============================================================

options_by_line = (
    order_item_options
    .withColumn(
        "OPTION_REVENUE",
        F.col("OPTION_PRICE").cast("decimal(18,2)")
        * F.col("OPTION_QUANTITY")
    )
    .groupBy(
        "ORDER_ID",
        "LINEITEM_ID"
    )
    .agg(
        F.sum("OPTION_REVENUE").alias("OPTION_REVENUE")
    )
)


# ============================================================
# 7. Identify option records that do not match an order line
# ============================================================

unmatched_options = (
    order_item_options
    .select("ORDER_ID", "LINEITEM_ID")
    .distinct()
    .join(
        order_items.select("ORDER_ID", "LINEITEM_ID").distinct(),
        on=["ORDER_ID", "LINEITEM_ID"],
        how="left_anti"
    )
)

print(
    f"Unmatched option ORDER_ID + LINEITEM_ID combinations: "
    f"{unmatched_options.count()}"
)


# ============================================================
# 8. Prepare order_items
# ============================================================

silver_order_items = (
    order_items

    # --------------------------------------------------------
    # Revenue
    # --------------------------------------------------------

    .withColumn(
        "ITEM_REVENUE",
        F.col("ITEM_PRICE").cast("decimal(18,2)")
        * F.col("ITEM_QUANTITY")
    )

    # --------------------------------------------------------
    # UTC date/time attributes
    # --------------------------------------------------------

    .withColumn(
        "ORDER_DATE",
        F.to_date("CREATION_TIME_UTC")
    )

    .withColumn(
        "ORDER_HOUR_UTC",
        F.hour("CREATION_TIME_UTC")
    )

    .withColumn(
        "TIME_OF_DAY_UTC",
        F.when(
            F.col("ORDER_HOUR_UTC") < 5,
            "Night"
        )
        .when(
            F.col("ORDER_HOUR_UTC") < 12,
            "Morning"
        )
        .when(
            F.col("ORDER_HOUR_UTC") < 17,
            "Afternoon"
        )
        .otherwise(
            "Evening"
        )
    )

    # --------------------------------------------------------
    # Customer classification
    # --------------------------------------------------------

    .withColumn(
        "CUSTOMER_TYPE",
        F.when(
            F.col("USER_ID").isNull()
            | (F.trim(F.col("USER_ID")) == ""),
            "GUEST"
        )
        .otherwise("IDENTIFIED")
    )

    # --------------------------------------------------------
    # Printed card classification
    # --------------------------------------------------------

    .withColumn(
        "CARD_STATUS",
        F.when(
            F.col("PRINTED_CARD_NUMBER").isNotNull()
            & (F.trim(F.col("PRINTED_CARD_NUMBER")) != ""),
            "CARD_PRESENT"
        )
        .otherwise("NO_CARD")
    )
)


# ============================================================
# 9. Join option revenue to order_items
# ============================================================

silver_order_items = (
    silver_order_items
    .join(
        options_by_line,
        on=["ORDER_ID", "LINEITEM_ID"],
        how="left"
    )
    .fillna(
        {"OPTION_REVENUE": 0}
    )
    .withColumn(
        "TOTAL_LINE_REVENUE",
        F.col("ITEM_REVENUE")
        + F.col("OPTION_REVENUE")
    )
)


# ============================================================
# 10. Prepare Silver date dimension
# ============================================================

# Generate a complete calendar covering the full order-data date range.
calendar_start = "2020-04-21"
calendar_end = "2024-02-21"

silver_date_dim = (
    spark.sql(
        f"""
        SELECT sequence(
            to_date('{calendar_start}'),
            to_date('{calendar_end}'),
            interval 1 day
        ) AS date_array
        """
    )
    .select(F.explode("date_array").alias("date_key"))
    .withColumn("year", F.year("date_key"))
    .withColumn("month", F.month("date_key"))
    .withColumn("week", F.weekofyear("date_key"))
    .withColumn("day_of_week", F.date_format("date_key", "EEEE"))
    .withColumn(
        "is_weekend",
        F.dayofweek("date_key").isin([1, 7])
    )
    .withColumn(
        "is_holiday",
        F.lit(False)
    )
    .withColumn(
        "holiday_name",
        F.lit(None).cast("string")
    )
)

# ============================================================

# 11. Join date dimension
# ============================================================

date_attributes = silver_date_dim.select(
    "date_key",
    "year",
    "month",
    "week",
    "day_of_week",
    "is_weekend",
    "is_holiday",
    "holiday_name"
)

silver_order_items = (
    silver_order_items
    .join(
        date_attributes,
        silver_order_items["ORDER_DATE"]
        == date_attributes["date_key"],
        how="left"
    )
    .drop("date_key")
)


# ============================================================
# 12. Validate Silver grain
# ============================================================

silver_count = silver_order_items.count()

print(f"Silver order_items rows: {silver_count}")

if silver_count != order_items_count:
    raise ValueError(
        "Silver row count does not match Bronze order_items row count."
    )


# ============================================================
# 13. Prepare Silver options
# ============================================================

silver_order_item_options = (
    order_item_options
    .withColumn(
        "OPTION_REVENUE",
        F.col("OPTION_PRICE").cast("decimal(18,2)")
        * F.col("OPTION_QUANTITY")
    )
)


# 14. Write Silver datasets
# ============================================================

silver_order_items.write \
    .mode("overwrite") \
    .parquet(
        f"{SILVER_BASE}/order_items/"
    )

silver_order_item_options.write \
    .mode("overwrite") \
    .parquet(
        f"{SILVER_BASE}/order_item_options/"
    )

silver_date_dim.write \
    .mode("overwrite") \
    .parquet(
        f"{SILVER_BASE}/date_dim/"
    )


# ============================================================
# 15. Complete Glue job
# ============================================================

job.commit()
