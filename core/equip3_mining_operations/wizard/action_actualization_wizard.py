from odoo import models, fields, api, _


class ActionActualizationWizard(models.TransientModel):
    _name = 'action.actualization.wizard'
    _description = 'Action Actualization Wizard'

    @api.depends('mining_prod_line_id')
    def _compute_production_lines(self):
        for record in self:
            prod_line_ids = []
            if record.mining_prod_plan_id:
                prod_line_ids = record.mining_prod_plan_id.operation_ids.mapped('mining_prod_line_id').ids
            record.allowed_mining_prod_line_ids = [(6, 0, prod_line_ids)]

    allowed_mining_prod_line_ids = fields.One2many(comodel_name='mining.production.line', string='Mining Production Lines', compute=_compute_production_lines)
    mining_prod_plan_id = fields.Many2one(comodel_name='mining.production.plan', string='Mining Production Plan', required=True)
    mining_prod_line_id = fields.Many2one(comodel_name='mining.production.line', string='Mining Production Line', domain="[('id', 'in', allowed_mining_prod_line_ids)]", required=True)

    def submit(self):
        self.ensure_one()
        return self.mining_prod_line_id.action_actualization()
