from odoo import models, fields, api, _

class LandedCost(models.Model):
    _inherit = "stock.landed.cost"

    new_name = fields.Char('New Name')
    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        fields['new_name'] = ", s.new_name as new_name"
        return super(LandedCost, self)._query(with_clause, fields, groupby, from_clause)