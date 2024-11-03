# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    _description = 'Stock Picking'

    exim_document_id = fields.Many2one('ceisa.documents', string='Exim Documents')
    exim_document_count = fields.Integer('Number of Exim Documents', compute="_compute_exim_documents_count")

    @api.depends('exim_document_id')
    def _compute_exim_documents_count(self):
        for exim in self:
            exim.exim_document_count = len(exim.exim_document_id)

    def action_export_document(self):
        ceisa_value = []
        seq_date = None
        ceisa_sequence = self.env['ir.sequence'].next_by_code('ceisa.documents', sequence_date=seq_date) or _('New')
        ceisa_value.append({
            'name': ceisa_sequence,
            'type': 'export',
        })
        actions = self.env['ir.actions.act_window']._for_xml_id(
            'equip3_manuf_ceisa.action_export_documents_view')
        # actions.update({'context': {'warning_line_ids': warning_line_ids}})
        # actions.update({
        #     'domain': [('id', 'in', self.exim_document_ids.ids)],
        #     'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
        # })
        actions.update({
            'domain': [('id', 'in', self.exim_document_id.id)]
        })
        return actions

    def action_import_document(self):
        ceisa_value = []
        seq_date = None
        ceisa_sequence = self.env['ir.sequence'].next_by_code('ceisa.documents', sequence_date=seq_date) or _('New')
        ceisa_value.append({
            'name': ceisa_sequence,
            'type': 'import',
        })
        actions = self.env['ir.actions.act_window']._for_xml_id(
            'equip3_manuf_ceisa.action_import_documents_view')
        # actions.update({'context': {'warning_line_ids': warning_line_ids}})
        # actions.update({
        #     'domain': [('id', 'in', self.exim_document_ids.ids)],
        #     'views': [(tree_view_ref.id, 'tree'), (form_view_ref.id, 'form')],
        # })
        actions.update({
            'domain': [('id', 'in', self.exim_document_id.id)]
        })
        return actions

    def action_view_export_document(self):
        print('View Exim Documents')