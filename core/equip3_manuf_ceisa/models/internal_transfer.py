# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class InternalTransfer(models.Model):
    _inherit = 'internal.transfer'
    _description = 'Internal Transfer'

    # ceisa_id = fields.Integer('CEISA Document ID')

    def action_export_document(self):
        actions = self.env['ir.actions.act_window']._for_xml_id(
            'equip3_manuf_ceisa.action_export_documents_view')
        # actions.update({'context': {'warning_line_ids': warning_line_ids}})
        return actions

    def action_import_document(self):
        actions = self.env['ir.actions.act_window']._for_xml_id(
            'equip3_manuf_ceisa.action_import_documents_view')
        # actions.update({'context': {'warning_line_ids': warning_line_ids}})
        return actions