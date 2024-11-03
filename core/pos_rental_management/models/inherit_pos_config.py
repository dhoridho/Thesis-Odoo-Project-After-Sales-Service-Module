# -*- coding: utf-8 -*-
#################################################################################
#
#   Copyright (c) 2016-Present Webkul Software Pvt. Ltd. (<https://webkul.com/>)
#   See LICENSE file for full copyright and licensing details.
#   License URL : <https://store.webkul.com/license.html/>
#
#################################################################################

from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = 'pos.config'

    def _default_rental_security_product(self):
        if not self.rental_security_product_id:
            return int(self.env['ir.config_parameter'].get_param('default_rental_security_product_id'))

    partial_payment = fields.Boolean(
        string="Allow Partial Payment", help="Only For Rental Order")
    rental_security_product_id = fields.Many2one('product.product', string="Default Rental Security Product",
                                                 default=_default_rental_security_product)

    @api.model
    def set_rental_product_id(self):
        self = self.sudo()
        for rec in self.search([]):
            if not rec.rental_security_product_id:
                rec.rental_security_product_id = int(
                    self.env['ir.config_parameter'].get_param('default_rental_security_product_id'))
