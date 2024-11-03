# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class MeasurementWizard(models.TransientModel):
    _name = 'sh.mrp.measurement'
    _description = 'MRP Quality Measurement'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    sh_message = fields.Text('Measurement Message', readonly=True)
    sh_quality_point_id = fields.Many2one(
        'sh.qc.point', 'Quality Control Point')
    sh_measure = fields.Float('Measure', default=0.0)
    mrp_id = fields.Many2one('mrp.production', 'Manufacturing')
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')

    @api.model
    def default_get(self, fields):
        res = super(MeasurementWizard, self).default_get(fields)
        context = self._context

        if context.get('active_model') == 'mrp.workorder':
            workorder = self.env['mrp.workorder'].sudo().search(
                [('id', '=', context.get('active_id'))], limit=1)

            if workorder and workorder.sh_workorder_quality_point_id:
                res.update({
                    'product_id': workorder.sh_workorder_quality_point_id.product_id.id,
                    'sh_quality_point_id': workorder.sh_workorder_quality_point_id.id,
                    'sh_message': workorder.sh_workorder_quality_point_id.sh_instruction,
                    'workorder_id': workorder.id
                })

        else:
            mrp = self.env['mrp.production'].sudo().search(
                [('id', '=', context.get('active_id'))], limit=1)

            if mrp and mrp.sh_mrp_quality_point_id:
                res.update({
                    'product_id': mrp.sh_mrp_quality_point_id.product_id.id,
                    'sh_quality_point_id': mrp.sh_mrp_quality_point_id.id,
                    'sh_message': mrp.sh_mrp_quality_point_id.sh_instruction,
                    'mrp_id': mrp.id
                })
        return res

    def action_validate(self):
        context = self._context

        if context.get('active_model') == 'mrp.workorder':
            if self.sh_measure >= self.sh_quality_point_id.sh_unit_from and self.sh_measure <= self.sh_quality_point_id.sh_unit_to:
                self.env['sh.mrp.quality.check'].sudo().create({
                    'product_id': self.product_id.id,
                    'sh_workorder_id': self.workorder_id.id,
                    'sh_control_point': self.sh_quality_point_id.name,
                    'control_point_id': self.sh_quality_point_id.id,
                    'sh_date': fields.Datetime.now(),
                    'sh_norm': self.sh_measure,
                    'state': 'pass',
                    'qc_type': 'type2'
                })
            else:
                self.env['sh.mrp.quality.check'].sudo().create({
                    'product_id': self.product_id.id,
                    'sh_workorder_id': self.workorder_id.id,
                    'sh_control_point': self.sh_quality_point_id.name,
                    'control_point_id': self.sh_quality_point_id.id,
                    'sh_date': fields.Datetime.now(),
                    'sh_norm': self.sh_measure,
                    'state': 'fail',
                    'qc_type': 'type2'
                })
                message = 'You Measured '+str(self.sh_measure)+' mm and it should be between '+str(
                    self.sh_quality_point_id.sh_unit_from) + ' to ' + str(self.sh_quality_point_id.sh_unit_to) + ' mm.'
                return {
                    'name': 'Quality Checks Measurement',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.mrp.correct.qc.measurement',
                    'context': {'global_check': True, 'default_workorder_id': self.workorder_id.id, 'default_sh_quality_point_id': self.sh_quality_point_id.id, 'default_sh_measure': self.sh_measure, 'default_sh_message': message, 'default_product_id': self.product_id.id, 'default_sh_text': self.sh_message},
                    'target': 'new',
                }

        if context.get('active_model') == 'mrp.production':
            if self.sh_measure >= self.sh_quality_point_id.sh_unit_from and self.sh_measure <= self.sh_quality_point_id.sh_unit_to:
                self.env['sh.mrp.quality.check'].sudo().create({
                    'product_id': self.product_id.id,
                    'sh_mrp': self.mrp_id.id,
                    'sh_control_point': self.sh_quality_point_id.name,
                    'control_point_id': self.sh_quality_point_id.id,
                    'sh_date': fields.Datetime.now(),
                    'sh_norm': self.sh_measure,
                    'state': 'pass',
                    'qc_type': 'type2'
                })
            else:
                self.env['sh.mrp.quality.check'].sudo().create({
                    'product_id': self.product_id.id,
                    'sh_mrp': self.mrp_id.id,
                    'sh_control_point': self.sh_quality_point_id.name,
                    'control_point_id': self.sh_quality_point_id.id,
                    'sh_date': fields.Datetime.now(),
                    'sh_norm': self.sh_measure,
                    'state': 'fail',
                    'qc_type': 'type2'
                })
                message = 'You Measured '+str(self.sh_measure)+' mm and it should be between '+str(
                    self.sh_quality_point_id.sh_unit_from) + ' to ' + str(self.sh_quality_point_id.sh_unit_to) + ' mm.'
                return {
                    'name': 'Quality Checks',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.mrp.correct.qc.measurement',
                    'context': {'global_check': True, 'default_mrp_id': self.mrp_id.id, 'default_sh_quality_point_id': self.sh_quality_point_id.id, 'default_sh_measure': self.sh_measure, 'default_sh_message': message, 'default_product_id': self.product_id.id, 'default_sh_text': self.sh_message},
                    'target': 'new',
                }
