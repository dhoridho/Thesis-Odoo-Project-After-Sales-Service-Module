# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class MeasurementWizard(models.TransientModel):
    _name = 'sh.qc.measurement'
    _description = "Quality Measurement"

    measurement_ids = fields.One2many(
        'sh.qc.measurement.line', 'measurement_id', string="Measurement Lines")

    @api.model
    def default_get(self, fields):
        res = super(MeasurementWizard, self).default_get(fields)
        context = self._context
        picking_id = self.env['stock.picking'].browse(context.get('active_id'))
        line_ids = []
        if picking_id:
            for line in picking_id.move_ids_without_package:
                quality_point_id = self.env['sh.qc.point'].sudo().search(
                    [('product_id', '=', line.product_id.id), ('operation', '=', picking_id.picking_type_id.id)], limit=1)
                if quality_point_id:
                    vals = {
                        'product_id': quality_point_id.product_id.id,
                        'sh_measure': 0.0,
                        'sh_text': quality_point_id.sh_instruction,
                        'state': 'draft',
                        'quality_point_id': quality_point_id.id,
                        'type': quality_point_id.type,
                    }
                    line_ids.append((0, 0, vals))
        res.update({
            'measurement_ids': line_ids
        })
        return res

    def action_validate(self):
        context = self._context
        picking_id = self.env['stock.picking'].browse(context.get('active_id'))
        if self.measurement_ids:
            for line in self.measurement_ids:
                if line.sh_measure >= line.quality_point_id.sh_unit_from and line.sh_measure <= line.quality_point_id.sh_unit_to:
                    line.state = 'pass'
                    self.env['sh.quality.check'].sudo().create({
                        'product_id': line.product_id.id,
                        'sh_picking': picking_id.id,
                        'sh_control_point': line.quality_point_id.name,
                        'control_point_id': self.quality_point_id.id,
                        'sh_date': fields.Datetime.now(),
                        'sh_norm': line.sh_measure,
                        'state': 'pass'
                    })
                else:
                    self.env['sh.quality.check'].sudo().create({
                        'product_id': line.product_id.id,
                        'sh_picking': picking_id.id,
                        'sh_control_point': line.quality_point_id.name,
                        'control_point_id': self.quality_point_id.id,
                        'sh_date': fields.Datetime.now(),
                        'sh_norm': line.sh_measure,
                        'state': 'fail'
                    })


class MeasurementWizardLine(models.TransientModel):
    _name = 'sh.qc.measurement.line'
    _description = "Quality Measurement Line"

    measurement_id = fields.Many2one('sh.qc.measurement', string="Measurement")
    product_id = fields.Many2one('product.product', 'Product')
    sh_measure = fields.Float('Measure', default=0.0)
    sh_text = fields.Text('Message', readonly=True)
    state = fields.Selection([('draft', 'Draft'), ('pass', 'Pass'),
                              ('fail', 'Fail')], default='draft', string='State')
    quality_point_id = fields.Many2one('sh.qc.point', 'Quality Point')
    type = fields.Selection(
        [('type1', 'Pass Fail'), ('type2', 'Measurement')], string="Type")

    @api.onchange('sh_measure')
    def onchange_state(self):
        if self:
            for rec in self:
                if rec.quality_point_id:
                    if rec.sh_measure >= rec.quality_point_id.sh_unit_from and self.sh_measure <= rec.quality_point_id.sh_unit_to:
                        rec.state = 'pass'
                    else:
                        rec.state = 'fail'
