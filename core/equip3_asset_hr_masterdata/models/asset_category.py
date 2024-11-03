# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MaintenanceEquipmentCategoryInherit(models.Model):
    _inherit = 'maintenance.equipment.category'

    department_id = fields.Many2one(comodel_name='hr.department', string='Department')
