from odoo import api, fields, models, _

class AccountAnalyticDistribution(models.Model):
    _inherit = 'account.analytic.distribution'
    
    analytic_group_id = fields.Many2one('account.analytic.group',string="Analytic Category", tracking=True)

    def _valid_field_parameter(self, field, name):
        return name == "tracking" or super()._valid_field_parameter(field, name)
