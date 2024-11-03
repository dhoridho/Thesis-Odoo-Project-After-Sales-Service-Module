from odoo import models, fields


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    is_agri_worker = fields.Boolean()
