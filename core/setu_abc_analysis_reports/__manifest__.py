# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'ABC Sales Analysis Reports',
    'version' : '1.1.1',
    'price' : 149,
    'currency'  :'EUR',
    'category': 'sale',
    'summary': """Inventory Techniques - ABC Sales Analysis Reports, 
                  Inventory XYZ Analysis Report, ABC-XYZ Combine Analysis Report, ABC Sales Frequency Analysis Report,
                  fsn analysis, xyz analysis, abc analysis, inventory reports, inventory management,
                  track product, product movement, stock movement,
                  """,
    'website' : 'https://www.setuconsulting.com' ,
    'support' : 'support@setuconsulting.com',
    'description' : """
        ABC Sales Analysis Reports
        --------------------------
        - Overview
        In any industry it is mandatory to evaluate product performance so they can focus their time and energy on right products which represent the biggest revenue source for the company. But it’s not that much of an easy function to execute.
        The ABC analysis is an inventory categorization method that assigns a class to every item - or SKU, or product - typically referred to as A, B and C, where A (resp. C) is the class associated with the most (resp. least) frequently sold or consumed items.
        Our solution helps you to categorize your sales into ABC classification, ABC-XYZ Combines classification, XYZ classifications and ABC classification for sales order frequency for each product sold out in the company.

        - Key features
        => ABC Sales Analysis Report
        ABC analysis of inventory allows you to know which products deserve most of your resources and attention to help you boost your sales and net margins.
        
        => XYZ Analysis Report
        Helps classify inventory items according to variability of their demand based on stock value and helps minimize the inventory carrying cost.
    
        => ABC - XYZ Combined Analysis Report
        The ABC XYZ classification thus provides a framework for developing and refining inventory management strategies by classifying products according to their sales volume (ABC) but also according to their uncertainties (XYZ).

        => ABC Sales Frequency Analysis Report
        ABC Sales Frequency Analysis helps classify products according to the frequency of orders rather than ordered quantity which helps to define putaway and removal strategy of the products.

        - Details
        => ABC Sales Analysis Report
        ABC analysis is derived from the term “The Pareto Principle” named after an Italian economist Vilfredo Pareto, also called the 80/20 rule. ABC analysis of inventory allows you to separate your most important products from your least important ones so that you know which products deserve most of your resources and attention to help you boost your sales and net margins.
        
        ABC analysis of inventory helps you keep working capital costs low because it identifies which items you should reorder more frequently and which items don’t need to be stocked often – reducing obsolete inventory and optimizing the rate of inventory turnover.
        The meanings in the list after the application of the method ABC are divided into three groups
        A – the most important for the total of (20% gives 80% of the results).
        B – average in importance (30% - 15%).
        C - the least important (50% - 5%).

        - Advantages of ABC Analysis

        Better Forecasting
            ABC analysis of inventory helps you effectively forecast demand by splitting your sales into categories that are based on customer demand.
        Negotiations with Suppliers
            After analyzing your sales and sorting it into A, B, or C categories, you’ll know which products you should focus on buying at the lowest price, and which suppliers of those products you should negotiate with to bring their prices down so you can maximize your profit margins.
        Strategic Pricing
            Since you know items in category A are your best-sellers, you may be able to raise the prices of those products for increased revenue. Whereas, with products in category B or C, you know you may have to use creative sale techniques like product bundling or social media sales to move these products out of your warehouse.
        Inventory optimization
            Inventory optimization is the most crucial reason why ABC inventory analysis is preferred by many businesses. to organize and segregate the products in the inventory as per their revenue and importance.
        
        Inventory XYZ Analysis Report
        -----------------------------
        XYZ Analysis is always done for the current Stock in Inventory and aims at classifying the items into three classes on the basis of their Inventory values. 
        The current value of the items/variants in the Inventory alone is taken into consideration for the Analysis and it is not possible to do this analysis for any other dates. 
        
        First 70% of the total Inventory value corresponds to X Class 
        Next 20% are of Y Class 
        Last 10% of the value corresponds to the Z Class.
        
        - Advantage of XYZ analysis
        XYZ classification helps to identify inventories investment status
        XYZ classification helps to decide action plan for existing inventories whether any inventories require strategically sales planning or not 
        XYZ classification helps to  evaluate how each inventory part should be monitored and controlled.
            - Some inventories are critically important and require close monitoring and tight control.
            - Some inventories are of lower criticality requiring standard controls and periodic reviews of usage. 
            - Some require the least controls, are sometimes issued as “free stock” or forward holding.
        Company wise separate reporting 
        User can filter by companies, categories & products
        Report can be downloaded in well format EXCEL file
        Report can be analysed in graphical form (Charts)
        Report available in list view to give flexibility about grouping, searching.
        
        
        ABC-XYZ Combine Analysis Report
        -------------------------------
        The ABC XYZ analysis is fundamental to optimize your inventory. The ABC method is a very good start but this is not enough in managing your inventory.
        The ABC XYZ classification thus provides a framework for developing and refining inventory management strategies by classifying products according to their sales volume (ABC) but also according to their uncertainties (XYZ). Your procurement strategy will then be different according to this new classification to optimize your stock and customer service rate.
        
        Main purpose of ABC-XYZ Combined Analysis
            - Classify by Sales Volume => ABC Analysis
            - Classify by Uncertainty => XYZ Analysis
        
        - Advantage of ABC-XYZ Combined Analysis
    
        XYZ analysis when combined with ABC analysis helps to formulate more specific sales strategies. 
        ABC-XYZ combined analysis helps to decide putaway and removal strategy of the products
        ABC-XYZ combined analysis clarifies service levels for items with volatile demand.
        It helps to reduces stock obsolescence
        It helps to Improve accuracy of forecasting.
        Reduces stock-out possibilities
        Report can be downloaded in well format EXCEL file
        Report can be analysed in graphical form (Charts)
        Report available in list view to give flexibility about grouping, searching.
    
        ABC Sales Frequency Analysis Report
        -----------------------------------
        It is always necessary for warehousing operations to keep the products stock in the right place  in the warehouse. For warehousing operation it is more important to consider orders frequency rather than order quantity. 
        How many times warehouse users need to run throughout the stocks and arrange the shipments for orders. So it is always useful for them to identify which products are frequently ordered and which are less. So they can keep frequently moving products in nearer locations and least running products keep away. In the warehouse.
        This report gives you a detailed idea about the products ordered frequency from highest order to lowest order. 
        
        - Advantage of ABC Sales Frequency Analysis Report
        Allows you to focus your attention on the highest moving items
        Improves decision making on the timing and quantity of inventory sales or consumption
        Helps to define removal strategy and putaway strategy of an items
        Helps you understand the risk by checking whether all sales comes from single order or multiple orders
        User can filter by companies, categories, warehouses & products
        Report can be downloaded in well format EXCEL file
        Report can be analysed in graphical form (Charts)
        Report available in list view to give flexibility about grouping, searching.

    """,
    'author' : 'Setu Consulting Services Pvt. Ltd.',
    'license' : 'OPL-1',
    'sequence': 25,
    'depends' : ['sale_management','sale_stock'],
    'images': ['static/description/banner.gif'],
    'data' : [
        'security/ir.model.access.csv',
        'views/setu_abc_sales_analysis_report.xml',
        'views/setu_inventory_xyz_analysis_report.xml',
        'views/setu_abc_xyz_analysis_report.xml',
        'views/setu_abc_sales_frequency_analysis_report.xml',
        'db_function/get_sales_data.sql',
        'db_function/get_abc_sales_analysis_data.sql',
        'db_function/get_sales_frequency_data.sql',
        'db_function/get_abc_sales_analysis_data_by_company.sql',
        'db_function/get_inventory_xyz_analysis_data.sql',
        'db_function/get_abc_xyz_analysis_report.sql',
        'db_function/get_abc_sales_frequency_analysis_data.sql',
    ],
    'application': True,
    # 'pre_init_hook': 'pre_init',
    #'live_test_url' : 'http://95.111.225.133:5929/web/login',
}
