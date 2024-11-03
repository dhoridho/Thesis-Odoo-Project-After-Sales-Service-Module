from odoo import models, fields, _


class ReplenishmentHistoryWizard(models.TransientModel):
    _name = 'replenishment.history.wizard'
    _description = 'Replenishment History Wizard'

    html_field = fields.Html(string=' ')
