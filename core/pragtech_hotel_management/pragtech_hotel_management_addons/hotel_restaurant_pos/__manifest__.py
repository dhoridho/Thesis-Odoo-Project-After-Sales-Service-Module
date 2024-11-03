{
    "name": "Hotel Restaurant POS",
    "version": "2.2",
    "author": "Pragmatic TechSoft Pvt Ltd",
    'website': 'http://pragtech.co.in/',
    "category": "Generic Modules/Hotel Restaurant POS",
    "description": """
    Module for Hotel Restaurant and POS intigration. You can manage:
    * Table booking as well as room booking from pos
    * Generate and process Kitchen Order ticket,
    """,
    "depends": ['point_of_sale', 'hotel', 'sale_enhancement'],
    "init_xml": [],
    "demo_xml": [],

    #     "update_xml" : ['views/templates.xml',
    #                     'views/hotel_restaurant_pos_view.xml',]

    # "depends" : ['point_of_sale','hotel_management'],
    "init_xml": [],
    "demo_xml": [],
    "data": ['security/ir.model.access.csv',
              'views/templates.xml',
             'views/hotel_restaurant_pos_view.xml',
             'wizard/pos_credit_details.xml',
             #                     'views/pos_credit_sales_report.xml',
             #                     'report/pos_credit_sale_report.xml',

             #                     'views/hotel_pos_workflow.xml',
             ],
    'installable': True,
    'application': True,

    # Web client
    #    'data':['wizard/pos_credit_details.xml'],
    'qweb': ['static/src/xml/hotel_pos.xml', ],

    #     'js': [
    #            'static/src/js/main.js',
    #            'static/src/js/widget.js',
    #            'static/src/js/models.js',
    #            'static/src/js/screens.js',
    #            'static/src/js/jquery.multiselect.js',
    #            'static/src/js/jquery.moment.js',
    #            ],
    #     'css': [ 'static/src/css/jquery.multiselect.css',
    #             'static/src/css/switch.css','static/src/css/pos.css'],



}
