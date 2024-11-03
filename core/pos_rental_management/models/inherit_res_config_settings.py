# -*- coding: utf-8 -*-

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    rental_security_product_id = fields.Many2one('product.product', string="Default Rental Security Product", domain=[('available_in_pos', '=', True)],
                                                 config_parameter="default_rental_security_product_id")

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        if self.rental_security_product_id:
            configs = self.env['pos.config'].search([])
            for config in configs:
                if config.rental_security_product_id and config.rental_security_product_id.id != self.rental_security_product_id.id:
                    config.rental_security_product_id = self.rental_security_product_id
