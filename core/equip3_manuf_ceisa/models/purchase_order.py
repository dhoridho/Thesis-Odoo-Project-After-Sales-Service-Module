# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'purchase.order'
    _description = 'Purchase Order'

    # ceisa_id = fields.Integer('CEISA Document ID')

    def action_import_document(self):
        actions = self.env['ir.actions.act_window']._for_xml_id(
            'equip3_manuf_ceisa.action_import_documents_view')
        # actions.update({'context': {'warning_line_ids': warning_line_ids}})
        return actions