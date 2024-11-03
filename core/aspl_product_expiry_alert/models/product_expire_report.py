# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################
from odoo import fields, models, api, _


class ProductExpireReport(models.Model):
    _name = 'product.expire.report'
    _description = 'Product Expire Report'
    
    report_selection = fields.Selection([('product', 'Product'), ('category', 'Category'),
                                         ('warehouse', 'Warehouse'), ('location', 'Location')])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: