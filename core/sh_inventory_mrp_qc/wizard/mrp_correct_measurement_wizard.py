# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields


class CorrectMeasurementWizard(models.TransientModel):
    _name = 'sh.mrp.correct.qc.measurement'
    _description = 'Correct Measurement Wizard'

    product_id = fields.Many2one('product.product', 'Product')
    sh_measure = fields.Float('Measure')
    sh_message = fields.Text("Message", readonly=True)
    sh_text = fields.Text("Measurement Message")
    sh_quality_point_id = fields.Many2one(
        'sh.qc.point', 'Quality Control Point')
    mrp_id = fields.Many2one('mrp.production', 'Manufacturing')
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')

    def action_correct(self):

        if self.workorder_id:
            return {
                'name': 'Quality Check',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.mrp.qc.measurement',
                'context': {'default_workorder_id': self.workorder_id.id, 'default_quality_point_id': self.sh_quality_point_id.id, 'default_sh_measure': self.sh_measure, 'default_sh_message': self.sh_text, 'default_product_id': self.product_id.id},
                'target': 'new',
            }
        else:
            return {
                'name': 'Quality Check',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.mrp.qc.measurement',
                'context': {'default_mrp_id': self.mrp_id.id, 'default_quality_point_id': self.sh_quality_point_id.id, 'default_sh_measure': self.sh_measure, 'default_sh_message': self.sh_text, 'default_product_id': self.product_id.id},
                'target': 'new',
            }

    def action_confirm(self):
        if self.workorder_id:
            self.env['sh.mrp.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_workorder_id': self.workorder_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': self.sh_measure,
                'state': 'fail'
            })
        else:
            self.env['sh.mrp.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_mrp': self.mrp_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': self.sh_measure,
                'state': 'fail'
            })
