from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, date, timedelta
import pytz
from odoo.exceptions import ValidationError, UserError, Warning, AccessError, AccessDenied, MissingError, RedirectWarning



class Agreement(models.Model):
    _inherit = 'agreement'
    
    invoice_count = fields.Integer(string='Invoices', compute='_compute_invoice_count')
    is_editable = fields.Boolean(string='Is editable', related='stage_id.is_editable', store=True)
    is_new_version = fields.Boolean(string='Is new version', related='stage_id.is_new_version', store=True)
    is_recurring_invoice = fields.Boolean(string='Is recurring invoice', store=True, related='stage_id.is_recurring_invoice')
    is_non_recurring_invoice = fields.Boolean(string='Is non recurring invoice', store=True, related='stage_id.is_non_recurring_invoice')
    recurring_invoice_id = fields.Many2one('agreement.recurring.invoice', string='Recurring Invoice', required=False)
    payment_type = fields.Selection([('daily', 'Daily'), ('monthly', 'Monthly'), ('yearly', 'Yearly')], string='Payment Type')
    end_date = fields.Date(store=True)
    start_date = fields.Date(store=True)
    expired_date = fields.Date(string='Expired Date', compute='_compute_expired_date', store=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', readonly= True)
    invoice_type = fields.Selection([('recurring', 'Recurring'), ('non_recurring', 'Non-Recurring')], string='Invoice Type', default='recurring', required=True)
    next_invoice = fields.Date(string='Next Invoice', required=False)
    partner_email =  fields.Char(string='Partner Email', compute='_compute_partner_email', store=True)
    is_expired = fields.Boolean(string='Is Expired', compute='_compute_is_expired', store=True, readonly=True)
    last_contract = fields.Many2one('agreement', string='Last Contract', store=True)
    agreement_renewal_code = fields.Integer(string='Agreement Renewal', store=True)
    renewal_contract_count = fields.Integer(string='Renewal Contracts', compute='_compute_renewal_contract_count')
    expense_count = fields.Integer(string='Expenses', compute='_compute_expense_count')
    duration_daily = fields.Integer(string='Duration (Days)', default=1)
    duration_monthly = fields.Integer(string='Duration (Months)', default=1)
    duration_yearly = fields.Integer(string='Duration (Years)', default=1)
    
    def _compute_expense_count(self):
        for exp in self:
            exp.expense_count = self.env['agreement.expense.plan'].search_count([('agreement_id', '=', exp.id)])
    
    def expense_link(self):
        return {
        'name': 'Expense Plan',
        'type': 'ir.actions.act_window',
        'view_mode': 'tree,form',
        'res_model': 'agreement.expense.plan',
        'views': [
            (self.env.ref('equip3_contract_operation.agreement_expense_plan_view_tree').id, 'tree'),
            (self.env.ref('equip3_contract_operation.agreement_expense_plan_view_form').id, 'form'),
        ],
        'domain': [('agreement_id', '=', self.id)],
        'context': {'default_agreement_id': self.id}
        }    
    
    @api.depends('agreement_renewal_code')
    def _compute_renewal_contract_count(self):
        for agreement in self:
            if agreement.agreement_renewal_code:
                agreement.renewal_contract_count = self.env['agreement.renewal.line'].search_count([('agreement_renewal_code', '=', agreement.agreement_renewal_code)])
            else:
                agreement.renewal_contract_count = 0
    
    @api.depends('stage_id')
    def _compute_is_expired(self):
        for agreement in self:
            if agreement.stage_id.name == 'Expired':
                agreement.is_expired = True
            else:
                agreement.is_expired = False

    @api.depends('end_date')
    def _compute_expired_date(self):
        self.expired_date = False
        for agreement in self:
            if agreement.end_date:
                agreement.expired_date = agreement.end_date + timedelta(days=1)
            else:
                agreement.expired_date = False

    @api.depends('partner_id', 'notification_address_id')
    def _compute_partner_email(self):
        for agreement in self:
            if agreement.notification_address_id:
                agreement.partner_email = agreement.notification_address_id.email
            else:
                agreement.partner_email = agreement.partner_id.email
    
    @api.depends('stage_id')
    def _compute_is_recurring_invoice(self):
        for agreement in self:
            if agreement.stage_id.is_recurring_invoice == True:
                agreement.is_recurring_invoice = True
    
    def _compute_invoice_count(self):
        for agreement in self:
            agreement.invoice_count = self.env['account.move'].search_count([('agreement_id', '=', agreement.id)])
            
    def invoice_link(self):
        invoices = self.env['account.move'].search([('agreement_id', '=', self.id)])
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) > 1:
            action['domain'] = [('id', 'in', invoices.ids)]
        elif len(invoices) == 1:
            action['views'] = [(self.env.ref('account.view_move_form').id, 'form')]
            action['res_id'] = invoices.ids[0]
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action
    
    @api.onchange('start_date', 'duration_daily', 'duration_monthly', 'duration_yearly')
    def onchange_start_date(self):
        if self.start_date and self.payment_type:
            if self.payment_type == 'daily':
                self.end_date = self.start_date + relativedelta(days=self.duration_daily)
            elif self.payment_type == 'monthly':
                self.end_date = self.start_date + relativedelta(months=self.duration_monthly)
            elif self.payment_type == 'yearly':
                self.end_date = self.start_date + relativedelta(years=self.duration_yearly)
    
    def get_today(self):
        tz = pytz.timezone('Asia/Singapore')
        today = datetime.now(tz).date()
        return today
    
    @api.model
    def create(self, vals):
        res = super(Agreement, self).create(vals)
        return res
    
    def write(self, vals):
        res = super(Agreement, self).write(vals)
        if vals.get('stage_id'):
            id = self.env['agreement.stage'].search([('id', '=', vals.get('stage_id'))])
            if self.invoice_type:
                if id.is_recurring_invoice == True or id.is_non_recurring_invoice == True:
                    if self.line_ids:
                        self.create_self_invoice()
                    else:
                        raise ValidationError(_('Please add agreement product/service line before changing stage to create or recurring invoice.'))
            else:
                raise ValidationError(_('Please select invoice type before changing stage.'))
        return res
    
    def unlink(self):
        for rec in self:
            if rec.renewal_contract_count > 0:
                renewal_line = self.env['agreement.renewal.line'].search([('agreement_renewal_code', '=', rec.agreement_renewal_code)])
                for renewal in renewal_line:
                    if renewal.last_contract.id == rec.id:
                        raise ValidationError(_('You cannot delete this agreement as it is linked to a renewal contract %s.') % (renewal.agreement_id.name))
                    if rec.renewal_contract_count <= 2:
                        renewal.agreement_id.agreement_renewal_code = False
                        renewal.unlink()
        return super(Agreement, self).unlink()
                
        
        
    def fun_create_invoice(self):
        vals_line = []
        for line in self.line_ids:
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
                'name': self.name,
                'account_id': income_account,
                'tax_ids': [(6, 0, line.taxes_id.ids)],
            }))
        in_date = self.start_date
        if self.invoice_type == 'recurring':
            recurring = self.recurring_invoice_id.recurring_type
            if recurring == 'daily':
                freq = self.duration_daily
                in_due_date = self.get_today() + relativedelta(days=freq)
            elif recurring == 'monthly':
                freq = self.duration_monthly
                in_due_date = self.get_today() + relativedelta(months=freq)
            elif recurring == 'yearly':
                freq = self.duration_yearly
                in_due_date = self.get_today() + relativedelta(years=freq)
        else:
            if self.end_date:
                in_due_date = self.end_date
            else:
                in_due_date = self.get_today()
        vals = {
            'agreement_id': self.id,
            'move_type': 'out_invoice',
            'invoice_origin': self.name,
            'partner_id': self.partner_id.id,
            'invoice_date_due': in_due_date,
            'invoice_date': in_date,
            'invoice_user_id': self.create_uid.id,
            'invoice_line_ids': vals_line,
        }
        invoice = self.env['account.move'].create(vals)
        if invoice:
            if self.invoice_type == 'recurring':
                self.next_invoice = in_due_date
                print("Invoice created")
            else:
                self.next_invoice = False
                print("Invoice created")
        else:
            print("Invoice not created")
        
    def create_self_invoice(self):
        if self.invoice_type == 'recurring':
            if self.recurring_invoice_id:
                if self.start_date == False or self.end_date == False:
                    raise ValidationError(_('Please select start date and end date before creating recurring invoice.'))
                if self.start_date <= self.get_today() and self.end_date >= self.get_today():
                    self.fun_create_invoice()
            else:
                raise ValidationError(_('Please select recurring invoice.'))
        elif self.invoice_type == 'non_recurring':
            self.fun_create_invoice()
    
    def create_invoice_agreement(self):
        self.send_email_to_partner()
        agreement = self.env['agreement'].search([('start_date', '!=', False), ('end_date', '!=', False), ('is_template', '=', False)])
        if agreement:
            for agree in agreement:
                end = agree.end_date
                if agree.start_date <= self.get_today() and end >= self.get_today():
                    if agree.recurring_invoice_id:
                        invo = self.env['account.move'].search([('agreement_id', '=', agree.id), ('invoice_date', '=', self.get_today())])
                        if not invo and agree.is_recurring_invoice == True and agree.invoice_type == 'recurring':
                            if agree.start_date == self.get_today() or agree.next_invoice == self.get_today():
                                ag_id = agree.id
                                vals_line = []
                                for line in agree.line_ids:
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
                                        'name': agree.name,
                                        'account_id': income_account,
                                        'tax_ids': [(6, 0, line.taxes_id.ids)],
                                    }))
                                in_date = self.get_today()
                                recurring = agree.recurring_invoice_id.recurring_type
                                if recurring == 'monthly':
                                    freq = agree.recurring_invoice_id.month
                                    in_due_date = self.get_today() + relativedelta(months=freq)
                                elif recurring == 'yearly':
                                    freq = agree.recurring_invoice_id.year
                                    in_due_date = self.get_today() + relativedelta(years=freq)
                                vals = {
                                    'agreement_id': ag_id,
                                    'move_type': 'out_invoice',
                                    'invoice_origin': agree.name,
                                    'partner_id': agree.partner_id.id,
                                    'invoice_date_due': in_due_date,
                                    'invoice_date': in_date,
                                    'invoice_user_id': agree.create_uid.id,
                                    'invoice_line_ids': vals_line,
                                }
                                invoice = agree.env['account.move'].create(vals)
                                if invoice:
                                    agree.invoice_id = invoice.id
                                    agree.next_invoice = in_due_date
                                    print("Invoice created")
                                else:
                                    print("Invoice not created")
                                    
                if agree.end_date < self.get_today():
                    if agree.is_recurring_invoice == True or agree.is_non_recurring_invoice == True:
                        agree.next_invoice = False
                        stage_id = self.env['agreement.stage'].search([('name', '=', 'Expired')])
                        agree.write({'stage_id': stage_id.id})
                        
    def send_email_to_partner(self):
        agreement = self.env['agreement'].search([('stage_id', '!=', False), ('is_template', '=', False)])
        for rec in agreement:
            if rec.is_recurring_invoice == True or rec.is_non_recurring_invoice == True:
                if rec.expiration_notice:
                    exp_notice = rec.end_date - timedelta(days=rec.expiration_notice)
                else:
                    exp_notice = rec.end_date
                if self.get_today() == exp_notice:
                    template = self.env.ref('equip3_contract_operation.expire_contract_reminder_template')
                    values = template.generate_email(rec.id, fields=['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
                    mail_id = self.env['mail.mail']
                    msg = mail_id.sudo().create(values)
                    if msg:
                        msg.sudo().send()
                        
    def renew_contract(self):
        exp = self.stage_id.name
        if exp not in ['Expired']:
            raise ValidationError(_('Renewal is only allowed for expired contracts.'))
        view_id = self.env.ref('equip3_contract_operation.renew_contract_wizard_form').id
        if view_id:
            return {
                'name': _('Renew Contract'),
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'renewal.contract.wizard',
                'view': view_id,
                'target': 'new',
                'context': {'default_agreement_id': self.id, 'default_name': self.name + ' - Renewal'}
            }
    
    def action_renewal_contract(self):
        #return tree view of renewal contract
        view_id = self.env.ref('equip3_contract_operation.agreement_renewal_line_view_tree').id
        if view_id:
            return {
                'name': _('Renewal Contract'),
                'type': 'ir.actions.act_window',
                'view_mode': 'tree',
                'res_model': 'agreement.renewal.line',
                'view_id': self.env.ref('equip3_contract_operation.agreement_renewal_line_view_tree').id,
                'target': 'current',
                'domain': [('agreement_renewal_code', '=', self.agreement_renewal_code)],
            }
        else:
            raise UserError(_('No view found.'))
        
Agreement()

class AgreementRenewalLine(models.Model):
    _name = 'agreement.renewal.line'

    name = fields.Char(string='Name')
    agreement_id = fields.Many2one('agreement', string='Contract')
    agreement_stage_id = fields.Many2one('agreement.stage', string='Contract Stage', related='agreement_id.stage_id')
    agreement_renewal_code = fields.Integer(string='Contract Renewal', related='agreement_id.agreement_renewal_code')
    desc = fields.Text(string='Description')
    last_contract = fields.Many2one('agreement', string='Last Contract', related='agreement_id.last_contract')