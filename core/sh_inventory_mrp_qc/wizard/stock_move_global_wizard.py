# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api


class StockMoveQCWizard(models.TransientModel):
    _name = 'sh.stock.move.global.check'
    _description = 'Stock Move Quality Measurement Global check'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    sh_message = fields.Text('Measurement Message', readonly=True)
    sh_quality_point_id = fields.Many2one(
        'sh.qc.point', 'Quality Control Point')
    picking_id = fields.Many2one('stock.picking', 'Picking')
    sh_measure = fields.Float('Measure', default=0.0)
    text_message = fields.Text("Enter QC details..")
    attachment_ids = fields.Many2many(
        'ir.attachment', string="Upload Pictures")
    type = fields.Selection([('type1', 'Pass-Fail'), ('type2', 'Measurement'),
                             ('type3', 'Take a Picture'), ('type4', 'Text')])
    move_id = fields.Many2one('stock.move')

    @api.model
    def default_get(self, fields):
        res = super(StockMoveQCWizard, self).default_get(fields)
        context = self._context
        stock_move = self.env['stock.move'].sudo().search(
            [('id', '=', context.get('default_move_id'))], limit=1)\
            
        quality_point_id = self.env['sh.qc.point'].sudo().search([('product_id', '=', stock_move.product_id.id),
                                                                                  ('operation', '=', stock_move.picking_id.picking_type_id.id),
                                                                  '|', ('team.user_ids.id', 'in', [self.env.uid]), ('team', '=', False)
                                                                  ], limit=1, order='create_date desc')
        
        if quality_point_id:
            res.update({
                'product_id': quality_point_id.product_id.id,
                'sh_quality_point_id': quality_point_id.id,
                'sh_message': quality_point_id.sh_instruction,
                'type': quality_point_id.type,
                'move_id': stock_move.id,
                'picking_id': stock_move.picking_id.id
            })
        return res

    def action_pass(self):
        if self.picking_id:

            if self.type == 'type1':
                self.env['sh.quality.check'].sudo().create({
                    'product_id': self.product_id.id,
                    'sh_picking': self.picking_id.id,
                    'sh_control_point': self.sh_quality_point_id.name,
                    'control_point_id': self.sh_quality_point_id.id,
                    'sh_date': fields.Datetime.now(),
                    'sh_norm': 0.0,
                    'state': 'pass',
                    'qc_type': 'type1'
                })
            elif self.type == 'type3':
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
            elif self.type == 'type4':
                self.env['sh.quality.check'].sudo().create({
                    'product_id': self.product_id.id,
                    'sh_picking': self.picking_id.id,
                    'sh_control_point': self.sh_quality_point_id.name,
                    'control_point_id': self.sh_quality_point_id.id,
                    'sh_date': fields.Datetime.now(),
                    'sh_norm': 0.0,
                    'state': 'pass',
                    'qc_type': 'type4',
                    'text_message': self.text_message
                })

            if self.move_id:
                lines = self.picking_id.move_ids_without_package.filtered(
                    lambda x: x.id != self.move_id.id and x.id > self.move_id.id and x.number_of_test > 0 and x.sh_quality_point == True)
                if len(lines) > 0:
                    return {
                        'name': 'Quality Check',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sh.stock.move.global.check',
                        'context': {'default_move_id': lines[0].id},
                        'target': 'new',
                    }

    def action_next(self):
        if self.move_id and self.picking_id:
            lines = self.picking_id.move_ids_without_package.filtered(
                lambda x: x.id != self.move_id.id and x.id > self.move_id.id and x.number_of_test > 0 and x.sh_quality_point == True)
            if len(lines) > 0:
                return {
                    'name': 'Quality Check',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.stock.move.global.check',
                    'context': {'default_move_id': lines[0].id},
                    'target': 'new',
                }

    def action_validate(self):
        context = self._context
        if self.sh_measure >= self.sh_quality_point_id.sh_unit_from and self.sh_measure <= self.sh_quality_point_id.sh_unit_to:
            self.env['sh.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_picking': self.picking_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': self.sh_measure,
                'state': 'pass',
                'qc_type': 'type2'
            })
            if self.move_id and self.picking_id:
                lines = self.picking_id.move_ids_without_package.filtered(
                    lambda x: x.id != self.move_id.id and x.id > self.move_id.id and x.number_of_test > 0 and x.sh_quality_point == True)
                if len(lines) > 0:
                    return {
                        'name': 'Quality Check',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sh.stock.move.global.check',
                        'context': {'default_move_id': lines[0].id},
                        'target': 'new',
                    }
        else:
            self.env['sh.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_picking': self.picking_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': self.sh_measure,
                'state': 'fail',
                'qc_type': 'type2'
            })
            message = 'You Measured '+str(self.sh_measure)+' mm and it should be between '+str(
                self.sh_quality_point_id.sh_unit_from) + ' and ' + str(self.sh_quality_point_id.sh_unit_to) + ' mm.'
            return {
                'name': 'Quality Checks',
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'sh.correct.qc.measurement',
                'context': {'default_picking_id': self.picking_id.id, 'default_sh_quality_point_id': self.sh_quality_point_id.id, 'default_sh_measure': self.sh_measure, 'default_sh_message': message, 'default_product_id': self.product_id.id, 'default_sh_text': self.sh_message},
                'target': 'new',
            }

    def action_fail(self):
        context = self._context
        if self.picking_id:
            if self.type == 'type1':
                self.env['sh.quality.check'].sudo().create({
                    'product_id': self.product_id.id,
                    'sh_picking': self.picking_id.id,
                    'sh_control_point': self.sh_quality_point_id.name,
                    'control_point_id': self.sh_quality_point_id.id,
                    'sh_date': fields.Datetime.now(),
                    'sh_norm': 0.0,
                    'state': 'fail',
                    'qc_type': 'type1'
                })
            elif self.type == 'type3':
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
                    self.picking_id.write(
                        {'attachment_ids': [(6, 0, self.attachment_ids.ids)]})

            elif self.type == 'type4':
                self.env['sh.quality.check'].sudo().create({
                    'product_id': self.product_id.id,
                    'sh_picking': self.picking_id.id,
                    'sh_control_point': self.sh_quality_point_id.name,
                    'control_point_id': self.sh_quality_point_id.id,
                    'sh_date': fields.Datetime.now(),
                    'sh_norm': 0.0,
                    'state': 'fail',
                    'qc_type': 'type4',
                    'text_message': self.text_message
                })
            if self.move_id:
                lines = self.picking_id.move_ids_without_package.filtered(
                    lambda x: x.id != self.move_id.id and x.id > self.move_id.id and x.number_of_test > 0 and x.sh_quality_point == True)
                if len(lines) > 0:
                    return {
                        'name': 'Quality Check',
                        'type': 'ir.actions.act_window',
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'sh.stock.move.global.check',
                        'context': {'default_move_id': lines[0].id},
                        'target': 'new',
                    }
