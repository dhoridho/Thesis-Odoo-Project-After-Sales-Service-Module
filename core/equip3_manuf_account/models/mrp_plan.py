from odoo import models, fields, api


class MrpPlan(models.Model):
    _inherit = 'mrp.plan'

    @api.model
    def _default_analytic_tags(self, context=None, company_id=None, branch_id=None):
        if context is None:
            context = self.env.context
        elif context is False:
            context = dict()

        default = context.get('default_analytic_tag_ids', False)
        if default:
            return default

        user = self.env.user
        # do not apply for False
        if company_id is None:
            company_id = context.get('default_company_id', self.env.company)
        if branch_id is None:
            branch_id = context.get('default_branch_id', self.env.branch if len(self.env.branches) == 1 else self.env['res.branch'])

        if isinstance(company_id, int):
            company_id = self.env['res.company'].browse(company_id)
        if isinstance(branch_id, int):
            branch_id = self.env['res.branch'].browse(branch_id)
        current_company_id = self.env.company.id
        user_analytic_tags = self.env["account.analytic.tag"].search([('company_id', '=', current_company_id)])
        priority = self.env['analytic.priority'].search([], limit=1, order='priority')
        analytic_tags = self.env['account.analytic.tag']  
        if priority.object_id == 'user':
            analytic_tags = user_analytic_tags
        elif priority.object_id == 'branch':
            analytic_tags = branch_id.analytic_tag_ids
        elif priority.object_id == 'product_category':
            product_category = self.env['product.category'].search([('analytic_tag_ids', '!=', False)], limit=1)
            analytic_tags = product_category.analytic_tag_ids
        return [(6, 0, analytic_tags.ids)]


    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytical Group', domain="[('company_id', '=', company_id)]", default=_default_analytic_tags)
    stock_valuation_layer_ids = fields.One2many('stock.valuation.layer', 'mrp_plan_id', string='Valuations', readonly=True)
    estimated_cost_ids = fields.One2many('mrp.estimated.cost', 'plan_id', string='Estimated Cost', readonly=True)

    @api.onchange('company_id', 'branch_id')
    def onchange_company_branch(self):
        super(MrpPlan, self).onchange_company_branch()
        self.analytic_tag_ids = self._default_analytic_tags(context=False, company_id=self.company_id, branch_id=self.branch_id)

    def _get_estimated_cost(self):
        self.ensure_one()
        cost_values = []
        evaluated = self.env['mrp.production']
        for order in self.mrp_order_ids[::-1]:
            if order in evaluated:
                continue
            cost_values += order.bom_id._get_estimated_cost(order.product_id, order.product_qty, order.product_uom_id, self, 'plan_id')
            evaluated |= order.child_ids
        self.estimated_cost_ids = [(5,)] + cost_values
