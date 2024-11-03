# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class InternalTransfer(models.Model):
    _inherit = 'internal.transfer'
    _description = 'Internal Transfer'

    # ceisa_id = fields.Integer('CEISA Document ID')
    bc23_document_id = fields.Many2one('ceisa.documents.bc23')
    bc25_document_id = fields.Many2one('ceisa.documents.bc25')
    bc27_document_id = fields.Many2one('ceisa.documents.bc27')
    bc261_document_id = fields.Many2one('ceisa.documents.bc261')
    bc262_document_id = fields.Many2one('ceisa.documents.bc262')
    bc40_document_id = fields.Many2one('ceisa.documents.bc40')
    bc41_document_id = fields.Many2one('ceisa.documents.bc41')
    transfer_out_count = fields.Integer('Transfer Out Count', compute="_compute_transfer_out_documents_count")
    transfer_in_count = fields.Integer('Transfer In Count', compute="_compute_transfer_in_documents_count")


    @api.depends('bc23_document_id', 'bc40_document_id', 'bc262_document_id')
    def _compute_transfer_in_documents_count(self):
        for exim in self:
            if not exim.bc23_document_id and not exim.bc40_document_id and not exim.bc262_document_id:
                transfer_in = 0
            else:
                transfer_in = 1
            exim.transfer_in_count = transfer_in

    @api.depends('bc25_document_id', 'bc27_document_id', 'bc261_document_id', 'bc41_document_id')
    def _compute_transfer_out_documents_count(self):
        for exim in self:
            if not exim.bc25_document_id and not exim.bc27_document_id and not exim.bc261_document_id and not exim.bc41_document_id:
                transfer_out = 0
            else:
                transfer_out = 1
            exim.transfer_out_count = transfer_out


    def action_internal_transfer_documents(self):
        return {
            'name': 'Add New Transfer Document Wizard',
            'type': 'ir.actions.act_window',
            'res_model': 'ceisa.transfer.documents.wizard',
            'view_id': False,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }

    def action_view_transfer_out_document(self):
        if self.bc25_document_id:
            search_picking_document = self.env['ceisa.documents.bc25'].search([('internal_transfer_id', '=', self.id)], limit=1)
        elif self.bc27_document_id:
            search_picking_document = self.env['ceisa.documents.bc27'].search([('internal_transfer_id', '=', self.id)], limit=1)
        elif self.bc261_document_id:
            search_picking_document = self.env['ceisa.documents.bc261'].search([('internal_transfer_id', '=', self.id)], limit=1)
        elif self.bc41_document_id:
            search_picking_document = self.env['ceisa.documents.bc41'].search([('internal_transfer_id', '=', self.id)], limit=1)

        if search_picking_document:
            ceisa_id = search_picking_document
        else:
            raise UserError('Cannot open the Documents.')

        if self.bc25_document_id:
            actions = self.env['ir.actions.act_window']._for_xml_id(
                'equip3_manuf_it_inventory.action_documents_bc25_view')
        elif self.bc27_document_id:
            actions = self.env['ir.actions.act_window']._for_xml_id(
                'equip3_manuf_it_inventory.action_documents_bc27_view')
        elif self.bc261_document_id:
            actions = self.env['ir.actions.act_window']._for_xml_id(
                'equip3_manuf_it_inventory.action_documents_bc261_view')
        elif self.bc41_document_id:
            actions = self.env['ir.actions.act_window']._for_xml_id(
                'equip3_manuf_it_inventory.action_documents_bc41_view')

        actions.update({
            'context': {'default_internal_transfer_id': self.id},
            'res_id': ceisa_id.id,
        })
        return actions

    def action_view_transfer_in_document(self):
        if self.bc23_document_id:
            search_picking_document = self.env['ceisa.documents.bc23'].search([('internal_transfer_id', '=', self.id)], limit=1)
        if self.bc40_document_id:
            search_picking_document = self.env['ceisa.documents.bc40'].search([('internal_transfer_id', '=', self.id)], limit=1)
        elif self.bc262_document_id:
            search_picking_document = self.env['ceisa.documents.bc262'].search([('internal_transfer_id', '=', self.id)], limit=1)

        if search_picking_document:
            ceisa_id = search_picking_document
        else:
            raise UserError('Cannot open the Documents.')

        if self.bc23_document_id:
            actions = self.env['ir.actions.act_window']._for_xml_id(
                'equip3_manuf_it_inventory.action_documents_bc23_view')
        elif self.bc40_document_id:
            actions = self.env['ir.actions.act_window']._for_xml_id(
                'equip3_manuf_it_inventory.action_documents_bc40_view')
        elif self.bc262_document_id:
            actions = self.env['ir.actions.act_window']._for_xml_id(
                'equip3_manuf_it_inventory.action_documents_bc262_view')
        actions.update({
            'context': {'default_internal_transfer_id': self.id},
            'res_id': ceisa_id.id,
        })
        return actions

