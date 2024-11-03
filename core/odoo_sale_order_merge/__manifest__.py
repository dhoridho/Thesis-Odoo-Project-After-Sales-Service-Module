# -*- coding: utf-8 -*-

# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Odoo Sales Order Merge',
    'version' : '1.1.2',
    'category' : 'Sales/Sales',
    'license': 'Other proprietary',
    'price' : 39.0,
    'currency' : 'EUR',
    'summary': """This app allow you to merge multiple sale orders.""",
    'description': """
This app allow you to merge multiple sale orders
Allow to select multiple Sale orders and merge
Allow to merge sale order with create new sale order or exsisting sale order
sale order merge
merge sale order
sales order merge
merge order
order merge
order sale merge
sale order line merge
merge sale order line
sales orders merge
merge_sale_order
Merge Sale Order
Merge Sale Orders
sale_order_merge
Merge sale orders


    """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'http://www.probuse.com',
    'support': 'contact@probuse.com',
    'live_test_url': 'https://probuseappdemo.com/probuse_apps/odoo_sale_order_merge/835',#'https://youtu.be/NXwZejq8sIQ',
    'images': [
               'static/description/img1.jpg'
    ],
    'depends' : [
        'sale'
    ],
    'data' : [
        'security/ir.model.access.csv',
        'wizard/merge_order_view.xml',
    ],
    'installable' : True,
    'auto_install' : False

}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
