from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from datetime import datetime, date
import pytz


class AgreementExpensePlan(models.Model):
    _name = 'agreement.expense.plan'
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = 'Expense Plan'

    name = fields.Char(string='Name', required=True, tracking=True)
    expense_type = fields.Selection([('recurring', 'Recurring'), ('non_recurring', 'Non-Recurring')], string='Expense Type', default='recurring', tracking=True)
    start_date = fields.Date(string='Start Date', required=True, tracking=True)
    end_date = fields.Date(string='End Date, tracking=True')
    recurring_type_id = fields.Many2one('agreement.recurring.expenses', string='Recurring Type', tracking=True)
    agreement_id = fields.Many2one('agreement', string='Contract', domain=[('is_template', '=', False)], required=True, tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('active', 'Active'), ('cancelled', 'Cancelled')], string='State', default='draft', tracking=True)
    invoice_count = fields.Integer(string='Invoices', compute='_compute_invoice_count')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,default=lambda self: self.env.company.currency_id.id)
    line_ids = fields.One2many('agreement.expense.plan.line', 'expense_plan_id', string='Expense Lines')
    amount_untaxed = fields.Monetary(string='Expense Untaxed Amount', store=True, readonly=True, compute='_amount_all_material')
    amount_tax = fields.Monetary(string='Expense Taxes', store=True, readonly=True, compute='_amount_all_material')
    amount_total = fields.Monetary(string='Expense Total', store=True, readonly=True, compute='_amount_all_material')
    next_date = fields.Date(string='Next Date', store=True)
    
    @api.depends('line_ids.price_total')
    def _amount_all_material(self):
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.line_ids:
                line._compute_amount_price()
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': order.currency_id.round(amount_untaxed),
                'amount_tax': order.currency_id.round(amount_tax),
                'amount_total': amount_untaxed + amount_tax,
            })

    def _compute_invoice_count(self):
        for expense in self:
            expense.invoice_count = self.env['account.move'].search_count([('move_type', '=', 'in_invoice'), ('expense_plan_id', '=', expense.id)])
            
    def invoice_link(self):
        invoices = self.env['account.move'].search([('move_type', '=', 'in_invoice'), ('expense_plan_id', '=', self.id)])
        action = self.env.ref('account.action_move_in_invoice_type').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    @api.onchange('start_date')
    def onchange_start_date(self):
        if self.expense_type == 'recurring':
            if self.recurring_type_id:
                if self.recurring_type_id.recurring_type == 'day':
                    self.end_date = self.start_date + relativedelta(days=self.recurring_type_id.recurring_duration)
                if self.recurring_type_id.recurring_type == 'week':
                    self.end_date = self.start_date + relativedelta(days=self.recurring_type_id.recurring_duration * 7)
                if self.recurring_type_id.recurring_type == 'month':
                    self.end_date = self.start_date + relativedelta(months=self.recurring_type_id.recurring_duration)
                if self.recurring_type_id.recurring_type == 'year':
                    self.end_date = self.start_date + relativedelta(years=self.recurring_type_id.recurring_duration)
    
    @api.onchange('recurring_type_id')
    def onchange_recurring_type_id(self):
        if self.start_date:
            if self.recurring_type_id.recurring_type == 'day':
                self.end_date = self.start_date + relativedelta(days=self.recurring_type_id.recurring_duration)
            if self.recurring_type_id.recurring_type == 'week':
                self.end_date = self.start_date + relativedelta(days=self.recurring_type_id.recurring_duration * 7)
            if self.recurring_type_id.recurring_type == 'month':
                self.end_date = self.start_date + relativedelta(months=self.recurring_type_id.recurring_duration)
            if self.recurring_type_id.recurring_type == 'year':
                self.end_date = self.start_date + relativedelta(years=self.recurring_type_id.recurring_duration)
        else:
            if self.recurring_type_id.recurring_type == 'day':
                self.end_date = self.get_today() + relativedelta(days=self.recurring_type_id.recurring_duration)
            if self.recurring_type_id.recurring_type == 'week':
                self.end_date = self.get_today() + relativedelta(days=self.recurring_type_id.recurring_duration * 7)
            if self.recurring_type_id.recurring_type == 'month':
                self.end_date = self.get_today() + relativedelta(months=self.recurring_type_id.recurring_duration)
            if self.recurring_type_id.recurring_type == 'year':
                self.end_date = self.get_today() + relativedelta(years=self.recurring_type_id.recurring_duration)
                
    def get_today(self):
        tz = pytz.timezone('Asia/Singapore')
        today = datetime.now(tz).date()
        return today
    
    def active_expense_plan(self):
        agreement = self.env['agreement'].search([('id', '=', self.agreement_id.id)])
        if agreement.stage_id.name != 'Active':
            raise UserError(_("Contract's state not yet in Active, please activate the contract first."))
        self.state = 'active'
        
    def cancel_expense_plan(self):
        self.state = 'cancelled'
        
    def draft_expense_plan(self):
        self.state = 'draft'
    
    @api.model
    def create(self, vals):
        if vals.get('state') == 'active':
            if vals.get('start_date') <= self.get_today() and vals.get('end_date') >= self.get_today():
                self.create_invoice_line()
        if vals.get('start_date') or vals.get('end_date'):
            if vals.get('start_date') > vals.get('end_date'):
                raise UserError(_('End Date must be greater than Start Date.'))
            if vals.get('agreement_id'):
                agreement = self.env['agreement'].search([('id', '=', vals.get('agreement_id'))])
                start_date = datetime.strptime(vals.get('start_date'), '%Y-%m-%d').date()
                end_date = datetime.strptime(vals.get('end_date'), '%Y-%m-%d').date()
                if start_date < agreement.start_date or end_date > agreement.end_date:
                    raise UserError(_("Start date and End date should be on Contract's Start Date and End Date. Range: %s to %s") % (agreement.start_date, agreement.end_date))
        return super(AgreementExpensePlan, self).create(vals)
    
    def write(self, vals):
        if vals.get('state') == 'active':
            if self.agreement_id:
                if self.start_date <= self.get_today() and self.end_date >= self.get_today():
                    self.create_invoice_line()
            else:
                raise UserError(_('Please select Agreement.'))
        if vals.get('start_date') or vals.get('end_date'):
            if vals.get('agreement_id') or self.agreement_id:
                if vals.get('agreement_id'):
                    agreement = self.env['agreement'].search([('id', '=', vals.get('agreement_id'))])
                else:
                    agreement = self.agreement_id
                start_date = datetime.strptime(vals.get('start_date'), '%Y-%m-%d').date()
                end_date = datetime.strptime(vals.get('end_date'), '%Y-%m-%d').date()
                if start_date < agreement.start_date or end_date > agreement.end_date:
                    raise UserError(_("Start date and End date should be on Contract's Start Date and End Date. Range: %s to %s" % (agreement.start_date, agreement.end_date)))
        return super(AgreementExpensePlan, self).write(vals)
    
    def create_invoice(self):
        expense = self.env['agreement.expense.plan'].search([('state', '=', 'active'), ('start_date', '!=', False), ('end_date', '!=', False), ('expense_type', '=', 'recurring'), ('agreement_id', '!=', False)])
        if expense:
            for exp in expense:
                if exp.start_date <= self.get_today() and exp.end_date >= self.get_today():
                    invo = self.env['account.move'].search([('move_type', '=', 'in_invoice'), ('expense_plan_id', '=', exp.id), ('invoice_date', '=', self.get_today())])
                    if not invo:
                        if exp.start_date == self.get_today() or exp.next_date == self.get_today():
                            self.create_invoice_line(exp.id)                           
    
    def create_invoice_line(self, expense_plan_id=False):
        if expense_plan_id == False:
            expense_plan = self.env['agreement.expense.plan'].browse(self.id)
        else:
            expense_plan = self.env['agreement.expense.plan'].browse(expense_plan_id)
        if expense_plan.agreement_id:
            vals_line = []
            for line in expense_plan.line_ids:
                if line.product_id.property_account_income_id:
                    income_account = line.product_id.property_account_income_id.id
                elif line.product_id.categ_id.property_account_income_categ_id:
                    income_account = line.product_id.categ_id.property_account_income_categ_id.id
                else:
                    raise UserError(_('Please define income '
                                    'account for this product: "%s" (id:%d).')
                                    % (line.product_id.name, line.product_id.id))
                    
                vals_line.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_id': line.uom_id.id,
                    'quantity': line.qty,
                    'price_unit': line.unit_price,
                    'name': expense_plan.name,
                    'account_id': income_account,
                    'tax_ids': [(6, 0, line.taxes_id.ids)],
                }))
            in_date = expense_plan.get_today()
            if expense_plan.expense_type == 'recurring':
                recurring = expense_plan.recurring_type_id.recurring_type
                if recurring == 'day':
                    in_due_date = in_date + relativedelta(days=expense_plan.recurring_type_id.day)
                elif recurring == 'week':
                    in_due_date = in_date + relativedelta(days=expense_plan.recurring_type_id.week * 7)
                elif recurring == 'month':
                    in_due_date = in_date + relativedelta(months=expense_plan.recurring_type_id.month)
                elif recurring == 'year':
                    in_due_date = in_date + relativedelta(years=expense_plan.recurring_type_id.year)
            else:
                in_due_date = expense_plan.end_date
                
            vals = {
                'expense_plan_id': expense_plan.id,
                'move_type': 'in_invoice',
                'invoice_origin': expense_plan.name + ' - ' + expense_plan.agreement_id.name,
                'partner_id': expense_plan.agreement_id.partner_id.id,
                'invoice_date_due': in_due_date,
                'invoice_date': in_date,
                'invoice_user_id': expense_plan.create_uid.id,
                'invoice_line_ids': vals_line,
            }
            invoice = expense_plan.env['account.move'].create(vals)
            if invoice:
                expense_plan.next_date = in_due_date
                print("Invoice created")
            else:
                print("Invoice not created")

