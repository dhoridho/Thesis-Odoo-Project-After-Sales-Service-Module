# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models


class PurchaseDocument(models.Model):
    _inherit = 'purchase.order'

    document_count = fields.Integer(
        'Documents', compute='_compute_document_count')

    def _compute_document_count(self):
        if self:
            for rec in self:
                rec.document_count = 0
                doc = self.env['ir.attachment'].search(
                    [('res_id', '=', rec.id), ('res_model', '=', self._name)])
                rec.document_count = len(doc.ids)

    def open_document(self):
        if self:

            document = self.env['ir.attachment'].search(
                [('res_id', '=', self.id), ('res_model', '=', self._name)])

            action = self.env.ref(
                'base.action_attachment').sudo().read()[0]

            action['context'] = {'domain': [('id', 'in', document.ids)], 'search_default_res_id': self.id,
                                 'default_res_id': self.id, 'default_res_model': self._name, }

            action['domain'] = [('id', 'in', document.ids)]

            return action
