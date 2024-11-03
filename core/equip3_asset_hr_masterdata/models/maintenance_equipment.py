from odoo import models, fields, api, _

class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.equipment'

    @api.onchange('category_id')
    def _onchange_department_id(self):
        self.department_id = self.category_id.department_id.id  