# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class StockMovePicsWizard(models.TransientModel):
    _name = 'sh.stock.move.pics'
    _description = 'Stock Move Quality Measurement Pictures'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    sh_message = fields.Text('Measurement Message', readonly=True)
    sh_quality_point_id = fields.Many2one(
        'sh.qc.point', 'Quality Control Point')
    picking_id = fields.Many2one('stock.picking', 'Picking')
    attachment_ids = fields.Many2many(
        'ir.attachment', string="Upload Pictures")

    @api.model
    def default_get(self, fields):
        res = super(StockMovePicsWizard, self).default_get(fields)
        context = self._context
        stock_move = self.env['stock.move'].sudo().search(
            [('id', '=', context.get('active_id'))], limit=1)
        if stock_move and stock_move.sh_quality_point_id:
            res.update({
                'product_id': stock_move.sh_quality_point_id.product_id.id,
                'sh_quality_point_id': stock_move.sh_quality_point_id.id,
                'sh_message': stock_move.sh_quality_point_id.sh_instruction,
            })
        return res

    def action_pass(self):
        if self.picking_id:
            self.env['sh.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_picking': self.picking_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': 0.0,
                'state': 'pass',
                'qc_type': 'type3',
                'attachment_ids': [(6, 0, self.attachment_ids.ids)]
            })
            if self.attachment_ids:
                if self.picking_id.attachment_ids:
                    self.picking_id.write({'attachment_ids': [
                                          (6, 0, self.picking_id.attachment_ids.ids+self.attachment_ids.ids)]})
                else:

                    self.picking_id.write(
                        {'attachment_ids': [(6, 0, self.attachment_ids.ids)]})

    def action_fail(self):
        context = self._context
        if self.picking_id:
            self.env['sh.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_picking': self.picking_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': 0.0,
                'state': 'fail',
                'qc_type': 'type3',
                'attachment_ids': [(6, 0, self.attachment_ids.ids)]
            })
            if self.attachment_ids:
                if self.picking_id.attachment_ids:
                    self.picking_id.write({'attachment_ids': [
                                          (6, 0, self.picking_id.attachment_ids.ids+self.attachment_ids.ids)]})
                else:

                    self.picking_id.write(
                        {'attachment_ids': [(6, 0, self.attachment_ids.ids)]})
