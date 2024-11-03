from odoo import models, fields, api, _

class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    is_read_only = fields.Boolean('Is Readonly', compute="compute_is_read_only")

    @api.depends('extra_state')
    def compute_is_read_only(self):
        for rec in self:
            if rec.extra_state != 'new':
                rec.is_read_only = True
            else:
                rec.is_read_only = False
