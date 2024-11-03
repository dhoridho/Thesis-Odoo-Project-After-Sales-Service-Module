# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MaintenanceWorkOrderInherit(models.Model):
    _inherit = 'maintenance.work.order'

    department_ids = fields.Many2many(comodel_name='hr.department', string='Departments')

    def action_create_repair_order(self):
        res = super(MaintenanceWorkOrderInherit, self).action_create_repair_order()
        repair_order = self.env['maintenance.repair.order'].search([('work_order_id', '=', self.id)])
        if self.department_ids:
            repair_order.write({
                'department_ids': self.department_ids
            })
        return res