# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MaintenanceRepairOrderInherit(models.Model):
    _inherit = 'maintenance.repair.order'

    department_ids = fields.Many2many(comodel_name='hr.department', string='Departments')
