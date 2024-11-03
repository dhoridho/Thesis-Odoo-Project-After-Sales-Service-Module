# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class StockMoveMeasurementWizard(models.TransientModel):
    _name = 'sh.stock.move.qc.measurement'
    _description = 'Stock Move Measurement'

    product_id = fields.Many2one(
        'product.product', string="Product", readonly=True)
    quality_point_id = fields.Many2one('sh.qc.point', 'Quality Point')
    sh_measure = fields.Float('Measure', default=0.0)
    sh_message = fields.Text('Message', readonly=True)
    picking_id = fields.Many2one("stock.picking", "Picking")

    @api.model
    def default_get(self, fields):
        res = super(StockMoveMeasurementWizard, self).default_get(fields)
        context = self._context
        stock_move = self.env['stock.move'].sudo().search(
            [('id', '=', context.get('active_id'))], limit=1)
        if stock_move and stock_move.sh_quality_point_id:
            res.update({
                'product_id': stock_move.sh_quality_point_id.product_id.id,
                'quality_point_id': stock_move.sh_quality_point_id.id,
                'sh_message': stock_move.sh_quality_point_id.sh_instruction,
            })
        return res

    def action_validate(self):
        context = self._context
        if self.sh_measure >= self.quality_point_id.sh_unit_from and self.sh_measure <= self.quality_point_id.sh_unit_to:
            self.env['sh.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_picking': self.picking_id.id,
                'sh_control_point': self.quality_point_id.name,
                'control_point_id': self.quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': self.sh_measure,
                'state': 'pass',
                'qc_type': 'type2'
            })
        else:
            self.env['sh.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_picking': self.picking_id.id,
                'sh_control_point': self.quality_point_id.name,
                'control_point_id': self.quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': self.sh_measure,
                'state': 'fail',
                'qc_type': 'type2'
            })
            message = 'You Measured '+str(self.sh_measure)+' mm and it should be between '+str(
                self.quality_point_id.sh_unit_from) + ' and ' + str(self.quality_point_id.sh_unit_to) + ' mm.'
            return {
                'name': 'Quality Checks',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.correct.qc.measurement',
                'context': {'global_check': True, 'default_picking_id': self.picking_id.id, 'default_sh_quality_point_id': self.quality_point_id.id, 'default_sh_measure': self.sh_measure, 'default_sh_message': message, 'default_product_id': self.product_id.id, 'default_sh_text': self.sh_message},
                'target': 'new',
            }
