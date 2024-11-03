# -*- coding: utf-8 -*-
{
    'name': "Equip3 POS Report Philippines",
    'summary': "Modification POS Report Philippines ",
    'description': "Modification POS Report Philippines ",
    'author': "PT. HashMicro Pte. Ltd.",
    'website': "http://www.hashmicro.com",
    'category': 'Uncategorized',
    'version': '1.1.6',
    'depends': ['equip3_pos_report','equip3_pos_membership','point_of_sale'],
    'data': [
        'views/assets.xml',
        'views/pos_config_views.xml',
        'views/res_views.xml',
        'views/product_views.xml',
        'views/pos_receipt_template_views.xml',
        'views/pos_order_views.xml',
        'views/account_views.xml',
        'report/receipt_template_overview.xml',
        'report/pos_sale_report_template.xml',
        'report/sale_summary_report.xml',
        'wizards/z_report_views.xml',
        'wizards/pos_sale_summary_wizard_views.xml',
    ],
    'qweb': [ 
        'static/src/xml/Screens/Receipt/*.xml',
    ], 


}
