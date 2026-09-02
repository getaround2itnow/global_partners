Note:  The SQL presented is conceptual design logic instead of executable code; for modeling purposes prior to transformation into PySpark for production purposes.


    Locating most recent customer:

	SELECT
		USER_ID,
		ORDER_ID,
		LINEITEM_ID,
		CREATION_TIME_UTC
		(ITEM_PRICE x ITEM_QUANTITY) as total_purch_amount
	FROM
		(
		SELECT oi.*,
			ROW_NUMBER() OVER (PARTITION BY) USER_ID ORDER BY CREATION_TIME_UTC DESC) AS most_recent_purchase
		FROM ORDER_ITEMS oi
	) t
	WHERE most_recent_purchase = 1

    Locating the 5 most recent customers:

	SELECT
		USER_ID,
		ORDER_ID,
		LINEITEM_ID,
		CREATION_TIME_UTC
		(ITEM_PRICE x ITEM_QUANTITY) as total_purch_amount
	FROM
		(
		SELECT oi.*,
			ROW_NUMBER() OVER (PARTITION BY) USER_ID ORDER BY CREATION_TIME_UTC DESC) AS most_recent_purchase
		FROM ORDER_ITEMS oi
	) t
	WHERE most_recent_purchase <= 5;

    Locating the most frequent customers within the last month (for SQL Server):

	SELECT
    	    USER_ID,
	    COUNT(DISTINCT ORDER_ID) AS number_of_purchases
	FROM
	    order_items
	WHERE
	    CREATION_TIME_UTC >= DATEADD(month, -1, GETUTCDATE())
	GROUP BY
	    USER_ID
	ORDER BY
    	    number_of_purchases DESC;
    
    Locating the most total amounts spent per customer within the last month (for SQL Server):
	
	SELECT
	    USER_ID,
	    SUM(ITEM_PRICE * ITEM_QUANTITY) AS total_amount_spent
	FROM
	    order_items
	WHERE
	    CREATION_TIME_UTC >= DATEADD(month, -1, CURRENT_TIMESTAMP)
	GROUP BY
	    USER_ID
	ORDER BY
	    total_amount_spent DESC;