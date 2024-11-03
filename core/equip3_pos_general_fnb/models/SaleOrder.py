# -*- coding: utf-8 -*-

from odoo import models, fields, api

class sale_order(models.Model):
    _inherit = "sale.order"

    reserve_order = fields.Boolean('is Reserve Order')
    reserve_from = fields.Datetime('Reserve From')
    reserve_to = fields.Datetime('Reserve To')
    reserve_no_of_guests = fields.Integer('Reserve no of Guests', default=1)
    reserve_mobile = fields.Char('Reserve Mobile', help='Mobile/Phone of Customer Reserved Order')
    reserve_table_id = fields.Many2one('restaurant.table', 'Reserve Table')

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        context = self._context.copy()
        if context.get('pos_config_id', None):
            config = self.env['pos.config'].browse(context.get('pos_config_id'))
            domain = ['|', '|', ('pos_config_id', '=', config.id), ('pos_config_id', '=', None), ('reserve_order', '=', True)]
        return super().search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)