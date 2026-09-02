Note:  The SQL presented is conceptual design logic instead of executable code; for modeling purposes prior to transformation into PySpark for production purposes.

Determining days since last order per customer within last month:

	SELECT
    		USER_ID,
		DATEDIFF(day, MAX(CREATION_TIME_UTC), CURRENT_TIMESTAMP) AS days_since_last_order
	FROM
	        order_items
	WHERE
	    CREATION_TIME_UTC >= DATEADD(month, -1, CURRENT_TIMESTAMP)
	GROUP BY
	    USER_ID
	ORDER BY
	    total_amount_spent DESC;

    Determining average gaps between orders in terms of amount spent & number of days:

	WITH order_summary AS (
	    -- Step 1: Aggregate line items to the distinct order level
	    SELECT
        	USER_ID,
	        ORDER_ID,
 	        MIN(CREATION_TIME_UTC) AS order_time,
        	SUM(ITEM_PRICE * ITEM_QUANTITY) AS order_total
	    FROM
        	order_items
	    GROUP BY
        	USER_ID,
	        ORDER_ID
	),

	order_gaps AS (
	    -- Step 2: Compare each order to the previous order for the same user
	    SELECT
        	USER_ID,
	        order_time,
	        order_total,
        	-- Time difference in days since the previous order
	        DATEDIFF(
        	    day,
	            LAG(order_time) OVER (PARTITION BY USER_ID ORDER BY order_time),
        	    order_time
	        ) AS days_since_prev_order,
        	-- Difference in spend compared to the previous order
	        order_total - LAG(order_total) OVER (PARTITION BY USER_ID ORDER BY order_time) AS spend_diff_from_prev_order
	    FROM
        	order_summary
	)

	-- Step 3: Compute the average gaps per user
	SELECT
	    USER_ID,
	    COUNT(order_time) AS total_orders,
	    AVG(days_since_prev_order) AS avg_days_between_orders,
	    AVG(spend_diff_from_prev_order) AS avg_spend_diff_between_orders
	FROM
	    order_gaps
	GROUP BY
	    USER_ID
	HAVING
	    COUNT(order_time) > 1  -- Filters out users with only 1 order (no gaps to measure)
	ORDER BY
	    avg_days_between_orders ASC;

    Calculating the percentage change in spending per customer for the last 5 orders:

	WITH order_summary AS (
	    -- Step 1: Aggregate line items to order-level totals
	    SELECT
        	USER_ID,
	        ORDER_ID,
	        MIN(CREATION_TIME_UTC) AS order_time,
        	SUM(ITEM_PRICE * ITEM_QUANTITY) AS order_total
	    FROM
        	order_items
	    GROUP BY
	        USER_ID,
	        ORDER_ID
	),

	order_history AS (
	    -- Step 2: Determine recency and capture previous order amount
	    SELECT
        	USER_ID,
	        ORDER_ID,
        	order_time,
	        order_total,
        	ROW_NUMBER() OVER (PARTITION BY USER_ID ORDER BY order_time DESC) AS recency_rank,
	        LAG(order_total) OVER (PARTITION BY USER_ID ORDER BY order_time ASC) AS prev_order_total
	    FROM
        	order_summary
	)

	-- Step 3: Filter for the last 5 orders and calculate percentage change
	SELECT
	    USER_ID,
	    ORDER_ID,
	    order_time,
	    order_total,
	    prev_order_total,
	    ROUND(
        	((order_total - prev_order_total) * 100.0) / NULLIF(prev_order_total, 0),
	        2
	    ) AS pct_change_from_prev_order
	FROM
	    order_history
	WHERE
	    recency_rank <= 5
	ORDER BY
	    USER_ID,
	    order_time ASC;