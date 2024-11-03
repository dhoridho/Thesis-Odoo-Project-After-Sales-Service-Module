from odoo import models, fields, api, _
from odoo.osv import expression


class MRPCostActualizationValuation(models.Model):
    _inherit = 'mrp.cost.actualization.valuation'

    def _get_svl_line_domain(self):
        domain = super(MRPCostActualizationValuation, self)._get_svl_line_domain()
        domain = expression.AND([domain, [('svl_source_production_id', '=', self.production_id.id)]])
        return domain
