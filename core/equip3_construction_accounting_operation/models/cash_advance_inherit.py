from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class VendorDepositInherit(models.Model):
    _inherit = 'vendor.deposit'

    project_id = fields.Many2one(comodel_name='project.project', string='Project')
    budgeting_method = fields.Selection(related='project_id.budgeting_method', string='Budgeting Method')
    budgeting_period = fields.Selection(related='project_id.budgeting_period', string='Budgeting Period')
    cost_sheet_id = fields.Many2one(comodel_name='job.cost.sheet', string='Cost Sheet')
    project_budget_id = fields.Many2one(comodel_name='project.budget', string='Project Budget')
    job_order = fields.Many2one('project.task', string='Job Order')
    material_overhead_id = fields.Many2one(comodel_name='material.overhead', string='Referred Budget', domain="[('job_sheet_id','=', cost_sheet_id), ('overhead_catagory','=', 'cash advance')]")
    budget_overhead_id = fields.Many2one(comodel_name='budget.overhead', string='Referred Budget', domain="[('budget_id','=', project_budget_id), ('overhead_catagory','=', 'cash advance')]")
    is_continue_over_budget = fields.Boolean(string='Is Continue Over Budget', default=False)

    @api.onchange('project_id')
    def _onchange_project_id(self):
        for rec in self:
            if rec.project_id:
                cost = self.env['job.cost.sheet'].search([('project_id', '=', rec.project_id.id), ('state', 'not in', ['cancelled', 'reject', 'revised'])]).id
                if not cost:
                    raise ValidationError("Please in progress the cost sheet first!")
                rec.cost_sheet_id = cost
                rec.branch_id = rec.project_id.branch_id.id
                rec.employee_id = rec.project_id.project_director.id

    @api.onchange('budget_overhead_id')
    def _onchange_budget(self):
        for res in self:
            if res.budget_overhead_id:
                res.material_overhead_id = res.budget_overhead_id.cs_overhead_id.id
    
    def send_bd_data(self, paid_qty, paid_amt):
        return{
            'purchased_qty': paid_qty,
            'purchased_amt': paid_amt,
        }
    
    def send_cs_data(self, paid_qty, paid_amt):
        return{
            'purchased_qty': paid_qty,
            'purchased_amt': paid_amt,
        }
    
    def reserve_cs_amount(self):
        quantity = (self.amount / self.material_overhead_id.overhead_amount_total) * self.material_overhead_id.product_qty
        paid_qty = self.material_overhead_id.purchased_qty + quantity
        paid_amt = self.material_overhead_id.purchased_amt + self.amount
        for bud in self.cost_sheet_id:
            bud.material_overhead_ids = [(1, self.material_overhead_id.id, self.send_cs_data(paid_qty, paid_amt))]
    
    def reserve_bd_amount(self):
        quantity = (self.amount / self.budget_overhead_id.amount_total) * self.budget_overhead_id.quantity
        paid_qty = self.budget_overhead_id.purchased_qty + quantity
        paid_amt = self.budget_overhead_id.purchased_amt + self.amount
        
        for bud in self.project_budget_id:
            bud.budget_overhead_ids = [(1, self.budget_overhead_id.id, self.send_bd_data(paid_qty, paid_amt))]

        for cos in self.cost_sheet_id:
            cos.material_overhead_ids = [(1, self.material_overhead_id.id, self.send_cs_data(paid_qty, paid_amt))]

    def action_pay_cash_advance(self):
        for record in self:
            if record.budgeting_method == 'product_budget':
                if record.project_budget_id:
                    if record.amount > record.budget_overhead_id.amt_left and not record.is_continue_over_budget:
                        if self.cost_sheet_id.is_over_budget_ratio:
                            over_budget_limit = (record.budget_overhead_id.amt_left * (self.cost_sheet_id.ratio_value / 100)) + record.budget_overhead_id.amt_left
                            if record.amount > over_budget_limit:
                                raise ValidationError(
                                    _("Limit for '%s' is '%s'" % (record.budget_overhead_id.name, over_budget_limit)))
                        return {
                            'name': _('Warning'),
                            'type': 'ir.actions.act_window',
                            'res_model': 'cash.advance.over.budget.validation.wizard',
                            'view_type': 'form',
                            'view_mode': 'form',
                            'target': 'new',
                            'context': {
                                'default_cash_advance_id': record.id,
                            }
                        }
                    else:
                        record.reserve_cs_amount()
                        record.reserve_bd_amount()
                else:
                    if record.amount > record.material_overhead_id.budgeted_amt_left and not record.is_continue_over_budget:
                        if self.cost_sheet_id.is_over_budget_ratio:
                            over_budget_limit = (record.material_overhead_id.budgeted_amt_left * (self.cost_sheet_id.ratio_value / 100)) + record.material_overhead_id.budgeted_amt_left
                            if record.amount > over_budget_limit:
                                raise ValidationError(
                                    _("Limit for '%s' is '%s'" % (record.budget_overhead_id.name, over_budget_limit)))
                        return {
                            'name': _('Warning'),
                            'type': 'ir.actions.act_window',
                            'res_model': 'cash.advance.over.budget.validation.wizard',
                            'view_mode': 'form',
                            'target': 'new',
                            'context': {
                                'default_cash_advance_id': record.id,
                            }
                        }
                    else:
                        record.reserve_cs_amount()
                    
            elif record.budgeting_method == 'gop_budget':
                if record.project_budget_id:
                    if record.amount > record.budget_overhead_id.overhead_gop_id.amt_left and not record.is_continue_over_budget:
                        if self.cost_sheet_id.is_over_budget_ratio:
                            over_budget_limit = (record.budget_overhead_id.overhead_gop_id.amt_left * (self.cost_sheet_id.ratio_value / 100)) + record.budget_overhead_id.overhead_gop_id.amt_left
                            if record.amount > over_budget_limit:
                                raise ValidationError(
                                    _("Limit for '%s' is '%s'" % (record.budget_overhead_id.group_of_product.name, over_budget_limit)))
                        return {
                            'name': _('Warning'),
                            'type': 'ir.actions.act_window',
                            'res_model': 'cash.advance.over.budget.validation.wizard',
                            'view_mode': 'form',
                            'target': 'new',
                            'context': {
                                'default_cash_advance_id': record.id,
                            }
                        }
                    else:
                        record.reserve_cs_amount()
                        record.reserve_bd_amount()

                        record.cost_sheet_id.get_gop_overhead_table()
                        record.project_budget_id.get_gop_overhead_table()
                else:
                    if record.amount > record.material_overhead_id.overhead_gop_id.budgeted_amt_left and not record.is_continue_over_budget:
                        if self.cost_sheet_id.is_over_budget_ratio:
                            over_budget_limit = (record.material_overhead_id.overhead_gop_id.budgeted_amt_left * (self.cost_sheet_id.ratio_value / 100)) + record.material_overhead_id.overhead_gop_id.budgeted_amt_left
                            if record.amount > over_budget_limit:
                                raise ValidationError(
                                    _("Limit for '%s' is '%s'" % (record.budget_overhead_id.group_of_product.name, over_budget_limit)))
                        return {
                            'name': _('Warning'),
                            'type': 'ir.actions.act_window',
                            'res_model': 'cash.advance.over.budget.validation.wizard',
                            'view_mode': 'form',
                            'view_type': 'form',
                            'target': 'new',
                            'context': {
                                'default_cash_advance_id': record.id,
                            }
                        }
                    else:
                        record.reserve_cs_amount()

                        record.cost_sheet_id.get_gop_overhead_table()
                    
            elif record.budgeting_method == 'budget_type':
                if record.project_budget_id:
                    if record.amount > record.project_budget_id.amount_left_overhead and not record.is_continue_over_budget:
                        if self.cost_sheet_id.is_over_budget_ratio:
                            over_budget_limit = (record.project_budget_id.amount_left_overhead * (self.cost_sheet_id.ratio_value / 100)) + record.project_budget_id.amount_left_overhead
                            if record.amount > over_budget_limit:
                                raise ValidationError(
                                    _("Limit for '%s' is '%s'" % ("Overhead", over_budget_limit)))
                        return {
                            'name': _('Warning'),
                            'type': 'ir.actions.act_window',
                            'res_model': 'cash.advance.over.budget.validation.wizard',
                            'view_mode': 'form',
                            'target': 'new',
                            'context': {
                                'default_cash_advance_id': record.id,
                            }
                        }
                    else:
                        record.reserve_cs_amount()
                        record.reserve_bd_amount()
                else:
                    if record.amount > record.cost_sheet_id.overhead_budget_left and not record.is_continue_over_budget:
                        if self.cost_sheet_id.is_over_budget_ratio:
                            over_budget_limit = (record.cost_sheet_id.overhead_budget_left * (self.cost_sheet_id.ratio_value / 100)) + record.cost_sheet_id.overhead_budget_left
                            if record.amount > over_budget_limit:
                                raise ValidationError(
                                    _("Limit for '%s' is '%s'" % ("Overhead", over_budget_limit)))
                        return {
                            'name': _('Warning'),
                            'type': 'ir.actions.act_window',
                            'res_model': 'cash.advance.over.budget.validation.wizard',
                            'view_mode': 'form',
                            'target': 'new',
                            'context': {
                                'default_cash_advance_id': record.id,
                            }
                        }
                    else:
                        record.reserve_cs_amount()
                    
            elif record.budgeting_method == 'total_budget':
                if record.project_budget_id:
                    if record.amount > record.project_budget_id.budget_left and not record.is_continue_over_budget:
                        if self.cost_sheet_id.is_over_budget_ratio:
                            over_budget_limit = (record.project_budget_id.budget_left * (self.cost_sheet_id.ratio_value / 100)) + record.project_budget_id.budget_left
                            if record.amount > over_budget_limit:
                                raise ValidationError(
                                    _("Limit for this project is '%s'" %  over_budget_limit))
                        return {
                            'name': _('Warning'),
                            'type': 'ir.actions.act_window',
                            'res_model': 'cash.advance.over.budget.validation.wizard',
                            'view_mode': 'form',
                            'view_type': 'form',
                            'target': 'new',
                            'context': {
                                'default_cash_advance_id': record.id,
                            }
                        }
                    else:
                        record.reserve_cs_amount()
                        record.reserve_bd_amount()
                else:
                    if record.amount > record.cost_sheet_id.contract_budget_left and not record.is_continue_over_budget:
                        over_budget_limit = (record.cost_sheet_id.contract_budget_left * (self.cost_sheet_id.ratio_value / 100)) + record.cost_sheet_id.contract_budget_left
                        if record.amount > over_budget_limit:
                            raise ValidationError(
                                _("Limit for this project is '%s'" %  over_budget_limit))
                        return {
                            'name': _('Warning'),
                            'type': 'ir.actions.act_window',
                            'res_model': 'cash.advance.over.budget.validation.wizard',
                            'view_mode': 'form',
                            'view_type': 'form',
                            'target': 'new',
                            'context': {
                                'default_cash_advance_id': record.id,
                            }
                        }
                    else:
                        record.reserve_cs_amount()
        res = super(VendorDepositInherit, self).action_pay_cash_advance()
        return res


