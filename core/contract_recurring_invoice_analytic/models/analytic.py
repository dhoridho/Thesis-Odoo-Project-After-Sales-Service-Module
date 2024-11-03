# -*- coding: utf-8 -*-

import datetime
from datetime import date, timedelta as td
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, tools, _
from odoo.tools.misc import formatLang, format_date
from odoo.exceptions import ValidationError, Warning, UserError


class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'
    
    subscription_product_line_ids = fields.One2many(
        'analytic.sale.order.line',
        'subscription_product_line_id',
        string="Contract Product Lines",
    )
    not_subscription_product_line_ids = fields.One2many(
        'analytic.sale.order.line',
        'not_subscription_product_line_id',
        string="Non-Contract Product Lines",
        readonly = True
    )
    terms_and_conditions = fields.Html(
        string="Terms and Conditions",
    )
    start_date = fields.Date(
        string="Start Date",
    )
    end_date = fields.Date(
        string="End Date",
    )
    recurring_interval = fields.Integer(
        string="Repeat Every",
    )
    recurring_next_date = fields.Date(
        string="Recurring Next Date"
    )
    journal_id = fields.Many2one(
        'account.journal',
        string="Accounting Journal",
        domain="[('type', '=', 'sale')]",
        company_dependent=True,
    )
    invoice_count = fields.Integer(
        compute="_invoice_count",
    )
    number_of_days = fields.Integer(
        string="Contracts Expiration Reminder(Days)",
        default=10,
        store=True,
    )
    contract_lock = fields.Boolean(
        string='Contract Lock',
        readonly = True,
    )
    recurring_rule_type = fields.Selection([
            ('daily', 'Day(s)'),
            ('weekly', 'Week(s)'),
            ('monthly', 'Month(s)'),
            ('yearly', 'Year(s)'), ],
        string='Recurring Period',
    )
    stage = fields.Selection([
        ('draft', 'New'),
        ('inprogress', 'Running'),
        ('to_expired', 'Expires Soon'),
        ('expired', 'Expired'),
        ('lock', 'Locked')], default='draft',
        compute = '_recurring_invoice_stage',
        string="Stage",
        readonly = True,
    )
    sub_amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        store=True,
        readonly=True,
        compute='_subscription_product_amount_all',
        track_visibility='always'
    )
    sub_amount_tax = fields.Monetary(
        string='Taxes',
        store=True,
        readonly=True,
        compute='_subscription_product_amount_all',
        track_visibility='always'
    )
    sub_amount_total = fields.Monetary(
        string='Total',
        store=True,
        readonly=True,
        compute='_subscription_product_amount_all',
        track_visibility='always'
    )
    sale_amount_untaxed = fields.Monetary(
        string='Untaxed Amount',
        store=True,
        readonly=True,
        compute='_sale_order_product_amount_all',
        track_visibility='always'
    )
    sale_amount_tax = fields.Monetary(
        string='Taxes',
        store=True,
        readonly=True,
        compute='_sale_order_product_amount_all',
        track_visibility='always'
    )
    sale_amount_total = fields.Monetary(
        string='Total',
        store=True,
        readonly=True,
        compute='_sale_order_product_amount_all',
        track_visibility='always'
    )
    order_invoice_currency_id = fields.Many2one(
        'res.currency',
        string="Order/Invoice Currency",
        readonly=True,
    )

    def _valid_field_parameter(self, field, name):
        return name == "track_visibility" or super()._valid_field_parameter(field, name)

    def _prepare_cron_recurring_inv_domain(self):
        return [('recurring_next_date','=',fields.date.today()), ('end_date','>=',fields.date.today())]

    @api.model
    def _cron_create_invoice(self):
        contracts = self.search(self._prepare_cron_recurring_inv_domain())
        for contract in contracts:
            try:
                contract.with_context(from_cron=True)._recurring_create_invoice()
            except:
                pass

    #@api.multi
    def button_dummy(self):
        for rec in self:
            pass
        return True

    @api.depends('subscription_product_line_ids.price_total')
    def _subscription_product_amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for rec in self:
            sub_amount_untaxed = sub_amount_tax = 0.0
            for line in rec.subscription_product_line_ids:
                sub_amount_untaxed += line.price_subtotal
                # FORWARDPORT UP TO 10.0
                if rec.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_ids.compute_all(price, line.subscription_product_line_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.subscription_product_line_id.partner_id)
                    sub_amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    sub_amount_tax += line.price_tax
            rec.update({
                'sub_amount_untaxed': rec.company_id.currency_id.round(sub_amount_untaxed),
                'sub_amount_tax': rec.company_id.currency_id.round(sub_amount_tax),
                'sub_amount_total': sub_amount_untaxed + sub_amount_tax,
            })

    @api.depends('not_subscription_product_line_ids.price_total')
    def _sale_order_product_amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for rec in self:
            sale_amount_untaxed = sale_amount_tax = 0.0
            for line in rec.not_subscription_product_line_ids:
                sale_amount_untaxed += line.price_subtotal
                # FORWARDPORT UP TO 10.0
                if rec.company_id.tax_calculation_rounding_method == 'round_globally':
                    price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                    taxes = line.tax_ids.compute_all(price, line.not_subscription_product_line_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.not_subscription_product_line_id.partner_id)
                    sale_amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                else:
                    sale_amount_tax += line.price_tax
            rec.update({
                'sale_amount_untaxed': rec.company_id.currency_id.round(sale_amount_untaxed),
                'sale_amount_tax': rec.company_id.currency_id.round(sale_amount_tax),
                'sale_amount_total': sale_amount_untaxed + sale_amount_tax,
            })

    def tax_ids_str(self, tax_id):
        name_str = ', '.join([i.name for i in tax_id])
        tax_ids = str(name_str)
        return tax_ids

    def analytic_tag_ids_str(self, analytic_tag_id):
        name_str = ', '.join([i.name for i in analytic_tag_id])
        analytic_tag_ids = str(name_str)
        return analytic_tag_ids

    #@api.multi
    def unlock_analytic_account(self):
        self.contract_lock = False

    #@api.multi
    def lock_analytic_account(self):
        self.contract_lock = True

    @api.depends()
    def _recurring_invoice_stage_dummy_old(self):
        for rec in self:
            if rec.contract_lock:
                rec.stage = 'lock'
            elif rec.invoice_count >= 1:
                rec.stage = 'inprogress'
            elif not rec.stage:
                rec.stage = 'draft'
            if not rec.contract_lock:
                if rec.end_date:
                    to_daydate = datetime.datetime.strptime(str(rec.end_date), "%Y-%m-%d")#31 Sept 2017
                    new_date = to_daydate + datetime.timedelta(days=rec.number_of_days)#31 Sept + 10 = 10 Oct
                    delta = new_date - to_daydate # 10 Days
                    for i in range(delta.days + 1):
                        date_entry = to_daydate + td(days=i) #31 Sept 2017 + 1,2,3,4,5,...11
                        if rec.recurring_next_date == datetime.date.strftime(date_entry, "%Y-%m-%d"):
                            rec.stage = 'to_expired'
                    for i in range(delta.days):
                        date_entry = to_daydate - td(days=i) #31 Sept 2017 - 10
                        if rec.recurring_next_date == datetime.date.strftime(date_entry, "%Y-%m-%d"):
                            rec.stage = 'expired'

    @api.depends()
    def _recurring_invoice_stage(self):
        for rec in self:
            rec.stage = 'draft'
            if rec.contract_lock:
                rec.stage = 'lock'
            elif rec.invoice_count >= 1:
                rec.stage = 'inprogress'
            if not rec.contract_lock:
                if rec.end_date:
                    today = fields.Date.today()
                    to_daydate = datetime.datetime.strptime(str(rec.end_date), "%Y-%m-%d")
                    reminder_date = to_daydate - datetime.timedelta(days=rec.number_of_days)
                    for i in range(rec.number_of_days + 1):
                        date_entry = reminder_date + td(days=i)
                        #if datetime.date.strftime(date_entry, "%Y-%m-%d") == today:
                        if date_entry.date() == today: # 4jan2020 - pkh
                            rec.stage = 'to_expired'
                    if rec.end_date < today:
                        rec.stage = 'expired'

    #@api.multi
    @api.depends()
    def _invoice_count(self):
        for rec in self:
            rec.ensure_one()
