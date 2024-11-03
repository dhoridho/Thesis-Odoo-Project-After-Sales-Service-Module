# -*- coding: utf-8 -*-
from odoo import models, fields, api

import logging

_logger = logging.getLogger()


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    enable_digitizer = fields.Boolean(compute='_compute_enable_digitizer')

    def create_document_from_attachment(self):
        for record in self:
            if record.enable_digitizer:
                invoice = self.env[self.res_model].browse(record.res_id)
                self.env['ai.invoice.digitizer'].extract_values_with_ai(record, invoice)

    @api.depends('res_model', 'res_id')
    def _compute_enable_digitizer(self):
        for record in self:
            record.enable_digitizer = False
            if record.res_model and record.res_id:
                rec = self.env[record.res_model].browse(record.res_id)
                record.enable_digitizer = hasattr(rec, 'enable_digitizer') and rec.enable_digitizer

    def _attachment_format(self, commands=False):
        res_list = super()._attachment_format(commands)
        for attachment in res_list:
            attachment['enable_digitizer'] = self.browse(attachment['id']).enable_digitizer
        return res_list