class ConvertToRevenue(models.TransientModel):
    _inherit = 'convert.revenue'

    def send_bd_data(self, act_qty, act_amt):
        return{
            'qty_used': act_qty,
            'amt_used': act_amt,
        }
   
    def send_cs_data(self, act_qty, act_amt):
        return{  
            'actual_used_qty': act_qty,
            'actual_used_amt': act_amt,
        }
    
    def used_cs_amount(self, cash_advance, amount):
        quantity = (amount / cash_advance.material_overhead_id.overhead_amount_total) * cash_advance.material_overhead_id.product_qty
        act_qty = cash_advance.material_overhead_id.actual_used_qty + quantity
        act_amt = cash_advance.material_overhead_id.actual_used_amt + amount
        for cos in cash_advance.cost_sheet_id:
            cos.material_overhead_ids = [(1, cash_advance.material_overhead_id.id, self.send_cs_data(act_qty, act_amt))]

    def used_bd_amount(self, cash_advance, amount):
        quantity = (amount / cash_advance.budget_overhead_id.amount_total) * cash_advance.budget_overhead_id.quantity
        act_qty = cash_advance.budget_overhead_id.qty_used + quantity
        act_amt = cash_advance.budget_overhead_id.amt_used + amount
        for bud in cash_advance.project_budget_id:
            bud.budget_overhead_ids = [(1, cash_advance.budget_overhead_id.id, self.send_bd_data(act_qty, act_amt))]

        for cos in cash_advance.cost_sheet_id:
            cos.material_overhead_ids = [(1, cash_advance.material_overhead_id.id, self.send_cs_data(act_qty, act_amt))]
    
    def action_confirm(self):

        cash_advance = self.env['vendor.deposit'].browse(self.env.context.get('active_id'))
        amount = cash_advance.remaining_amount

        if cash_advance.project_id:
            if cash_advance.project_budget_id:
                self.used_cs_amount(cash_advance, amount)
                self.used_bd_amount(cash_advance, amount)
            else:
                self.used_cs_amount(cash_advance, amount)

            if cash_advance.budgeting_method == 'gop_budget':
                cash_advance.cost_sheet_id.get_gop_overhead_table()
                if cash_advance.project_budget_id:
                    cash_advance.project_budget_id.get_gop_overhead_table()

        res = super(ConvertToRevenue, self).action_confirm()

        return res


class ReconcileVendorDepositWizard(models.TransientModel):
    _inherit = 'account.vendor.deposit.reconcile'

    def send_bd_data(self, act_qty, act_amt):
        return{
            'qty_used': act_qty,
            'amt_used': act_amt,
        }
   
    def send_cs_data(self, act_qty, act_amt):
        return{  
            'actual_used_qty': act_qty,
            'actual_used_amt': act_amt,
        }
    
    def used_cs_amount(self, cash_advance, amount):
        quantity = (amount / cash_advance.material_overhead_id.overhead_amount_total) * cash_advance.material_overhead_id.product_qty
        act_qty = cash_advance.material_overhead_id.actual_used_qty + quantity
        act_amt = cash_advance.material_overhead_id.actual_used_amt + amount
        for cos in cash_advance.cost_sheet_id:
            cos.material_overhead_ids = [(1, cash_advance.material_overhead_id.id, self.send_cs_data(act_qty, act_amt))]

    def used_bd_amount(self, cash_advance, amount):
        quantity = (amount / cash_advance.budget_overhead_id.amount_total) * cash_advance.budget_overhead_id.quantity
        act_qty = cash_advance.budget_overhead_id.qty_used + quantity
        act_amt = cash_advance.budget_overhead_id.amt_used + amount
        for bud in cash_advance.project_budget_id:
            bud.budget_overhead_ids = [(1, cash_advance.budget_overhead_id.id, self.send_bd_data(act_qty, act_amt))]

        for cos in cash_advance.cost_sheet_id:
            cos.material_overhead_ids = [(1, cash_advance.material_overhead_id.id, self.send_cs_data(act_qty, act_amt))]
    
    def reconcile_deposit(self):
        res = super(ReconcileVendorDepositWizard, self).reconcile_deposit()
        cash_advance = self.env['vendor.deposit'].browse(self.env.context.get('active_id'))
        amount = sum(self.allocation_line_ids.mapped('allocation_amount'))

        if cash_advance.project_id:
            if cash_advance.project_budget_id:
                self.used_bd_amount(cash_advance, amount)
                self.used_cs_amount(cash_advance, amount)
            else:
                self.used_cs_amount(cash_advance, amount)

            if cash_advance.budgeting_method == 'gop_budget':
                cash_advance.cost_sheet_id.get_gop_overhead_table()
                if cash_advance.project_budget_id:
                    cash_advance.project_budget_id.get_gop_overhead_table()

        return res