#            rec.invoice_count = self.env['account.invoice'].search_count([
#                ('related_project_id', '=', rec.id),
#            ])
#            account_invoice_line = self.env['account.invoice.line'].search([
#                ('account_analytic_id', '=', rec.id),
#            ])
            account_invoice_line = self.env['account.move.line'].search([
#                ('account_analytic_id', '=', rec.id),
                ('analytic_account_id', '=' ,rec.id),
            ])
#            rec.invoice_count = len(account_invoice_line.mapped('invoice_id'))
            rec.invoice_count = len(account_invoice_line.mapped('move_id'))

    #@api.multi
    def action_view_invoice(self):
        self.ensure_one()
        
#        account_invoice_line = self.env['account.invoice.line'].search([
#            ('account_analytic_id', '=', self.id),
#        ])
        account_invoice_line = self.env['account.move.line'].search([
#            ('account_analytic_id', '=', self.id),
            ('analytic_account_id', '=' ,self.id),
        ])
#        account_invoice_ids = account_invoice_line.mapped('invoice_id')
        account_invoice_ids = account_invoice_line.mapped('move_id')
#        action = self.env.ref('account.action_invoice_tree1')
        action = self.env.ref('account.action_move_out_invoice_type')
        result = action.read()[0]
        result['domain'] = [('id', 'in', account_invoice_ids.ids)]
        return result

    #@api.multi
    def recurring_invoice(self):
        self.stage = 'inprogress'
        if self._context.get('default_name'):
            ctx_cp = self._context.copy()
            ctx_cp.pop('default_name')
            self = self.with_context(ctx_cp)
        invoice_id = self._recurring_create_invoice()
        return self.action_subscription_invoice(invoice_id)

