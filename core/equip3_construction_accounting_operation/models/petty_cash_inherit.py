from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AccountPettycash(models.Model):
    _inherit = 'account.pettycash'

    project = fields.Many2one ('project.project', string="Project", domain="[('primary_states', '=', 'progress')]")
    budgeting_method = fields.Selection(related='project.budgeting_method', string='Budgeting Method')
    budgeting_period = fields.Selection(related='project.budgeting_period', string='Budgeting Period')
    cost_sheet = fields.Many2one('job.cost.sheet', string='Cost Sheet')
    job_order = fields.Many2one('project.task', string='Job Order')
    project_budget = fields.Many2one('project.budget', 'Periodical Budget')
    referred_budget_material = fields.Many2one('material.overhead', 'Referred Budget', force_save="1", domain="[('job_sheet_id','=', cost_sheet), ('overhead_catagory','=', 'petty cash')]")
    referred_budget_budget = fields.Many2one('budget.overhead', 'Referred Budget', force_save="1", domain="[('budget_id','=', project_budget), ('overhead_catagory','=', 'petty cash')]")
    is_continue_over_budget = fields.Boolean(string='Is Continue Over Budget', default=False)

    @api.onchange('project')
    def _onchange_project(self):
        for rec in self:
            if rec.project:
                cost = rec.env['job.cost.sheet'].search([('project_id', '=', rec.project.id), ('state', 'not in', ['cancelled', 'reject', 'revised'])])
                if not cost:
                    raise ValidationError("Please in progress the cost sheet first!")
                rec.custodian = rec.project.project_director.id
                rec.branch_id = rec.project.branch_id.id
                rec.analytic_group_ids = rec.project.analytic_idz.ids
                rec.write({'cost_sheet': cost})

    @api.onchange('referred_budget_budget')
    def _onchange_budget(self):
        for res in self:
            if res.referred_budget_budget:
                res.referred_budget_material = res.referred_budget_budget.cs_overhead_id.id
            
    def send_bd_data(self, res_qty, res_amt):
        return{
            'qty_res': res_qty,
            'amt_res': res_amt
        }
    
    def send_cs_data(self, res_qty, res_amt):
        return{
            'reserved_qty': res_qty,
            'reserved_amt': res_amt
        }
    
    def reserve_cs_amount(self):
        quantity = (self.amount / self.referred_budget_material.overhead_amount_total) * self.referred_budget_material.product_qty
        res_qty = self.referred_budget_material.reserved_qty + quantity
        res_amt = self.referred_budget_material.reserved_amt + self.amount
        for bud in self.cost_sheet:
            bud.material_overhead_ids = [(1, self.referred_budget_material.id, self.send_cs_data(res_qty, res_amt))]
    
    def reserve_bd_amount(self):
        quantity = (self.amount / self.referred_budget_budget.amount_total) * self.referred_budget_budget.quantity
        res_qty = self.referred_budget_budget.qty_res + quantity
        res_amt = self.referred_budget_budget.amt_res + self.amount
        
        for bud in self.project_budget:
            bud.budget_overhead_ids = [(1, self.referred_budget_budget.id, self.send_bd_data(res_qty, res_amt))]

        for cos in self.cost_sheet:
            cos.material_overhead_ids = [(1, self.referred_budget_material.id, self.send_cs_data(res_qty, res_amt))]

    def validate(self):
        if self.budgeting_method == 'product_budget':
            if self.project_budget:
                if self.amount > self.referred_budget_budget.amt_left and not self.is_continue_over_budget:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.referred_budget_budget.amt_left * (self.cost_sheet.ratio_value / 100)) + self.referred_budget_budget.amt_left
                        if self.amount > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % (self.referred_budget_budget.name, over_budget_limit)))
                    return {
                        'name': _('Warning'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'petty.cash.over.budget.validation.wizard',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'target': 'new',
                        'context': {
                            'default_petty_cash_id': self.id,
                        }
                    }
                else:
                    self.reserve_bd_amount()
            else:
                if self.amount > self.referred_budget_material.budgeted_amt_left and not self.is_continue_over_budget:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.referred_budget_material.budgeted_amt_left * (self.cost_sheet.ratio_value / 100)) + self.referred_budget_material.budgeted_amt_left
                        if self.amount > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % (self.referred_budget_budget.name, over_budget_limit)))
                    return {
                        'name': _('Warning'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'petty.cash.over.budget.validation.wizard',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'target': 'new',
                        'context': {
                            'default_petty_cash_id': self.id,
                        }
                    }
                else:
                    self.reserve_cs_amount()
        elif self.budgeting_method == 'gop_budget':
            if self.project_budget:
                if self.amount > self.referred_budget_budget.overhead_gop_id.amt_left and not self.is_continue_over_budget:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.referred_budget_budget.overhead_gop_id.amt_left * (self.cost_sheet.ratio_value / 100)) + self.referred_budget_budget.overhead_gop_id.amt_left
                        if self.amount > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % (self.referred_budget_budget.group_of_product.name, over_budget_limit)))
                    return {
                        'name': _('Warning'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'petty.cash.over.budget.validation.wizard',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'target': 'new',
                        'context': {
                            'default_petty_cash_id': self.id,
                        }
                    }
                else:
                    self.reserve_bd_amount()
                    self.project_budget.get_gop_overhead_table()
                    self.cost_sheet.get_gop_overhead_table()
            else:
                if self.amount > self.referred_budget_material.overhead_gop_id.budgeted_amt_left and not self.is_continue_over_budget:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.referred_budget_material.overhead_gop_id.budgeted_amt_left * (self.cost_sheet.ratio_value / 100)) + self.referred_budget_material.overhead_gop_id.budgeted_amt_left
                        if self.amount > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % (self.referred_budget_budget.group_of_product.name, over_budget_limit)))
                    return {
                        'name': _('Warning'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'petty.cash.over.budget.validation.wizard',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'target': 'new',
                        'context': {
                            'default_petty_cash_id': self.id,
                        }
                    }
                else:
                    self.reserve_cs_amount()
                    self.cost_sheet.get_gop_overhead_table()
        elif self.budgeting_method == 'budget_type':
            if self.project_budget:
                if self.amount > self.project_budget.amount_left_overhead and not self.is_continue_over_budget:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.project_budget.amount_left_overhead * (self.cost_sheet.ratio_value / 100)) + self.project_budget.amount_left_overhead
                        if self.amount > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % ("Overhead", over_budget_limit)))
                    return {
                        'name': _('Warning'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'petty.cash.over.budget.validation.wizard',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'target': 'new',
                        'context': {
                            'default_petty_cash_id': self.id,
                        }
                    }
                else:
                    self.reserve_bd_amount()
            else:
                if self.amount > self.cost_sheet.overhead_budget_left and not self.is_continue_over_budget:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.cost_sheet.overhead_budget_left * (self.cost_sheet.ratio_value / 100)) + self.cost_sheet.overhead_budget_left
                        if self.amount > over_budget_limit:
                            raise ValidationError(
                                _("Limit for '%s' is '%s'" % ("Overhead", over_budget_limit)))
                    return {
                        'name': _('Warning'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'petty.cash.over.budget.validation.wizard',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'target': 'new',
                        'context': {
                            'default_petty_cash_id': self.id,
                        }
                    }
                else:
                    self.reserve_cs_amount()
        elif self.budgeting_method == 'total_budget':
            if self.project_budget:
                if self.amount > self.project_budget.budget_left and not self.is_continue_over_budget:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.project_budget.budget_left * (self.cost_sheet.ratio_value / 100)) + self.project_budget.budget_left
                        if self.amount > over_budget_limit:
                            raise ValidationError(
                                _("Limit for this project is '%s'" % over_budget_limit))
                    return {
                        'name': _('Warning'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'petty.cash.over.budget.validation.wizard',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'target': 'new',
                        'context': {
                            'default_petty_cash_id': self.id,
                        }
                    }
                else:
                    self.reserve_bd_amount()
            else:
                if self.amount > self.cost_sheet.contract_budget_left and not self.is_continue_over_budget:
                    if self.cost_sheet.is_over_budget_ratio:
                        over_budget_limit = (self.cost_sheet.contract_budget_left * (self.cost_sheet.ratio_value / 100)) + self.cost_sheet.contract_budget_left
                        if self.amount > over_budget_limit:
                            raise ValidationError(
                                _("Limit for this project is '%s'" % over_budget_limit))
                    return {
                        'name': _('Warning'),
                        'type': 'ir.actions.act_window',
                        'res_model': 'petty.cash.over.budget.validation.wizard',
                        'view_mode': 'form',
                        'view_type': 'form',
                        'target': 'new',
                        'context': {
                            'default_petty_cash_id': self.id,
                        }
                    }
                else:
                    self.reserve_cs_amount()


        res = super(AccountPettycash, self).validate()

        return res


class AccountPettycashFundReconcile(models.TransientModel):
    _inherit = 'account.pettycash.fund.reconcile'

    def send_bd_data(self, res_qty, res_amt, act_qty, act_amt):
        return{
            'qty_res': res_qty,
            'amt_res': res_amt,
            'purchased_qty': act_qty,
            'purchased_amt': act_amt,
            'qty_used': act_qty,
            'amt_used': act_amt,
        }
   
    def send_cs_data(self, res_qty, res_amt, act_qty, act_amt):
        return{
            'reserved_qty': res_qty,
            'reserved_amt': res_amt,
            'purchased_qty': act_qty,
            'purchased_amt': act_amt,  
            'actual_used_qty': act_qty,
            'actual_used_amt': act_amt
        }
    
    def used_cs_amount(self, petty_cash, amount):
        quantity = (amount / petty_cash.referred_budget_material.overhead_amount_total) * petty_cash.referred_budget_material.product_qty
        act_qty = petty_cash.referred_budget_material.actual_used_qty + quantity
        act_amt = petty_cash.referred_budget_material.actual_used_amt + amount
        res_qty = petty_cash.referred_budget_material.reserved_qty - quantity
        res_amt = petty_cash.referred_budget_material.reserved_amt - amount
        for cos in petty_cash.cost_sheet:
            cos.material_overhead_ids = [(1, petty_cash.referred_budget_material.id, self.send_cs_data(res_qty, res_amt, act_qty, act_amt))]

    def used_bd_amount(self, petty_cash, amount):
        quantity = (amount / petty_cash.referred_budget_budget.amount_total) * petty_cash.referred_budget_budget.quantity
        act_qty = petty_cash.referred_budget_budget.qty_used + quantity
        act_amt = petty_cash.referred_budget_budget.amt_used + amount
        res_qty = petty_cash.referred_budget_budget.qty_res - quantity
        res_amt = petty_cash.referred_budget_budget.amt_res - amount
        for bud in petty_cash.project_budget:
            bud.budget_overhead_ids = [(1, petty_cash.referred_budget_budget.id, self.send_bd_data(res_qty, res_amt, act_qty, act_amt))]

        for cos in petty_cash.cost_sheet:
            cos.material_overhead_ids = [(1, petty_cash.referred_budget_material.id, self.send_cs_data(res_qty, res_amt, act_qty, act_amt))]
    
    def update_used_amount(self, petty_cash, amount):
        if petty_cash.project_budget:
            self.used_bd_amount(petty_cash, amount)
        else:
            self.used_cs_amount(petty_cash, amount)
                
    def reconcile_vouchers(self):
        # PettyCash = self.env['account.pettycash']
        res = super(AccountPettycashFundReconcile, self).reconcile_vouchers()
        petty_cash = self.env['account.pettycash'].browse(self.env.context.get('active_id'))
        amount = 0
        for wiz in self:
            for voucher in wiz.vouchers:
                amount += sum(voucher.voucher_line.mapped('price_total'))
            wiz.update_used_amount(petty_cash, amount)
            if petty_cash.budgeting_method == 'gop_budget':
                petty_cash.cost_sheet.get_gop_overhead_table()
                if petty_cash.project_budget:
                    petty_cash.project_budget.get_gop_overhead_table()
        return res


class ReplenishWizardInherit(models.TransientModel):
    _inherit = 'replenish.wizard'

    
    def send_bd_data(self, res_qty, res_amt):
        return{
            'qty_res': res_qty,
            'amt_res': res_amt
        }
    
    def send_cs_data(self, res_qty, res_amt):
        return{
            'reserved_qty': res_qty,
            'reserved_amt': res_amt
        }
    
    def reserve_cs_amount(self, petty_cash):
        quantity = (self.replenish_amount / petty_cash.referred_budget_material.overhead_amount_total) * petty_cash.referred_budget_material.product_qty
        res_qty = petty_cash.referred_budget_material.reserved_qty + quantity
        res_amt = petty_cash.referred_budget_material.reserved_amt + self.replenish_amount
        for bud in petty_cash.cost_sheet:
            bud.material_overhead_ids = [(1, petty_cash.referred_budget_material.id, self.send_cs_data(res_qty, res_amt))]
    
    def reserve_bd_amount(self, petty_cash):
        quantity = (self.replenish_amount / petty_cash.referred_budget_budget.amount_total) * petty_cash.referred_budget_budget.quantity
        res_qty = petty_cash.referred_budget_budget.qty_res + quantity
        res_amt = petty_cash.referred_budget_budget.amt_res + self.replenish_amount
        
        for bud in petty_cash.project_budget:
            bud.budget_overhead_ids = [(1, petty_cash.referred_budget_budget.id, self.send_bd_data(res_qty, res_amt))]

        for cos in petty_cash.cost_sheet:
            cos.material_overhead_ids = [(1, petty_cash.referred_budget_material.id, self.send_cs_data(res_qty, res_amt))]
    
    def replenish_fund(self):
        res = super(ReplenishWizardInherit, self).replenish_fund()
        petty_cash = self.env['account.pettycash'].browse(self.env.context.get('active_id'))

        if petty_cash.budgeting_method == 'product_budget':
            if petty_cash.project_budget:
                if self.replenish_amount > petty_cash.referred_budget_budget.amt_left:
                    raise ValidationError(_("The amount is over the remaining budget"))
                else:
                    self.reserve_cs_amount(petty_cash)
                    self.reserve_bd_amount(petty_cash)
            else:
                if self.replenish_amount > petty_cash.referred_budget_material.budgeted_amt_left:
                    raise ValidationError(_("The amount is over the remaining budget"))
                else:
                    self.reserve_cs_amount(petty_cash)
                
        elif petty_cash.budgeting_method == 'gop_budget':
            if petty_cash.project_budget:
                if self.replenish_amount > petty_cash.referred_budget_budget.overhead_gop_id.amt_left:
                    raise ValidationError(_("The amount is over the remaining budget"))
                else:
                    self.reserve_cs_amount(petty_cash)
                    self.reserve_bd_amount(petty_cash)
            else:
                if self.replenish_amount > petty_cash.referred_budget_material.overhead_gop_id.budgeted_amt_left:
                    raise ValidationError(_("The amount is over the remaining budget"))
                else:
                    self.reserve_cs_amount(petty_cash)

            petty_cash.cost_sheet.get_gop_overhead_table()
            if petty_cash.project_budget:
                petty_cash.project_budget.get_gop_overhead_table()
                
        elif petty_cash.budgeting_method == 'budget_type':
            if petty_cash.project_budget:
                if self.replenish_amount > petty_cash.project_budget.amount_left_overhead:
                    raise ValidationError(_("The amount is over the remaining budget"))
                else:
                    self.reserve_cs_amount(petty_cash)
                    self.reserve_bd_amount(petty_cash)
            else:
                if self.replenish_amount > petty_cash.cost_sheet.overhead_budget_left:
                    raise ValidationError(_("The amount is over the remaining budget"))
                else:
                    self.reserve_cs_amount(petty_cash)
                
        elif petty_cash.budgeting_method == 'total_budget':
            if petty_cash.project_budget:
                if self.replenish_amount > petty_cash.project_budget.budget_left:
                    raise ValidationError(_("The amount is over the remaining budget"))
                else:
                    self.reserve_cs_amount(petty_cash)
                    self.reserve_bd_amount(petty_cash)
            else:
                if self.replenish_amount > petty_cash.cost_sheet.contract_budget_left:
                    raise ValidationError(_("The amount is over the remaining budget"))
                else:
                    self.reserve_cs_amount(petty_cash)
       
        return res
    

class CloseFundWizardInherit(models.TransientModel):
    _inherit = 'account.pettycash.fund.close'

    
    def send_bd_data(self, res_qty, res_amt):
        return{
            'qty_res': res_qty,
            'amt_res': res_amt
        }
    
    def send_cs_data(self, res_qty, res_amt):
        return{
            'reserved_qty': res_qty,
            'reserved_amt': res_amt
        }
    
    def reserve_cs_amount(self, petty_cash):
        quantity = (petty_cash.balance / petty_cash.referred_budget_material.overhead_amount_total) * petty_cash.referred_budget_material.product_qty
        res_qty = petty_cash.referred_budget_material.reserved_qty - quantity
        res_amt = petty_cash.referred_budget_material.reserved_amt - petty_cash.balance
        for bud in petty_cash.cost_sheet:
            bud.material_overhead_ids = [(1, petty_cash.referred_budget_material.id, self.send_cs_data(res_qty, res_amt))]
    
    def reserve_bd_amount(self, petty_cash):
        quantity = (petty_cash.balance / petty_cash.referred_budget_budget.amount_total) * petty_cash.referred_budget_budget.quantity
        res_qty = petty_cash.referred_budget_budget.qty_res - quantity
        res_amt = petty_cash.referred_budget_budget.amt_res - petty_cash.balance
        
        for bud in petty_cash.project_budget:
            bud.budget_overhead_ids = [(1, petty_cash.referred_budget_budget.id, self.send_bd_data(res_qty, res_amt))]

        for cos in petty_cash.cost_sheet:
            cos.material_overhead_ids = [(1, petty_cash.referred_budget_material.id, self.send_cs_data(res_qty, res_amt))]

    def close_fund(self):
        res = super(CloseFundWizardInherit, self).close_fund()
        petty_cash = self.env['account.pettycash'].browse(self.env.context.get('active_id'))
        
        if petty_cash.balance > 0:
            if petty_cash.project_budget:
                self.reserve_bd_amount()
            else:
                self.reserve_cs_amount()

        return res