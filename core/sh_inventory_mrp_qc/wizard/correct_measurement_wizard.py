# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields


class CorrectMeasurementWizard(models.TransientModel):
    _name = 'sh.correct.qc.measurement'
    _description = 'Correct Measurement Wizard'

    product_id = fields.Many2one('product.product', 'Product')
    sh_measure = fields.Float('Measure')
    sh_message = fields.Text("Message", readonly=True)
    sh_text = fields.Text("Measurement Message")
    sh_quality_point_id = fields.Many2one(
        'sh.qc.point', 'Quality Control Point')
    picking_id = fields.Many2one('stock.picking', 'Picking')

    def action_correct(self):
        return {
            'name': 'Quality Check',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sh.stock.move.qc.measurement',
            'context': {'default_picking_id': self.picking_id.id, 'default_quality_point_id': self.sh_quality_point_id.id, 'default_sh_measure': self.sh_measure, 'default_sh_message': self.sh_text, 'default_product_id': self.product_id.id},
            'target': 'new',
        }

    def action_confirm(self):
        self.env['sh.quality.check'].sudo().create({
            'product_id': self.product_id.id,
            'sh_picking': self.picking_id.id,
            'sh_control_point': self.sh_quality_point_id.name,
            'control_point_id': self.sh_quality_point_id.id,
            'sh_date': fields.Datetime.now(),
            'sh_norm': self.sh_measure,
            'state': 'fail'
        })
