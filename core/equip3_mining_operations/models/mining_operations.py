from odoo import models, fields, api, _


class MiningOperations(models.Model):
    _name = 'mining.operations'
    _description = 'Mining Operations Management'

    @api.depends('val_jan', 'val_feb', 'val_mar', 'val_apr', 'val_jun', 'val_jul', 'val_aug', 'val_sep', 'val_oct',
                 'val_nov', 'val_dec')
    def _compute_total(self):
        for record in self:
            record.total = sum([record[key] for key in
                                ['val_jan', 'val_feb', 'val_mar', 'val_apr', 'val_jun', 'val_jul', 'val_aug', 'val_sep',
                                 'val_oct', 'val_nov', 'val_dec']])

    @api.depends('plan_id.year')
    def _compute_year(self):
        self.year = self.plan_id.year

    @api.depends('plan_id', 'plan_id.estate_id')
    def _compute_allowed_operations(self):
        for record in self:
            record.allowed_operation_two_ids = [(6, 0, record.plan_id.estate_id.operation_ids.ids)]

    name = fields.Char('Name')
    plan_id = fields.Many2one('mining.budget.planning', string='Budget Planning', required=True,
                              ondelete='cascade')

    year = fields.Char(required=True, compute="_compute_year")

    company_id = fields.Many2one('res.company', related='plan_id.company_id')
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id')
    operation_id = fields.Many2one(comodel_name='mining.operations.two')
    allowed_operation_two_ids = fields.Many2many('mining.operations.two', compute=_compute_allowed_operations)

    val_jan = fields.Monetary(string='January')
    val_feb = fields.Monetary(string='February')
    val_mar = fields.Monetary(string='March')
    val_apr = fields.Monetary(string='April')
    val_may = fields.Monetary(string='May')
    val_jun = fields.Monetary(string='June')
    val_jul = fields.Monetary(string='July')
    val_aug = fields.Monetary(string='August')
    val_sep = fields.Monetary(string='September')
    val_oct = fields.Monetary(string='October')
    val_nov = fields.Monetary(string='November')
    val_dec = fields.Monetary(string='December')

    total = fields.Monetary(string='Total', compute=_compute_total, store=True)
