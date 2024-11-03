# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class MeasurementWizard(models.TransientModel):
    _name = 'sh.mrp.allow.qc.measurement'
    _description = 'Not Allow For Quality Check'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    sh_message = fields.Text('Measurement Message', readonly=True)
    sh_quality_point_id = fields.Many2one(
        'sh.qc.point', 'Quality Control Point')
    mrp_id = fields.Many2one('mrp.production', 'Manufacturing')

    @api.model
    def default_get(self, fields):
        res = super(MeasurementWizard, self).default_get(fields)
        context = self._context
        mrp = self.env['mrp.production'].sudo().search(
            [('id', '=', context.get('active_id'))], limit=1)

        return res
