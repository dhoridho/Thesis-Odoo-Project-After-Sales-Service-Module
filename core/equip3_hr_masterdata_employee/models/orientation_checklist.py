from odoo import api, fields, models, _


class HrJob(models.Model):
    _inherit = 'orientation.checklist'
    _description = 'Orientation Checklist'

    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company,
                                 tracking=True)
    branch_id = fields.Many2one("res.branch", string="Branch", domain="[('company_id', '=', company_id)]",
                                tracking=True)
