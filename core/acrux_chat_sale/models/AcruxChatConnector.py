# -*- coding: utf-8 -*-

from odoo import models, fields


class AcruxChatConnector(models.Model):
    _inherit = 'acrux.chat.connector'

    sale_report_id = fields.Many2one('ir.actions.report', string='Sale Report', required=True,
                                     default=lambda self: self.env.ref('sale.action_report_saleorder'),
                                     domain=[('model', '=', 'sale.order')])
