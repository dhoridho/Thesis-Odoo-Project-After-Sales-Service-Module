from odoo import api, fields, models, _

      
class MiningProdPlanOPerations(models.Model):
    _name = 'mining.production.plan.operations'
    _description = 'Production Operation'

    def unlink(self):
        for record in self:
            if record.mining_prod_line_id and record.mining_prod_plan_id:
                record.mining_prod_line_id.write({'mining_prod_plan_id': False})
        return super(MiningProdPlanOPerations, self).unlink()

    @api.depends('mining_prod_plan_id', 'mining_prod_plan_id.mining_site_id')
    def _compute_allowed_operations(self):
        prod_confs = self.env['mining.production.conf'].search([])
        for record in self:
            site_id = False
            if record.mining_prod_plan_id:
                site_id = record.mining_prod_plan_id.mining_site_id
            operation_ids = prod_confs.filtered(lambda p: p.site_id == site_id).mapped('operation_id')
            record.operation_ids = [(6, 0, operation_ids.ids)]
    
    mining_prod_plan_id = fields.Many2one(comodel_name='mining.production.plan', string='Mining Production Plan')
    mining_prod_line_id = fields.Many2one(comodel_name='mining.production.line', string='Reference', domain="[('mining_prod_plan_id', '=', False)]")
    operation_id = fields.Many2one(comodel_name='mining.operations.two', string='Operation', required=True, domain="[('id', 'in', operation_ids)]")
    operation_ids = fields.Many2many(comodel_name='mining.operations.two', string='Allowed Operations', compute=_compute_allowed_operations)
    ppic_id = fields.Many2one('res.users', 'PPIC', default=lambda self: self.env.user, required=True)
    notes = fields.Char(string='Notes')

    @api.onchange('mining_prod_line_id')
    def _onchange_prod_line_id(self):
        if self.mining_prod_line_id:
            self.operation_id = self.mining_prod_line_id.operation_id.id
            self.ppic_id = self.mining_prod_line_id.ppic_id.id
