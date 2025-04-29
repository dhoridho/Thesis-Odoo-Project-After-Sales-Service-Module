# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

{
    'name': 'RMA-Return Merchandise Authorization / Return Orders Management',
    'version': '1.0.2',
    'sequence': 1,
    'category': 'Generic Modules/Sales Management',
    'description':
        """
         odoo app Return Merchandise and Return Orders Management user can return Order, refund, Replacement and repair of return product
        
        Return product in odoo,
        Repair product in odoo,
        Replace product in odoo,
        refund product in odoo,
        return order management in odoo
        odoo Return Orders Management
        odoo Return Merchandise Authorization
        odoo Return Order
Return Merchandise Authorization
Odoo Return Merchandise Authorization
Manage return merchandise authorization 
Odoo manage return merchandise authorization
Return orders management 
Odoo return orders management
Return orders 
Odoo return orders 
Manage return orders 
Odoo manage return orders 
Manage Return orders management 
Manage Odoo return orders management
RETURN ORDERS MANAGEMENT IN ODOO
RMA Module allow to customer to manage return/repair/replace/refund product. 
Odoo RMA Module allow to customer to manage return/repair/replace/refund product. 
RMA Create Return Product shipment , replace product, credit note of return products and repair return product.
Odoo RMA Create Return Product shipment , replace product, credit note of return products and repair return product.
Create rma for return product
Odoo Create rma for return product
Manage return, refund and replace product through rma
Odoo Manage return, refund and replace product through rma
Auto Generate Shipment , Sale Order, Credit Note based on rma action
Odoo Auto Generate Shipment , Sale Order, Credit Note based on rma action
Approve and Reject RMA request with Reject Reason
Odoo Approve and Reject RMA request with Reject Reason
Print RMA Report , team wise Dashboard and rma analysis Pivot View
Odoo Print RMA Report , team wise Dashboard and rma analysis Pivot View
Manage return 
Odoo manage return 
Return management 
Odoo return management 

    """,
    'summary': 'rma odoo app Return Merchandise and Return Orders Management user can return Order, refund, Replacement, and repair-return product, Return Merchandise Authorization, Return orders, return/repair/replace/refund product, Reject RMA request,Odoo return management',
    'depends': ['sale_management','sale_stock','stock_account', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'views/sequence.xml',
        'wizard/rma_reject_reason_view.xml',
        'wizard/replace_product_wizard.xml',
        'wizard/dev_credit_note_wizard.xml',
        'views/dev_rma_rma.xml',
        'report/report_rma.xml',
        'report/report_menu.xml',
        'report/rma_report_views.xml',
        # 'views/crm_team_view.xml',
        'views/stock_picking_view.xml',
        ],
    'demo': [],
    'test': [],
    'css': [],
    'qweb': [],
    'js': [],
    'images': ['images/main_screenshot.png'],
    'installable': True,
    'application': True,
    'auto_install': False,
    
    # author and support Details =============#
    'author': 'DevIntelle Consulting Service Pvt.Ltd',
    'website': 'http://www.devintellecs.com',    
    'maintainer': 'DevIntelle Consulting Service Pvt.Ltd', 
    'support': 'devintelle@gmail.com',
    'price':49.0,
    'currency':'EUR',
    'live_test_url':'https://youtu.be/BxDjiPy_jHo',
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
