# -*- coding: utf-8 -*-

from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    emenu_outlet_images_ids = fields.Many2many(
        'pos.emenu.outlet.image', 
        'pos_config_pos_emenu_outlet_image_rel', 
        'pos_emenu_outlet_image_id', 
        'pos_category_id', 
        string='Emenu Outlet Images')
    emenu_additional_orders_on_the_cashier_screen = fields.Boolean('Additional orders on the cashier screen')

    def emenu_format_currency(self, amount, currency=None):
        if not currency:
            currency = self.pricelist_id.currency_id
        amount = '{:20,.2f}'.format(amount)
        if (currency.position == 'after'):
            return str(amount) + ' ' + (currency.symbol or '');
        return (currency.symbol or '') + ' ' + str(amount);