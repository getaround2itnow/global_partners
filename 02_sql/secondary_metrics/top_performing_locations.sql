Note:  The SQL presented is conceptual design logic instead of executable code; for modeling purposes prior to transformation into PySpark for production purposes.


Calculating total revenue, average order value and orders per week per restaurant

    WITH order_totals AS (
    	-- Step 1: Calculate the total spend and week per distinct order
	SELECT
            RESTAURANT_ID,
            ORDER_ID,
    	    DATE_TRUNC('week', MIN(CREATION_TIME_UTC)) AS order_week,
            SUM(ITEM_PRICE * ITEM_QUANTITY) AS order_total
        FROM
    	    order_items
        GROUP BY
    	    RESTAURANT_ID,
            ORDER_ID
    )

    -- Step 2: Aggregate to the restaurant-weekly level
    SELECT
    	RESTAURANT_ID,
        order_week,
        SUM(order_total) AS total_revenue,
	COUNT(ORDER_ID) AS weekly_order_count,
        ROUND(AVG(order_total), 2) AS average_order_value
    FROM
    	order_totals
    GROUP BY
    	RESTAURANT_ID,
	order_week
    ORDER BY
    	RESTAURANT_ID ASC,
        order_week DESC;