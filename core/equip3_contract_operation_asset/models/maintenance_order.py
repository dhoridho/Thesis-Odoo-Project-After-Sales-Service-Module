from odoo import models, fields, api, _


class MaintenanceWorkOrder(models.Model):
    _inherit = 'maintenance.work.order'

    agreement_id = fields.Many2one(String='Agreement', comodel_name='agreement', domain="[(is_template, '=', False)]")

class MaintenanceRepairOrder(models.Model):
    _inherit = 'maintenance.repair.order'

    agreement_id = fields.Many2one(String='Agreement', comodel_name='agreement', domain="[(is_template, '=', False)]")