#    @api.returns('account.invoice')
    @api.returns('account.move')
    def _recurring_create_invoice(self, automatic=False):
#        AccountInvoice = self.env['account.invoice']
        AccountInvoice = self.env['account.move']
        invoices = []
        current_date = fields.Date.today()
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        domain = [('id', 'in', self.ids)] if self.ids else [('recurring_next_date', '<=', current_date), ('stage', '!=', 'lock')]
        sub_data = self.search_read(fields=['id', 'company_id'], domain=domain)
        for company_id in set(data['company_id'][0] for data in sub_data):
            company_x = self.env['res.company'].browse(company_id)
            sub_ids = map(lambda s: s['id'], filter(lambda s: s['company_id'][0] == company_id, sub_data))
            subs = self.with_context(company_id=company_id).with_company(company_x).browse(sub_ids)
            # subs = self.with_context(company_id=company_id, force_company=company_id).browse(sub_ids)
            for sub in subs:

                if not self._context.get("from_cron", False):
                    if sub.end_date and sub.end_date < current_date:
                        raise UserError(
                            "You can not create invoice for closed contract!"
                        )
                try:
                    res_sub = sub._prepare_invoice()
                    # invoices.append(AccountInvoice.create(sub._prepare_invoice()))
                    invoices.append(AccountInvoice.create(res_sub))
                    invoices[-1].message_post_with_view('mail.message_origin_link',
#                     values={'self': invoices[-1], 'origin': sub},
                     values={'self': invoices[-1], 'invoice_origin': sub},
                     subtype_id=self.env.ref('mail.mt_note').id)