class AgreementExpenseLine(models.Model):
    _name = 'agreement.expense.plan.line'
    
    product_id = fields.Many2one("product.product", string="Product", domain=[('is_property', '=', False)])
    name = fields.Char(string="Description", required=True)
    expense_plan_id = fields.Many2one("agreement.expense.plan", string="Agreement", ondelete="cascade")
    qty = fields.Float(string="Quantity", default=1.0)
    uom_id = fields.Many2one("uom.uom", string="Unit of Measure", required=True)
    unit_price = fields.Float(string='Unit Price', digits='Product Price', compute='compute_unit_price')
    taxes_id = fields.Many2many('account.tax', string='Taxes', domain=[('type_tax_use', '=', 'sale')], default=lambda self: self.env.company.account_sale_tax_id)
    price_subtotal = fields.Monetary(compute='_compute_amount_price', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount_price', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount_price', string='Tax', store=True)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,default=lambda self: self.env.company.currency_id.id)

    @api.onchange("product_id")
    def _onchange_product_id(self):
        self.name = self.product_id.name
        self.uom_id = self.product_id.uom_id.id
        
    @api.depends('product_id')
    def compute_unit_price(self):
        for line in self:
            if line.product_id:
                line.unit_price = line.product_id.lst_price
            else:
                line.unit_price = 0.0
                
    @api.depends('qty', 'unit_price', 'taxes_id')
    def _compute_amount_price(self):
        for line in self:
            taxes = line.taxes_id.compute_all(
                line.unit_price,
                line.expense_plan_id.currency_id,
                line.qty,)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })
