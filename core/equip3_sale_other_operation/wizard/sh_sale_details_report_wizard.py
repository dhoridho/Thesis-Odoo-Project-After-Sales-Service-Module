from odoo import models, api


class SalesDetailWizard(models.TransientModel):
    _inherit = "sh.sale.details.report.wizard"

    @api.model
    def default_get(self, fields):
        rec = super(SalesDetailWizard, self).default_get(fields)
        search_teams = self.env["crm.team"].search([])
        rec.update({
            "team_ids": [(6, 0, search_teams.ids)],
        })
        return rec
