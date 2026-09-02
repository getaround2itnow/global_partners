Note:  The SQL presented is conceptual design logic instead of executable code; for modeling purposes prior to transformation into PySpark for production purposes.

Pricing & Discount Effectiveness

    Calculating revenue from discounted orders vs from non-discounted orders.  Also total numbers of orders and average value of each order

    WITH discounted_orders AS (
        -- Step 1: Identify all distinct ORDER_IDs that have at least one discount option
        SELECT DISTINCT
    	    ORDER_ID
        FROM
    	    order_items_options
        WHERE
    	    OPTION_PRICE = 0
    ),

    order_totals AS (
    	-- Step 2: Compute the total spend per distinct order
        SELECT
    	    ORDER_ID,
            SUM(ITEM_PRICE * ITEM_QUANTITY) AS order_total
    	FROM
       	    order_items
	GROUP BY
            ORDER_ID
    ),

    order_classification AS (
    -- Step 3: Flag each order as 'Discounted' or 'Full Price'
    SELECT
        ot.ORDER_ID,
        ot.order_total,
        CASE 
            WHEN d.ORDER_ID IS NOT NULL THEN 'Discounted Order'
            ELSE 'Full Price Order'
        END AS discount_status
    FROM
        order_totals ot
    LEFT JOIN
        discounted_orders d ON ot.ORDER_ID = d.ORDER_ID
   )

    -- Step 4: Aggregate total revenue, order count, and AOV by status
    SELECT
        discount_status,
        COUNT(ORDER_ID) AS total_orders,
        ROUND(SUM(order_total), 2) AS total_revenue,
        ROUND(AVG(order_total), 2) AS average_order_value,
        ROUND(
            100.0 * COUNT(ORDER_ID) / SUM(COUNT(ORDER_ID)) OVER (), 
            2
        ) AS pct_of_total_orders,
        ROUND(
            100.0 * SUM(order_total) / SUM(SUM(order_total)) OVER (), 
            2
        ) AS pct_of_total_revenue
    FROM
        order_classification
    GROUP BY
        discount_status;