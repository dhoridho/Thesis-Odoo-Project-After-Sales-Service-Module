from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
 

class StockLandedCost(models.Model):
    _inherit = "stock.landed.cost"

    def _compute_allowed_mrp_production_ids(self):
        for cost in self:
            latest_production = self.env['mrp.production'].search([
                ('state', '!=', 'cancel'),
                ('company_id', '=', cost.company_id.id),
            ], order='id desc', limit=1)
            self.allowed_mrp_production_ids = latest_production