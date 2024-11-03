from odoo import models, fields, api


class MrpCostActualization(models.Model):
    _inherit = 'mrp.cost.actualization'

    @api.model
    def _get_svl_types(self):
        return super(MrpCostActualization, self)._get_svl_types() + ['subcontracting']


class MrpCostActualizationLine(models.Model):
    _inherit = 'mrp.cost.actualization.line'

    cost_category = fields.Selection(selection_add=[('subcontracting', 'Subcontracting')])


class MrpCostActualizationValuation(models.Model):
    _inherit = 'mrp.cost.actualization.valuation'

    category = fields.Selection(selection_add=[('subcontracting', 'Subcontracting')])


class MrpCostActualizationProduction(models.Model):
    _inherit = 'mrp.cost.actualization.production'

    total_subcontracting = fields.Monetary(string='Total Subcontracting', copy=False)

    @api.depends('total_material', 'total_overhead', 'total_labor', 'total_subcontracting', 'former_cost')
    def _compute_total(self):
        super(MrpCostActualizationProduction, self)._compute_total()
        for record in self:
            record.total += record.total_subcontracting
            record.new_cost += record.total_subcontracting
