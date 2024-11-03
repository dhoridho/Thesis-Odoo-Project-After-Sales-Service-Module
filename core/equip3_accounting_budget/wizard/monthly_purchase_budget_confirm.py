from odoo import api, fields, models, _

class MonthlyPurchaseBudgetConfirm(models.TransientModel):
    _name = 'monthly.purchase.budget.confirm'
    _description = 'Monthly Budget Purchase Confirm'

    message = fields.Text(string='Message')

    def _compute_message(self):
        for record in self:
            active_id = self.env.context.get('active_id')
            if active_id:
                budget = self.env['monthly.purchase.budget'].browse(active_id)
                if budget:
                    last_budget_period = self.env['monthly.purchase.budget'].search([('budget_purchase_id', '=', budget.budget_purchase_id.id)], order='month_period_id desc', limit=1)
                    is_last_period = budget.id == last_budget_period.id
                    if is_last_period:
                        record.message = "Are you sure you want to mark this budget as done? The remaining amount will be returned to %s." % budget.budget_purchase_id.name
                    else:
                        record.message = "Are you sure you want to mark this budget as done? The remaining amount will be carried over to the next period."

    @api.model
    def default_get(self, fields):
        res = super(MonthlyPurchaseBudgetConfirm, self).default_get(fields)
        active_id = self.env.context.get('active_id')
        if active_id:
            budget = self.env['monthly.purchase.budget'].browse(active_id)
            if budget:
                last_budget_period = self.env['monthly.purchase.budget'].search([('budget_purchase_id', '=', budget.budget_purchase_id.id)], order='month_period_id desc', limit=1)
                is_last_period = budget.id == last_budget_period.id
                if is_last_period:
                    res['message'] = "Are you sure you want to mark this budget as done? The remaining amount will be returned to %s." % budget.budget_purchase_id.name
                else:
                    res['message'] = "Are you sure you want to mark this budget as done? The remaining amount will be carried over to the next period."
        return res
    
    def action_confirm(self):
        active_id = self._context.get('active_id')
        if active_id:
            monthly_budget = self.env['monthly.purchase.budget'].browse(active_id)
            if monthly_budget:
                monthly_budget.action_budget_done()

class MonthlyPurchaseBudgetNextPeriod(models.TransientModel):
    _name = 'monthly.purchase.budget.next.period'
    _description = 'Monthly Budget Purchase End Period'

    message = fields.Text(string='Message', readonly=True)


    def action_confirm(self):
        active_id = self._context.get('active_id')
        if active_id:
            monthly_budget = self.env['monthly.purchase.budget'].browse(active_id)
            if monthly_budget:
                monthly_budget.action_budget_done()

class MonthlyPurchaseBudgetEndPeriod(models.TransientModel):
    _name = 'monthly.purchase.budget.end.period'
    _description = 'Monthly Budget Purchase End Period'

    message = fields.Text(string='Message', readonly=True)


    def action_confirm(self):
        active_id = self._context.get('active_id')
        if active_id:
            monthly_budget = self.env['monthly.purchase.budget'].browse(active_id)
            if monthly_budget:
                monthly_budget.action_budget_done()