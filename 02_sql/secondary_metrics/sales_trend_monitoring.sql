Note:  The SQL presented is conceptual design logic instead of executable code; for modeling purposes prior to transformation into PySpark for production purposes.

Total weekly revenue according to time of day:

	Option 1: Pivoted by Daypart (One Row per Week) - outputs one row per week with separate columns for Morning, Afternoon, Evening, 			
		and Total revenue.

	SELECT
	    DATE_TRUNC('week', CREATION_TIME_UTC) AS order_week,
    
	    -- Morning: Before 12:00 (Hours 0 - 11)
	    SUM(CASE 
        	WHEN EXTRACT(HOUR FROM CREATION_TIME_UTC) < 12 
	        THEN ITEM_PRICE * ITEM_QUANTITY 
        	ELSE 0 
	    END) AS morning_revenue,
    
 	   -- Afternoon: 12:00 up to 16:00 (Hours 12 - 15)
	    SUM(CASE 
        	WHEN EXTRACT(HOUR FROM CREATION_TIME_UTC) >= 12 AND EXTRACT(HOUR FROM CREATION_TIME_UTC) < 16 
	        THEN ITEM_PRICE * ITEM_QUANTITY 
        	ELSE 0 
	    END) AS afternoon_revenue,
    
  	    -- Evening / Night: 16:00 onwards (Hours 16 - 23)
	    SUM(CASE 
        	WHEN EXTRACT(HOUR FROM CREATION_TIME_UTC) >= 16 
	        THEN ITEM_PRICE * ITEM_QUANTITY 
        	ELSE 0 
	    END) AS evening_revenue,
    
       	-- Total Weekly Revenue
	SUM(ITEM_PRICE * ITEM_QUANTITY) AS total_weekly_revenue

		FROM
		    order_items
		GROUP BY
		    DATE_TRUNC('week', CREATION_TIME_UTC)
		ORDER BY
		    order_week DESC;    

	Option 2: Grouped by Week and Time of Day (Long Format) each daypart as its own separate row under each week (useful for BI 							dashboard dimension breakdowns):
		
	SELECT
    	    DATE_TRUNC('week', CREATION_TIME_UTC) AS order_week,
	    CASE
	        WHEN EXTRACT(HOUR FROM CREATION_TIME_UTC) < 12 THEN 'Morning'
	        WHEN EXTRACT(HOUR FROM CREATION_TIME_UTC) < 16 THEN 'Afternoon'
	        ELSE 'Evening'
	    END AS time_of_day,
	    SUM(ITEM_PRICE * ITEM_QUANTITY) AS total_revenue
	FROM
	    order_items
	GROUP BY
	    DATE_TRUNC('week', CREATION_TIME_UTC),
	    CASE
        	WHEN EXTRACT(HOUR FROM CREATION_TIME_UTC) < 12 THEN 'Morning'
	        WHEN EXTRACT(HOUR FROM CREATION_TIME_UTC) < 16 THEN 'Afternoon'
        	ELSE 'Evening'
	    END
	ORDER BY
	    order_week DESC,
	    MIN(EXTRACT(HOUR FROM CREATION_TIME_UTC));
	
Total weekly revenue per time of day per restaurant:

	SELECT
	    RESTAURANT_ID,
	    DATE_TRUNC('week', CREATION_TIME_UTC) AS order_week,
    
            -- Morning: Before 12:00
	    SUM(CASE 
	        WHEN EXTRACT(HOUR FROM CREATION_TIME_UTC) < 12 
        	THEN ITEM_PRICE * ITEM_QUANTITY 
	        ELSE 0 
	    END) AS morning_revenue,
    
    	-- Afternoon: 12:00 to 16:00
	SUM(CASE 
            WHEN EXTRACT(HOUR FROM CREATION_TIME_UTC) >= 12 AND EXTRACT(HOUR FROM CREATION_TIME_UTC) < 16 
	    THEN ITEM_PRICE * ITEM_QUANTITY 
	    ELSE 0 
	END) AS afternoon_revenue,
    
    	-- Evening: 16:00 onwards
	SUM(CASE 
            WHEN EXTRACT(HOUR FROM CREATION_TIME_UTC) >= 16 
	    THEN ITEM_PRICE * ITEM_QUANTITY 
            ELSE 0 
	END) AS evening_revenue,
    
    	-- Total Weekly Revenue for the Restaurant
        SUM(ITEM_PRICE * ITEM_QUANTITY) AS total_weekly_revenue

    FROM
        order_items
    GROUP BY
    	RESTAURANT_ID,
	DATE_TRUNC('week', CREATION_TIME_UTC)
    ORDER BY
    	RESTAURANT_ID ASC,
	order_week DESC;

Total weekly revenue per restaurant:


    SELECT
        RESTAURANT_ID,
	DATE_TRUNC('week', CREATION_TIME_UTC) AS order_week,
	SUM(ITEM_PRICE * ITEM_QUANTITY) AS total_weekly_revenue
    FROM
        order_items
    GROUP BY
        RESTAURANT_ID,
        DATE_TRUNC('week', CREATION_TIME_UTC)
    ORDER BY
        RESTAURANT_ID ASC,
        order_week DESC;

The same metric can be calculated for menu category by substituting RESTAURANT_ID with ITEM_CATEGORY