# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle
#
##############################################################################

from odoo import models, fields


class ResConfigSettings(models.Model):
    _inherit = 'res.company'

    down_payment_product_id = fields.Many2one('product.product', string='Product')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: