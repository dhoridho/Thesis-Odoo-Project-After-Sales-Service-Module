from datetime import datetime
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _


class StockScrapRequestInherit(models.Model):
    _inherit = 'stock.scrap.request'

    def action_request_validated(self):
        res = super(StockScrapRequestInherit, self).action_request_validated()
        for rec in self:
            account_moves = rec.env['account.move'].search([('stock_scrap_id', '=', rec.id)])
            for account in account_moves:
                account.analytic_group_ids = self.analytic_tag_ids
                for line in account.line_ids:
                    if line.debit > 0:
                        if rec.project.cip_account_id:
                            line.write({'account_id': rec.project.cip_account_id.id})
        return res
