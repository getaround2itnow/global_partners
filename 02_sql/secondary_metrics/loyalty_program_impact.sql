Note:  The SQL presented is conceptual design logic instead of executable code; for modeling purposes prior to transformation into PySpark for production purposes.

Calculating total orders, average, minimum, maximum and total for non-loyalty customers with no USER_ID.
    

    WITH non_loyalty_order_totals AS (
    	-- Step 1: Calculate the total spend per distinct guest order
	SELECT
            ORDER_ID,
            SUM(ITEM_PRICE * ITEM_QUANTITY) AS order_total
	FROM
            order_items
	WHERE
            IS_LOYALTY = FALSE  -- Use 0 if stored as a tinyint/boolean flag
	GROUP BY
            ORDER_ID
	)

	-- Step 2: Compute overall aggregate metrics across all non-loyalty orders
 	SELECT
	    COUNT(ORDER_ID) AS total_non_loyalty_orders,
	    ROUND(AVG(order_total), 2) AS avg_amount_spent_per_order,
	    ROUND(MAX(order_total), 2) AS max_amount_spent_on_order,
	    ROUND(MIN(order_total), 2) AS min_amount_spent_on_order,
	    ROUND(SUM(order_total), 2) AS total_non_loyalty_revenue
	FROM
	    non_loyalty_order_totals;

    Calculating total_orders, average purchase amount, customer lifetime value to date for non-loyalty users who have a USER_ID.

    WITH non_loyalty_orders AS (
    	-- Step 1: Calculate total spend per distinct order
	SELECT
            USER_ID,
            ORDER_ID,
     	    SUM(ITEM_PRICE * ITEM_QUANTITY) AS order_total
	FROM
            order_items
        WHERE
    	    IS_LOYALTY = FALSE          -- Adjust to 0 if stored as integer/bit
        AND 
	    USER_ID IS NOT NULL
	GROUP BY
            USER_ID,
            ORDER_ID
    )

    -- Step 2: Aggregate to customer-level metrics
    SELECT
    	USER_ID,
	COUNT(ORDER_ID) AS total_orders,
	ROUND(AVG(order_total), 2) AS avg_purchase_amount,
	ROUND(SUM(order_total), 2) AS lifetime_spent
    FROM
    	non_loyalty_orders
    GROUP BY
    	USER_ID
    ORDER BY
    	lifetime_spent DESC;

    Calculating average spending, number of orders per customer and total revenue to date for loyalty customers

    WITH loyalty_order_totals AS (
	SELECT
	    USER_ID,
	    SUM(ITEM_PRICE * ITEM_QUANTITY) AS order_total
	FROM
	    order_items
	WHERE
	    IS_LOYALTY = TRUE
 	GROUP BY
	    USER_ID
	)
    SELECT
	USER_ID,
	AVG(order_total) AS average_order_amount,
	COUNT(USER_ID) AS number_of_orders,
	SUM(order_total) AS total_loyalty_revenue
    FROM
	loyalty_order_totals
    GROUP BY
	USER_ID