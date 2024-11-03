# -*- coding: utf-8 -*-
{
    'name': 'Sales Credit Limit',
    'author': 'Softhealer Technologies',
    'website': 'https://www.softhealer.com',
    'support': 'support@softhealer.com',
    'version': '1.1.1',
    'category': 'Sales',
    'summary': "set client credit limit app, decide customer credit limit, choose user credit limit odoo, sales credit limit module, Sale Order Credit Limit, Sales Order Credit Limit, Quotation Credit Limit, Quote Credit Limit Odoo",
    'description': """A credit limit is the maximum amount of credit offered to a customer. You can set a credit limit for every customer using this module. For example, a manager grants a credit limit of $5,000 to a customer. The credit limit is used to limit the amount of loss that order will on hold if a customer does not pay. you can also notify the customer by email when a customer crosses his credit limit. And that order status will automatically set 'On hold'. This module also provides a different way to notify the customer by email. """,
    'depends': [
        'sale_management',
    ],
    'data': [
        'data/sale_order_partner_credit_limit_group.xml',
        'data/sale_order_partner_credit_limit_template.xml',
        'security/ir.model.access.csv',
        'views/res_partner.xml',
        'views/sale_config_settings.xml',
        'views/sale_order.xml',
        'views/sale_order_onhold.xml',
        'views/sale_customer_credit.xml',
    ],
    'images': ['static/description/background.png', ],
    "license": "OPL-1",
    'auto_install': False,
    'installable': True,
    'application': True,
    'price': 25,
    "currency": "EUR"
}
