# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields


class WorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    sh_mrp_workorder_quality_check_ids = fields.One2many(
        'sh.mrp.quality.check', 'sh_workorder_id', string="Mrp WorkOrder Quality Checks")

    sh_mrp_workorder_quality_alert_ids = fields.One2many(
        'sh.mrp.quality.alert', 'workorder_id', string="Mrp Quality Checks")

    sh_mrp_workorder_pass_fail_ids = fields.One2many(
        'sh.mrp.pass.fail', 'workorder_id', string="Mrp Pass Fail Quality Checks")
    sh_mrp_workorder_pics_ids = fields.One2many(
        'sh.mrp.pics', 'workorder_id', string="Mrp pics Quality Checks")

    sh_mrp_workorder_measurement_ids = fields.One2many(
        'sh.mrp.measurement', 'workorder_id', string="Workorder measurement Quality Checks")
    sh_mrp_workorder_qc_measurement_ids = fields.One2many(
        'sh.mrp.qc.measurement', 'workorder_id', string="Workorder QC measurement Quality Checks")

    qc_count = fields.Integer(
        'Quality Checks', compute='_compute_get_qc_count')
    qc_alert_count = fields.Integer(
        'Quality Alerts', compute='_compute_get_qc_alert_count')

    sh_workorder_quality_point_id = fields.Many2one(
        related='production_id.sh_mrp_quality_point_id', string='Quality Control Point')

    need_qc = fields.Boolean(
        "Need QC", related='production_id.need_qc', store=True)

    pending_qc = fields.Boolean(
        "Pending QC", compute='_compute_check_qc', search='search_workorder_pending_qc')

    qc_fail = fields.Boolean(
        "QC Fail", compute='_compute_check_qc', search='search_workorder_fail_qc')

    qc_pass = fields.Boolean(
        "QC Pass", compute='_compute_check_qc', search='search_workorder_pass_qc')

    attachment_ids = fields.Many2many(
        'ir.attachment', string="QC Pictures", copy=False)

    partner_id = fields.Many2one(
        related='production_id.partner_id', string='Contact')

    is_mandatory = fields.Boolean(
        "QC Mandatory", compute='_compute_check_qc_mandatory')

    def search_workorder_pending_qc(self, operator, value):
        rec_ids = []
        for rec_id in self.search([]):
            if rec_id.pending_qc:
                rec_ids.append(rec_id.id)
        return [('id', 'in', rec_ids)]

    def search_workorder_fail_qc(self, operator, value):
        rec_ids = []
        for rec_id in self.search([]):
            if rec_id.qc_fail:
                rec_ids.append(rec_id.id)
        return [('id', 'in', rec_ids)]

    def search_workorder_pass_qc(self, operator, value):
        rec_ids = []
        for rec_id in self.search([]):
            if rec_id.qc_pass:
                rec_ids.append(rec_id.id)
        return [('id', 'in', rec_ids)]

    def _compute_check_qc(self):
        if self:
            for rec in self:
                rec.qc_pass = False
                rec.qc_fail = False
                rec.pending_qc = False
                if rec.need_qc == True:
                    rec.pending_qc = True

                last_quality_check = self.env['sh.mrp.quality.check'].search(
                    [('product_id', '=', rec.product_id.id), ('sh_workorder_id', '=', rec.id)], limit=1, order='create_date desc')

                if last_quality_check:
                    for qc in last_quality_check:

                        if qc.state == 'fail':

                            rec.qc_fail = True
                            rec.qc_pass = False
                            rec.pending_qc = False

                        if qc.state == 'pass':
                            rec.qc_pass = True
                            rec.qc_fail = False
                            rec.pending_qc = False

    def _compute_check_qc_mandatory(self):
        if self:
            for rec in self:
                rec.is_mandatory = False
                if rec.sh_workorder_quality_point_id and rec.sh_workorder_quality_point_id.is_mandatory:
                    rec.is_mandatory = True

    def workorder_quality_point(self):
        if self.sh_workorder_quality_point_id:

            if len(self.sh_mrp_workorder_quality_check_ids) >= self.sh_workorder_quality_point_id.number_of_test and self.sh_workorder_quality_point_id.number_of_test != 0:

                message = 'You Maximum number of allowed Test is Over Now'

                return {
                    'name': 'NO. of Allowed Quality Checks',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.mrp.allow.qc.measurement',
                    'context': {'default_mrp_id': self.production_id.id, 'default_sh_quality_point_id': self.sh_workorder_quality_point_id.id, 'default_sh_message': message, 'default_product_id': self.product_id.id},
                    'target': 'new',
                }

            if self.sh_workorder_quality_point_id.type == 'type2':
                return {
                    'name': 'Quality Check',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.mrp.measurement',
                    'target': 'new',
                }

            if self.sh_workorder_quality_point_id.type == 'type1':
                return {
                    'name': 'Quality Check',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.mrp.pass.fail',
                    'target': 'new',
                }

            elif self.sh_workorder_quality_point_id.type == 'type3':
                return {
                    'name': 'Quality Check',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.mrp.pics',
                    'target': 'new',
                }

            elif self.sh_workorder_quality_point_id.type == 'type4':
                return {
                    'name': 'Quality Check',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.mrp.text',
                    'target': 'new',
                }

    def action_quality_alert(self):
        line_ids = []
        if self:
            vals = {
                'product_id': self.product_id.id,
                'partner_id': self.partner_id.id,
            }
            line_ids.append((0, 0, vals))
        return {
            'name': 'Quality Alert',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sh.mrp.qc.alert',
            'context': {'default_alert_ids': line_ids},
            'target': 'new',
        }

    def open_quality_check(self):
        po = self.env['sh.mrp.quality.check'].search(
            [('sh_workorder_id', '=', self.id)])
        action = self.env.ref(
            'sh_inventory_mrp_qc.mrp_quality_check_action').read()[0]
        action['context'] = {
            'domain': [('id', 'in', po.ids)]

        }
        action['domain'] = [('id', 'in', po.ids)]
        return action

    def open_quality_alert(self):
        alert_ids = self.env['sh.mrp.quality.alert'].search(
            [('workorder_id', '=', self.id)])
        action = self.env.ref(
            'sh_inventory_mrp_qc.mrp_quality_alert_action').read()[0]
        action['context'] = {
            'domain': [('id', 'in', alert_ids.ids)]
        }
        action['domain'] = [('id', 'in', alert_ids.ids)]
        return action

    def _compute_get_qc_count(self):
        if self:
            for rec in self:
                rec.qc_count = 0
                qc = self.env['sh.mrp.quality.check'].search(
                    [('sh_workorder_id', '=', rec.id)])
                rec.qc_count = len(qc.ids)

    def _compute_get_qc_alert_count(self):
        if self:
            for rec in self:
                rec.qc_alert_count = 0
                qlarts = self.env['sh.mrp.quality.alert'].search(
                    [('workorder_id', '=', rec.id)])
                rec.qc_alert_count = len(qlarts.ids)
