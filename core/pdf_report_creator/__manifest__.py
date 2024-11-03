# -*- coding: utf-8 -*-
##############################################################################
#
# developed by Shilal Software Center 
# Email : shilalgroup@gmail.com
# Phones : +249902605920 
# whatsapp : +249902605920
#    
##############################################################################

{
    'name': 'PDF Reports Creator',
    'description': 'print report that created py the user',
    'summary': """
            Define way to print report that created py the user 
            For employee , contract , contacts , sale order , purchase order
            account invoices , payments , pos price list stock picking and 
            inventory adjustment 
        """,
    'version': '14.0',
    'author': "Shilal",
    'company': 'Shilal Software Center',
    'website': "https://shilalg.blogspot.com",
    'license': 'LGPL-3',
    'price': 50.00,
    'currency': "USD",
    'category': 'Customized Modules',
    'depends': ['mail','hr','hr_contract','account','sale','purchase','stock','point_of_sale'],
    'data': [ 
        'security/ssc_create_report_security.xml',
        'security/ir.model.access.csv',

        'views/ssc_create_report.xml',
        'views/ssc_create_template_view.xml',

        'data/classic_employee_data.xml',
        'data/employee_experience_certificate.xml',
        'data/ar_en_employee_contract.xml',
        'data/en_employee_contract.xml',
        'data/ar_employee_contract.xml',
        'data/employee_id_card_temp_1.xml',
        'data/employee_id_card_temp_2.xml',
        'data/sale_O_Q_temp_1.xml',
        'data/sale_O_Q_temp_2.xml',
        'data/sale_O_Q_temp_3.xml',
        'data/purchase_O_Q_temp_1.xml',
        'data/purchase_O_Q_temp_2.xml',
        'data/purchase_O_Q_temp_3.xml',
        'data/account_invoice_temp_1.xml',
        'data/account_invoice_temp_2.xml',
        'data/account_invoice_temp_3.xml',
        'data/account_invoice_temp_4.xml',
        'data/pos_products_pricelist_temp.xml',
        'data/partner_calssical_temp.xml',
        'data/partner_modern_temp.xml',

        'report/portrait_report_creator_report_view.xml',
        'report/landscape_report_creator_report_view.xml',

        'wizard/ssc_create_report_wiz.xml',

        'menus.xml'
    ],
    'demo': [],
    'images': [
            'static/description/banner.gif'
            ],
    'installable': True,
    'auto_install': True,
    'application': False,
}
