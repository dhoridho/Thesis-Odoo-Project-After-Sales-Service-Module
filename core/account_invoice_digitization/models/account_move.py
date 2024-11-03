# -*- coding: utf-8 -*-
from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    enable_digitizer = fields.Boolean(compute='_compute_enable_digitizer')

    @api.depends('move_type')
    def _compute_enable_digitizer(self):
        for record in self:
            accepted_types = ['in_invoice', 'out_invoice', 'out_refund', 'in_refund']
            record.enable_digitizer = record.move_type in accepted_types and record.state == 'draft'

    def _get_create_invoice_from_attachment_decoders(self):
        res = super()._get_create_invoice_from_attachment_decoders()
        res.append((10, self.env['ai.invoice.digitizer'].extract_values_with_ai))
        return res

    def _get_update_invoice_from_attachment_decoders(self, invoice):
        res = super()._get_update_invoice_from_attachment_decoders(invoice)
        res.append((10, self.env['ai.invoice.digitizer'].extract_values_with_ai))
        return res

