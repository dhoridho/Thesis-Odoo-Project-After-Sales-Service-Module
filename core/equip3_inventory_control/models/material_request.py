from odoo import _, api, fields, models


class StockWarehouseOrderpoint(models.Model):
    _inherit = "material.request"

    @api.onchange('branch_id')
    def _onchange_analytic_account_group_ids(self):
        if self.branch_id:
            self.analytic_account_group_ids = [
                (6, 0, self.branch_id.analytic_tag_ids.ids)]
        else:
            self.analytic_account_group_ids = [(6, 0, list())]