#                    invoices[-1].compute_taxes()
                    next_date = fields.Date.from_string(sub.recurring_next_date or current_date)
                    if sub.recurring_rule_type == False or sub.recurring_interval == 0:
                        raise UserError("Please select Recurring Period and Recurring type on contract subscription.")
                    rule, interval = sub.recurring_rule_type, sub.recurring_interval
                    new_date = next_date + relativedelta(**{periods[rule]: interval})
                    sub.write({'recurring_next_date': new_date})
                    if automatic:
                        self.env.cr.commit()
                except Exception:
                    if automatic:
                        self.env.cr.rollback()
                        _logger.exception('Fail to create recurring invoice for contract %s', sub.code)
                    else:
                        raise
        return invoices

    #@api.multi
    def _prepare_invoice(self):
        invoice = self._prepare_invoice_data()
        invoice['invoice_line_ids'] = self._prepare_invoice_lines(invoice['fiscal_position_id'])
        return invoice

    #@api.multi
    def _prepare_invoice_data(self):
        self.ensure_one()

        if not self.partner_id:
            raise UserError(_("Please select customer on contract subscription in order to create invoice. %s!") % self.name)

        # if 'force_company' in self.env.context:
        #     company = self.env['res.company'].browse(self.env.context['force_company'])
        # else:
        #     company = self.company_id
        #     company_z = self.env.company
        #     # self = self.with_context(force_company=company.id, company_id=company.id)
        #     self = self.with_context(company_id=company_z.id).with_company(company_z)


        fpos_id = self.env['account.fiscal.position'].get_fiscal_position(self.partner_id.id)
        journal = self.journal_id
        if not journal:
            raise UserError(_('Please select accounting journal on contract subscription: %s.') % self.name)

        if not self.recurring_next_date:
            raise UserError(_("Please select Date of Next Invoice on contract subscription. This is required to make recurring invoice flow. %s!") % self.name)

        next_date = fields.Date.from_string(self.recurring_next_date)
        periods = {'daily': 'days', 'weekly': 'weeks', 'monthly': 'months', 'yearly': 'years'}
        if self.recurring_rule_type == False or self.recurring_interval == 0:
            raise UserError("Please select Recurring Period and Recurring type on contract subscription.")
        end_date = next_date + relativedelta(**{periods[self.recurring_rule_type]: self.recurring_interval})
        end_date = end_date - relativedelta(days=1)     # remove 1 day as normal people thinks in term of inclusive ranges.

        comment = self.terms_and_conditions and  tools.html2plaintext(self.terms_and_conditions).strip() or ''

        next_date = format_date(self.env, next_date)
        end_date = format_date(self.env, end_date)
        comment = comment + '\n\n' + _("This invoice covers the following period: %s - %s") % (next_date, end_date) + '\n'
        return {
            # 'name':self.name,
            'ref':self.name,

#            'origin':self.name,
            'invoice_origin':self.name,
            'related_project_id':self.id,
#            'account_id': self.partner_id.property_account_receivable_id.id,
#            'type': 'out_invoice',
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'currency_id': self.order_invoice_currency_id.id or self.currency_id.id,
            'journal_id': journal.id,
#            'date_invoice': self.recurring_next_date,
            'invoice_date': self.recurring_next_date,
#            'origin': self.code,
            'invoice_origin': self.code,
            'fiscal_position_id': fpos_id.id or False,
#            'payment_term_id': self.partner_id.property_payment_term_id.id,
            'invoice_payment_term_id': self.partner_id.property_payment_term_id.id,
            # 'company_id': company.id,
            'company_id': self.env.company.id,
            # 'comment': _("This invoice covers the following period: %s - %s") % (next_date, end_date),
#            'comment': comment,
            'narration': comment,
        }

    #@api.multi
    def _prepare_invoice_lines(self, fiscal_position):
        self.ensure_one()
        fiscal_position = self.env['account.fiscal.position'].browse(fiscal_position)
        return [(0, 0, self._prepare_invoice_line(line, fiscal_position)) for line in self.subscription_product_line_ids]

    #@api.multi
    def _prepare_invoice_line(self, line, fiscal_position):
#         if 'force_company' in self.env.context:
#             company = self.env['res.company'].browse(self.env.context['force_company'])
#         else:
#             company_y = self.env.company
# #             company = line.analytic_account_id.company_id
#             # line = line.with_context(force_company=company.id, company_id=company.id)
#             line = line.with_context(company_id=company_y.id).with_company(company_y)
        company = self.env.company


        account = line.product_id.property_account_income_id
        if not account:
            account = line.product_id.categ_id.property_account_income_categ_id
        account_id = fiscal_position.map_account(account).id

        tax = line.product_id.taxes_id.filtered(lambda r: r.company_id == company)
        tax = fiscal_position.map_tax(tax)
        return {
            'name': line.name,
#             'analytic_tag_ids':line.analytic_tag_ids,
#            'layout_category_id':line.layout_category_id.id, odoo12
            'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
            'account_id': account_id,
#            'account_analytic_id': self.id,
            'analytic_account_id': self.id,
#            'price_unit': line.product_id.lst_price or 0.0,
            'price_unit': line.price_unit or 0.0,
            'discount': line.discount,
            'quantity': line.product_uom_qty,
#            'uom_id': line.product_uom.id,
            'product_uom_id': line.product_uom.id,
            'product_id': line.product_id.id,
#            'invoice_line_tax_ids': [(6, 0, tax.ids)],
            'tax_ids': [(6, 0, tax.ids)],
        }

    #@api.multi
    def action_subscription_invoice(self, invoice):
        invoices = invoice[0]
#        action = self.env.ref('account.action_invoice_tree1').read()[0]
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        action['domain'] = [('id', 'in', invoices.ids)]
        return action
