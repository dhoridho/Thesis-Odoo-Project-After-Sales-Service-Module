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


class StockQuantity(models.Model):
    _inherit = 'stock.quant'

    state_check = fields.Selection(related='lot_id.state_check', string="state", store=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: