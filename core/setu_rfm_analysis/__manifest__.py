# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'RFM Analysis - Marketing Strategy',
    'version' : '1.1.4',
    'price' : 199,
    'currency'  :'EUR',
    'category': 'sale',
    'summary': """	
		RFM Analysis - A powerful marketing strategy
        RFM analysis increases business sales. It enables personalized marketing, increases engagement, and allows you to create specific, relevant offers to the right groups of customers.        
        RFM analysis allows marketers to target specific clusters of customers with communications that are much more relevant for their particular behavior – and thus generate much higher rates of response, plus increased loyalty and customer lifetime value.
        
        eCommerce sales analysis with RFM technique
        RFM analysis is a data driven customer behavior segmentation technique. 
        RFM analysis increases eCommerce sales. It enables personalized marketing, increases engagement, and allows you to create specific, relevant offers to the right groups of customers.
        It helps eCommerce sellers, online stores, marketplaces to boost their sales
        Directly integrated with Email Marketing, Automated mailing list generation feature 
		""",
    'website' : 'https://www.setuconsulting.com' ,
    'support' : 'support@setuconsulting.com',
    'description' : """
        RFM analysis is a data driven customer behavior segmentation technique.
        RFM stands for recency, frequency, and monetary value.
        RFM is a method used for analyzing customer value.
        As you can gauge, RFM analysis is a handy method to find your best customers, understand their behavior and then run targeted email / marketing campaigns to increase sales, satisfaction and customer lifetime value.
        
        RFM analysis increases eCommerce sales.
        It enables personalized marketing, increases engagement, and allows you to create specific, relevant offers to the right groups of customers.
        RFM analysis allows marketers to target specific clusters of customers with communications that are much more relevant for their particular behavior – and thus generate much higher rates of response, plus increased loyalty and customer lifetime value.

        RFM Analysis, our solution helps you to run targeted email / marketing campaigns to increase sales, satisfaction and customer lifetime value.
        With our solution you can easily bifurcate your customers by RFM segments which gives you a clear idea about your marketing strategy.  
    """,
    'author' : 'Setu Consulting Services Pvt. Ltd.',
    'license' : 'OPL-1',
    'sequence': 25,
    'depends' : ['sale_stock', 'mass_mailing_sale', 'sale_crm'],
    'images': ['static/description/banner.gif'],
    'data' : [
        'views/res_config_settings_views.xml',
        'views/rfm_segment.xml',
        'views/res_partner.xml',
        'views/team_customer_segment.xml',
        'views/update_customer_segment.xml',
        'views/rfm_quotation.xml',
        # 'data/db_operation.xml',
        'data/rfm_segment.xml',
        'data/rfm_score.xml',
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'db_function/get_rfm_analysis_data.sql',
        'db_function/update_customer_rfm_segment.sql',
        'db_function/get_rfm_segment_ratio_analysis_data.sql',
        'reports/rfm_yearly_analysis_by_segment.xml',

    ],
    'application': True,
    # 'pre_init_hook': 'pre_init',
    'live_test_url' : 'http://95.111.225.133:5929/web/login',
}
