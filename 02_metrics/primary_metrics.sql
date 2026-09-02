Note:  The SQL presented is conceptual design logic instead of executable code; for modeling purposes prior to transformation into PySpark for production purposes.


Customer Lifetime Value

	Will determine sum of all customer purchases (per a user_id) during 
		the customer's history with the App.  Will use the following
		SQL query as a guide:

	WITH order_total_CLV AS (
	    SELECT
		ORDER_ID,
		LINEITEM_ID,
		USER_ID,
		(ITEM_PRICE x ITEM_QUANTITY) AS total_regular_purchase
	    FROM
		order_items
	    GROUP BY
		USER_ID
		) AS ortc,
	option_total_CLV AS (
	    SELECT
		ORDER_ID,
		LINEITEM_ID,
		(ITEM_PRICE x ITEM_QUANTITY) AS total_options_price
	    FROM
		order_items_options
	    GROUP BY
		ORDER_ID, LINEITEM_ID,
		) AS optc
	SELECT
		ortc.USER_ID,
		optc.ORDER_ID,
		optc.LINEITEM_ID,
		(ortc.total_regular_purchase + optc.total_option_purchase) AS lifetime_total
	FROM
		order_total_CLV
	JOIN
		option_total_CLV
	ON	
		ortc.ORDER_ID + optc.ORDER_ID
	AND
		ortc.LINEITEM_ID + optc.LINEITEM_ID
	GROUP BY
		ortc.ORDER_ID, ortc.LINEITEM_ID
