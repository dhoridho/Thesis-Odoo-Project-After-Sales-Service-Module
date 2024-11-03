# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, fields, models, tools, SUPERUSER_ID, _
_logger = logging.getLogger(__name__)
class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'
    relation_model_name = fields.Char(compute='_compute_relation_model_name', string="Relation Model Label", store=False)
    @api.model
    def _compute_relation_model_name(self):
        for rec in self:
            if rec.relation:
                rec.relation_model_name = self.env['ir.model'].search([('model','=', rec.relation)],[]).name
            else:
                rec.relation_model_name = ''
    def name_get(self):
        if self._context.get('section'):
            res = []
            for field in self:
                name = '%s [%s]' % (field.field_description, field.name)
                res.append((field.id, name))
            return res
        return super(IrModelFields, self).name_get()
