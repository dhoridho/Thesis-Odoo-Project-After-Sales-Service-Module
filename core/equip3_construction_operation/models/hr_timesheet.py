from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime


class AccountAnalyticLine(models.Model):
    _inherit = 'account.analytic.line'

    subcon_id = fields.Many2one('res.partner', string="Subcon")
    is_subcon = fields.Boolean(string='Is Subcon')