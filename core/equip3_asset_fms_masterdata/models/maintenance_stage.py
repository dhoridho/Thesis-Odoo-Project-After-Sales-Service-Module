from odoo import api, fields, models

class MaintenanceStage(models.Model):
    _inherit = 'maintenance.stage'

    @api.model
    def delete_unused_stage(self):
        maintenance_stage = self.env['maintenance.stage'].sudo().search([])
        maintenance_request = self.env['maintenance.request'].sudo().search([('stage_id', 'in', maintenance_stage.ids)])
        set_stage_to_false = [mr.write({'stage_id': False}) for mr in maintenance_request] # set stage_id to False for current existing maintenance request
        delete_stage = [stage.unlink() for stage in maintenance_stage]
