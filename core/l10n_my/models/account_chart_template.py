from odoo import models, fields, api, _


class AccountChartTemplate(models.Model):
    _inherit = 'account.chart.template'

    # TODO: Might need to add this field to its corresponding view
    country_id = fields.Many2one('res.country', string='Country', )
