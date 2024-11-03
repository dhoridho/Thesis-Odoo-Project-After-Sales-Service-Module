# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.
from odoo import models, fields, api


class MrpPicsWizard(models.TransientModel):
    _name = 'sh.mrp.pics'
    _description = 'MRP Quality Measurement Pictures'

    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    sh_message = fields.Text('Measurement Message', readonly=True)
    sh_quality_point_id = fields.Many2one(
        'sh.qc.point', 'Quality Control Point')
    mrp_id = fields.Many2one('mrp.production', 'Manufacturing')
    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')
    attachment_ids = fields.Many2many(
        'ir.attachment', string="Upload Pictures")

    @api.model
    def default_get(self, fields):
        res = super(MrpPicsWizard, self).default_get(fields)
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
            return res

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

    def action_pass(self):
        if self.workorder_id:
            self.env['sh.mrp.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_workorder_id': self.workorder_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': 0.0,
                'state': 'pass',
                'qc_type': 'type3',
                'attachment_ids': [(6, 0, self.attachment_ids.ids)]
            })
            if self.attachment_ids:
                if self.workorder_id.attachment_ids:
                    self.workorder_id.write({'attachment_ids': [
                        (6, 0, self.workorder_id.attachment_ids.ids+self.attachment_ids.ids)]})
                else:

                    self.workorder_id.write(
                        {'attachment_ids': [(6, 0, self.attachment_ids.ids)]})

        if self.mrp_id:

            self.env['sh.mrp.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_mrp': self.mrp_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': 0.0,
                'state': 'pass',
                'qc_type': 'type3',
                'attachment_ids': [(6, 0, self.attachment_ids.ids)]
            })
            if self.attachment_ids:
                if self.mrp_id.attachment_ids:
                    self.mrp_id.write({'attachment_ids': [
                        (6, 0, self.mrp_id.attachment_ids.ids+self.attachment_ids.ids)]})
                else:

                    self.mrp_id.write(
                        {'attachment_ids': [(6, 0, self.attachment_ids.ids)]})

    def action_fail(self):
        if self.workorder_id:
            self.env['sh.mrp.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_workorder_id': self.workorder_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': 0.0,
                'state': 'fail',
                'qc_type': 'type3',
                'attachment_ids': [(6, 0, self.attachment_ids.ids)]
            })
            if self.attachment_ids:
                if self.workorder_id.attachment_ids:
                    self.workorder_id.write({'attachment_ids': [
                        (6, 0, self.workorder_id.attachment_ids.ids+self.attachment_ids.ids)]})
                else:

                    self.workorder_id.write(
                        {'attachment_ids': [(6, 0, self.attachment_ids.ids)]})

        if self.mrp_id:
            self.env['sh.mrp.quality.check'].sudo().create({
                'product_id': self.product_id.id,
                'sh_mrp': self.mrp_id.id,
                'sh_control_point': self.sh_quality_point_id.name,
                'control_point_id': self.sh_quality_point_id.id,
                'sh_date': fields.Datetime.now(),
                'sh_norm': 0.0,
                'state': 'fail',
                'qc_type': 'type3',
                'attachment_ids': [(6, 0, self.attachment_ids.ids)]
            })
            if self.attachment_ids:
                if self.mrp_id.attachment_ids:
                    self.mrp_id.write({'attachment_ids': [
                        (6, 0, self.mrp_id.attachment_ids.ids+self.attachment_ids.ids)]})
                else:

                    self.mrp_id.write(
                        {'attachment_ids': [(6, 0, self.attachment_ids.ids)]})