class ReturnDepositWizard(models.TransientModel):
    _inherit = 'account.deposit.return'

    def send_bd_data(self, paid_qty, paid_amt):
        return{
            'purchased_qty': paid_qty,
            'purchased_amt': paid_amt,
        }
   
    def send_cs_data(self, paid_qty, paid_amt):
        return{
            'purchased_qty': paid_qty,
            'purchased_amt': paid_amt,
        }
    
    def return_cs_amount(self, cash_advance, amount):
        quantity = (amount / cash_advance.material_overhead_id.overhead_amount_total) * cash_advance.material_overhead_id.product_qty
        paid_qty = cash_advance.material_overhead_id.purchased_qty - quantity
        paid_amt = cash_advance.material_overhead_id.purchased_amt - amount
        for cos in cash_advance.cost_sheet_id:
            cos.material_overhead_ids = [(1, cash_advance.material_overhead_id.id, self.send_cs_data(paid_qty, paid_amt))]

    def return_bd_amount(self, cash_advance, amount):
        quantity = (amount / cash_advance.budget_overhead_id.amount_total) * cash_advance.budget_overhead_id.quantity
        paid_qty = cash_advance.budget_overhead_id.purchased_qty - quantity
        paid_amt = cash_advance.budget_overhead_id.purchased_amt - amount
        for bud in cash_advance.project_budget_id:
            bud.budget_overhead_ids = [(1, cash_advance.budget_overhead_id.id, self.send_bd_data(paid_qty, paid_amt))]

        for cos in cash_advance.cost_sheet_id:
            cos.material_overhead_ids = [(1, cash_advance.material_overhead_id.id, self.send_cs_data(paid_qty, paid_amt))]
    
    def return_cash_advance(self):
        res = super(ReturnDepositWizard, self).return_cash_advance()
        cash_advance = self.env['vendor.deposit'].browse(self.env.context.get('active_id'))
        if self.payment_difference_handling == 'reconcile' and self.payment_difference:
            amount = self.payment_difference + self.return_amount
        else:
            amount = self.return_amount
        
        if cash_advance.project_id:
            if cash_advance.project_budget_id:
                self.return_bd_amount(cash_advance, amount)
                self.return_cs_amount(cash_advance, amount)
            else:
                self.return_cs_amount(cash_advance, amount)

            if cash_advance.budgeting_method == 'gop_budget':
                cash_advance.cost_sheet_id.get_gop_overhead_table()
                if cash_advance.project_budget_id:
                    cash_advance.project_budget_id.get_gop_overhead_table()

        return res