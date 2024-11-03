# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class InvoiceRecurring(models.Model):
    _name = "invoice.recurring"
    _inherit = ['portal.mixin', 'mail.thread',
                'mail.activity.mixin', 'utm.mixin']
    _description = "Invoice Order Recurring"
    _order = 'id desc'

    @api.constrains('sh_move_line')
    def check_balance(self):
        if sum(self.sh_move_line.mapped('debit')) != sum(self.sh_move_line.mapped('credit')):
            raise UserError("Cannot create unbalanced journal entry \n Differences debit - credit: %s" %(sum(self.sh_move_line.mapped('debit'))-sum(self.sh_move_line.mapped('credit'))))
    @api.model
    def get_sale_types(self, include_receipts=False):
        return ['out_invoice', 'out_refund'] + (include_receipts and ['out_receipt'] or [])

    @api.model
    def get_purchase_types(self, include_receipts=False):
        return ['in_invoice', 'in_refund'] + (include_receipts and ['in_receipt'] or [])

    @api.model
    def _search_default_journal(self, journal_types):
        company_id = self._context.get(
            'default_company_id', self.env.company.id)
        domain = [('company_id', '=', company_id),
                  ('type', 'in', journal_types)]

        journal = None
        if self._context.get('default_currency_id'):
            currency_domain = domain + \
                [('currency_id', '=', self._context['default_currency_id'])]
            journal = self.env['account.journal'].search(
                currency_domain, limit=1)

        if not journal:
            journal = self.env['account.journal'].search(domain, limit=1)

        if not journal:
            company = self.env['res.company'].browse(company_id)

            error_msg = _(
                "No journal could be found in company %(company_name)s for any of those types: %(journal_types)s",
                company_name=company.display_name,
                journal_types=', '.join(journal_types),
            )
            raise UserError(error_msg)

        return journal

    @api.model
    def _get_default_journal(self):
        ''' Get the default journal.
        It could either be passed through the context using the 'default_journal_id' key containing its id,
        either be determined by the default type.
        '''
        print("\n\n\n\n\n\n",self._context)
        move_type = self._context.get('default_move_type', 'entry')
        if move_type in self.get_sale_types(include_receipts=True):
            journal_types = ['sale']
        elif move_type in self.get_purchase_types(include_receipts=True):
            journal_types = ['purchase']
        else:
            journal_types = self._context.get(
                'default_move_journal_types', ['general'])

        if self._context.get('default_journal_id'):
            journal = self.env['account.journal'].browse(
                self._context['default_journal_id'])

            if move_type != 'entry' and journal.type not in journal_types:
                raise UserError(_(
                    "Cannot create an invoice of type %(move_type)s with a journal having %(journal_type)s as type.",
                    move_type=move_type,
                    journal_type=journal.type,
                ))
        else:
            journal = self._search_default_journal(journal_types)

        return journal

    name = fields.Char(string='Invoice Recurring Reference', required=True,
                       copy=False, readonly=True, index=True, default=lambda self: _('New'), tracking=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, tracking=True)

    start_date = fields.Date(string='Start date', index=True, copy=False,
                             required=True, default=fields.Date.context_today, store=True, tracking=True)
    active = fields.Boolean(string='Active', default=True, tracking=True)
    title = fields.Char(string="Title", tracking=True)
    note = fields.Text(string="Note", tracking=True)
    order_line = fields.One2many(
        'invoice.recurring.line', 'invoice_recurring_id', string='Order Lines', copy=True, auto_join=True)

    sh_move_line = fields.One2many('recurring.move.line','recurring_id')
    
    last_generated_date = fields.Date(
        string='Last date', index=True, copy=False, tracking=True)
    end_date = fields.Date(string='End date', copy=False, tracking=True)

    type = fields.Selection(selection=[
        ('entry', 'Journal Entry'),
        ('out_invoice', 'Customer Invoice'),
        ('out_refund', 'Customer Credit Note'),
        ('in_invoice', 'Vendor Bill'),
        ('in_refund', 'Vendor Credit Note'),
        ('out_receipt', 'Sales Receipt'),
        ('in_receipt', 'Purchase Receipt'),
    ], string='Type', required=True, store=True, index=True, tracking=True,
        default="entry", change_default=True)

    journal_id = fields.Many2one(
        'account.journal', string='Journal', required=True, readonly=True,
        states={'draft': [('readonly', False)]},
        default=_get_default_journal, tracking=True, domain="[('company_id', '=', company_id)]")

    company_id = fields.Many2one("res.company",
                                 string="Company",
                                 default=lambda self: self.env.company)

    state = fields.Selection([
        ('draft', 'New'),
        ('confirm', 'Running'),
        ('pending', 'To Renew'),
        ('done', 'Expired'),
        ('cancel', 'Cancelled'),
    ], string='Status', required=True, copy=False, default='draft', tracking=True)

    #main recurring part
    recurring_interval = fields.Integer(
        string="Interval", default=1, required=True, tracking=True)
    recurring_interval_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years'),
    ], string="Interval Unit", default="years", required=True, tracking=True)

    stop_recurring_interval = fields.Integer(
        string="Stop after", tracking=True)
    stop_recurring_interval_unit = fields.Selection(
        related="recurring_interval_unit",
        string="Stop Interval Unit", required=True, tracking=True)

    signature = fields.Image('Signature', help='Signature received through the portal.',
                             copy=False, attachment=True, max_width=1024, max_height=1024)
    signed_by = fields.Char(
        'Signed By', help='Name of the person that signed the SO.', copy=False)
    signed_on = fields.Datetime(
        'Signed On', help='Date of the signature.', copy=False)

    online_signature = fields.Boolean('Online Signature',related='company_id.sh_invoice_online_signature')

    invoice_filter_type_domain = fields.Char(compute='_compute_invoice_filter_type_domain',)
    
    @api.depends('type')
    def _compute_invoice_filter_type_domain(self):
        for rec in self:
            if rec.type in ['out_invoice', 'out_refund','out_receipt']:
                rec.invoice_filter_type_domain = 'sale'
            
            elif rec.type in ['in_invoice', 'in_refund','in_receipt']:
                rec.invoice_filter_type_domain = 'purchase'
            
            else:
                rec.invoice_filter_type_domain = False

    def has_to_be_signed(self, include_draft=False):
        return True

    def _compute_access_url(self):
        super(InvoiceRecurring, self)._compute_access_url()
        for invoice in self:
            invoice.access_url = '/my/recurring_invoices/%s' % (invoice.id)

    def active_sr(self):
        if self:
            for rec in self:
                if not rec.active:
                    rec.active = True

    def archive_sr(self):
        if self:
            for rec in self:
                if rec.active:
                    rec.active = False

    @api.onchange('stop_recurring_interval',
                  'recurring_interval_unit', 'start_date')
    def _onchange_stop_recurring_interval(self):
        if self and self.start_date:
            if self.stop_recurring_interval > 0:
                end_date = False
                st_date = fields.Date.from_string(self.start_date)
                if self.recurring_interval_unit == 'days':
                    end_date = st_date + \
                        relativedelta(days=self.stop_recurring_interval - 1)
                elif self.recurring_interval_unit == 'weeks':
                    end_date = st_date + \
                        relativedelta(weeks=self.stop_recurring_interval - 1)
                elif self.recurring_interval_unit == 'months':
                    end_date = st_date + \
                        relativedelta(months=self.stop_recurring_interval - 1)
                elif self.recurring_interval_unit == 'years':
                    end_date = st_date + \
                        relativedelta(years=self.stop_recurring_interval - 1)

                if end_date:
                    self.end_date = end_date
            else:
                self.end_date = False

    #compute no of invoice order in this recuring
    sh_invoice_recurring_count = fields.Integer(
        string='# of Invoices', compute='_compute_sh_invoice_recurring_order_compute')

    sh_bill_recurring_count = fields.Integer(
        string='# of Bills', compute='_compute_bills_count')

    sh_cust_credit_recurring_count = fields.Integer(
        string='# of Customer Credit Notes', compute='_compute_cust_credit_count')

    sh_vendor_credit_recurring_count = fields.Integer(
        string='# of Vendor Credit Notes', compute='_compute_vendor_credit_count')

    sh_sale_receipt_recurring_count = fields.Integer(
        string='# of Sales Receipts', compute='_compute_sale_reciept_count')

    sh_purchase_receipt_recurring_count = fields.Integer(
        string='# of Purchase Receipts', compute='_compute_purchase_reciept_count')

    sh_journal_entry_recurring_count = fields.Integer(compute = '_compute_journal_entry_count')

    def _compute_journal_entry_count(self):
        invoice_obj = self.env['account.move']
        if self:
            for rec in self:
                rec.sh_journal_entry_recurring_count = 0
                count = invoice_obj.sudo().search_count([
                    ('sh_invoice_recurring_order_id', '=', rec.id),
                    ('move_type', 'in', ['entry'])
                ])
                rec.sh_journal_entry_recurring_count = count
    
    def action_view_journal_entry(self):
        if self:
            invoice_obj = self.env['account.move']
            invoices = invoice_obj.sudo().search([
                ('sh_invoice_recurring_order_id', '=', self.id),
                ('move_type', 'in', ['entry'])
            ])
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
            if len(invoices.ids) > 1:
                action['domain'] = [('id', 'in', invoices.ids)]
            elif len(invoices.ids) == 1:
                form_view = [(self.env.ref('account.view_move_form').id, 'form')]
                if 'views' in action:
                    action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
                else:
                    action['views'] = form_view
                action['res_id'] = invoices.ids[0]
            else:
                action = {'type': 'ir.actions.act_window_close'}
            return action

    def _compute_sh_invoice_recurring_order_compute(self):
        invoice_obj = self.env['account.move']
        if self:
            for rec in self:
                rec.sh_invoice_recurring_count = 0
                count = invoice_obj.sudo().search_count([
                    ('sh_invoice_recurring_order_id', '=', rec.id),
                    ('move_type', 'in', ['out_invoice'])
                ])
                rec.sh_invoice_recurring_count = count

    def action_view_recurring_order(self):
        if self:
            invoice_obj = self.env['account.move']
            invoices = invoice_obj.sudo().search([
                ('sh_invoice_recurring_order_id', '=', self.id),
                ('move_type', 'in', ['out_invoice'])
            ])
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_invoice_type")
            if len(invoices.ids) > 1:
                action['domain'] = [('id', 'in', invoices.ids)]
            elif len(invoices.ids) == 1:
                form_view = [(self.env.ref('account.view_move_form').id, 'form')]
                if 'views' in action:
                    action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
                else:
                    action['views'] = form_view
                action['res_id'] = invoices.ids[0]
            else:
                action = {'type': 'ir.actions.act_window_close'}
            return action

    def _compute_bills_count(self):
        invoice_obj = self.env['account.move']
        if self:
            for rec in self:
                rec.sh_bill_recurring_count = 0
                count = invoice_obj.sudo().search_count([
                    ('sh_invoice_recurring_order_id', '=', rec.id),
                    ('move_type', 'in', ['in_invoice'])
                ])
                rec.sh_bill_recurring_count = count

    def action_view_bills(self):
        if self:
            invoice_obj = self.env['account.move']
            invoices = invoice_obj.sudo().search([
                ('sh_invoice_recurring_order_id', '=', self.id),
                ('move_type', 'in', ['in_invoice'])
            ])
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_invoice_type")
            if len(invoices.ids) > 1:
                action['domain'] = [('id', 'in', invoices.ids)]
            elif len(invoices.ids) == 1:
                form_view = [(self.env.ref('account.view_move_form').id, 'form')]
                if 'views' in action:
                    action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
                else:
                    action['views'] = form_view
                action['res_id'] = invoices.ids[0]
            else:
                action = {'type': 'ir.actions.act_window_close'}
            return action

    def _compute_cust_credit_count(self):
        invoice_obj = self.env['account.move']
        if self:
            for rec in self:
                rec.sh_cust_credit_recurring_count = 0
                count = invoice_obj.sudo().search_count([
                    ('sh_invoice_recurring_order_id', '=', rec.id),
                    ('move_type', 'in', ['out_refund'])
                ])
                rec.sh_cust_credit_recurring_count = count

    def action_view_cust_credit_note(self):
        if self:
            invoice_obj = self.env['account.move']
            invoices = invoice_obj.sudo().search([
                ('sh_invoice_recurring_order_id', '=', self.id),
                ('move_type', 'in', ['out_refund'])
            ])
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_refund_type")
            if len(invoices.ids) > 1:
                action['domain'] = [('id', 'in', invoices.ids)]
            elif len(invoices.ids) == 1:
                form_view = [(self.env.ref('account.view_move_form').id, 'form')]
                if 'views' in action:
                    action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
                else:
                    action['views'] = form_view
                action['res_id'] = invoices.ids[0]
            else:
                action = {'type': 'ir.actions.act_window_close'}
            return action
            
    def _compute_vendor_credit_count(self):
        invoice_obj = self.env['account.move']
        if self:
            for rec in self:
                rec.sh_vendor_credit_recurring_count = 0
                count = invoice_obj.sudo().search_count([
                    ('sh_invoice_recurring_order_id', '=', rec.id),
                    ('move_type', 'in', ['in_refund'])
                ])
                rec.sh_vendor_credit_recurring_count = count

    def action_view_vendor_credit_note(self):
        if self:
            invoice_obj = self.env['account.move']
            invoices = invoice_obj.sudo().search([
                ('sh_invoice_recurring_order_id', '=', self.id),
                ('move_type', 'in', ['in_refund'])
            ])
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_refund_type")
            if len(invoices.ids) > 1:
                action['domain'] = [('id', 'in', invoices.ids)]
            elif len(invoices.ids) == 1:
                form_view = [(self.env.ref('account.view_move_form').id, 'form')]
                if 'views' in action:
                    action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
                else:
                    action['views'] = form_view
                action['res_id'] = invoices.ids[0]
            else:
                action = {'type': 'ir.actions.act_window_close'}
            return action

    def _compute_sale_reciept_count(self):
        invoice_obj = self.env['account.move']
        if self:
            for rec in self:
                rec.sh_sale_receipt_recurring_count = 0
                count = invoice_obj.sudo().search_count([
                    ('sh_invoice_recurring_order_id', '=', rec.id),
                    ('move_type', 'in', ['out_receipt'])
                ])
                rec.sh_sale_receipt_recurring_count = count

    def action_view_sale_receipt(self):
        if self:
            invoice_obj = self.env['account.move']
            invoices = invoice_obj.sudo().search([
                ('sh_invoice_recurring_order_id', '=', self.id),
                ('move_type', 'in', ['out_receipt'])
            ])
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_out_receipt_type")
            if len(invoices.ids) > 1:
                action['domain'] = [('id', 'in', invoices.ids)]
            elif len(invoices.ids) == 1:
                form_view = [(self.env.ref('account.view_move_form').id, 'form')]
                if 'views' in action:
                    action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
                else:
                    action['views'] = form_view
                action['res_id'] = invoices.ids[0]
            else:
                action = {'type': 'ir.actions.act_window_close'}
            return action

    def _compute_purchase_reciept_count(self):
        invoice_obj = self.env['account.move']
        if self:
            for rec in self:
                rec.sh_purchase_receipt_recurring_count = 0
                count = invoice_obj.sudo().search_count([
                    ('sh_invoice_recurring_order_id', '=', rec.id),
                    ('move_type', 'in', ['in_receipt'])
                ])
                rec.sh_purchase_receipt_recurring_count = count

    def action_view_purchase_receipt(self):
        if self:
            invoice_obj = self.env['account.move']
            invoices = invoice_obj.sudo().search([
                ('sh_invoice_recurring_order_id', '=', self.id),
                ('move_type', 'in', ['in_receipt'])
            ])
            action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_in_receipt_type")
            if len(invoices.ids) > 1:
                action['domain'] = [('id', 'in', invoices.ids)]
            elif len(invoices.ids) == 1:
                form_view = [(self.env.ref('account.view_move_form').id, 'form')]
                if 'views' in action:
                    action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
                else:
                    action['views'] = form_view
                action['res_id'] = invoices.ids[0]
            else:
                action = {'type': 'ir.actions.act_window_close'}
            return action

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        if self.filtered(lambda c: c.end_date and c.start_date > c.end_date):
            raise ValidationError(_('start date must be less than end date.'))

    @api.constrains('stop_recurring_interval')
    def _check_stop_recurring_interval(self):
        if self.filtered(lambda c: c.stop_recurring_interval < 0):
            raise ValidationError(_('Stop after must be positive.'))

    @api.constrains('recurring_interval')
    def _check_recurring_interval(self):
        if self.filtered(lambda c: c.recurring_interval < 0):
            raise ValidationError(_('Interval must be positive.'))

    @api.model
    def create(self, vals):

        recurring_seq = self.env['ir.sequence'].next_by_code(
            'sh.invoice.recurring.sequence')
        vals.update({'name': recurring_seq})

        res = super(InvoiceRecurring, self).create(vals)
        res.message_subscribe(partner_ids=res.partner_id.ids)
        return res

    @api.model
    def recurring_order_cron(self):
        invoice_obj = self.env['account.move']

        search_recur_orders = self.env['invoice.recurring'].search([
            ('state', '=', 'confirm'),
            ('active', '=', True),
        ])
        if search_recur_orders:
            for rec in search_recur_orders:
                next_date = False
                if not rec.last_generated_date:
                    rec.last_generated_date = rec.start_date
                    next_date = fields.Date.from_string(rec.start_date)
                else:
                    last_generated_date = fields.Date.from_string(
                        rec.last_generated_date)
                    if rec.recurring_interval_unit == 'days':
                        next_date = last_generated_date + \
                            relativedelta(days=rec.recurring_interval)
                    elif rec.recurring_interval_unit == 'weeks':
                        next_date = last_generated_date + \
                            relativedelta(weeks=rec.recurring_interval)
                    elif rec.recurring_interval_unit == 'months':
                        next_date = last_generated_date + \
                            relativedelta(months=rec.recurring_interval)
                    elif rec.recurring_interval_unit == 'years':
                        next_date = last_generated_date + \
                            relativedelta(years=rec.recurring_interval)

                date_now = fields.Date.context_today(rec)
                date_now = fields.Date.from_string(date_now)

                end_date = False

                #for life time contract create
                if not rec.end_date:
                    end_date = next_date

                #for fixed time contract create
                if rec.end_date:
                    end_date = fields.Date.from_string(rec.end_date)

                # we still need to make new quotation
                if next_date <= date_now and next_date <= end_date:
                    invoice_vals = {}
                    invoice_vals.update({
                        'partner_id': rec.partner_id.id,
                        'invoice_date': next_date,
                        'sh_invoice_recurring_order_id': rec.id,
                        'invoice_origin': rec.name,
                        'journal_id': rec.journal_id.id,
                        'move_type': rec.type,
                    })
                    order_line_list = []
                    order_move_line_list = []

                    if rec.order_line and rec.type != 'entry':
                        for line in rec.order_line:
                            # if line.product_id and line.product_id.uom_id:
                                order_line_vals = {
                                    'product_id': line.product_id.id,
                                    'account_id' : line.account_id.id,
                                    'price_unit': line.price_unit,
                                    'quantity': line.quantity,
                                    'tax_ids' : [(6,0,line.tax_ids.ids)],
                                    'discount': line.discount,
                                    'product_uom_id': line.product_uom_id.id,
                                    'name': line.name
                                }
                                order_line_list.append((0, 0, order_line_vals))
                    
                    if rec.sh_move_line and rec.type == 'entry':
                        for line in rec.sh_move_line:
                            
                            order_line_vals = {
                                    'account_id': line.account_id.id,
                                    'partner_id': line.partner_id.id,
                                    'name': line.name,
                                    'debit':line.debit,
                                    'credit':line.credit
                                }
                            order_move_line_list.append((0, 0, order_line_vals))

                    if order_line_list:
                        invoice_vals.update({
                            'invoice_line_ids': order_line_list,
                        })
                    
                    if order_move_line_list:
                        invoice_vals.update({
                            'line_ids': order_move_line_list,
                        })

                    created_so = invoice_obj.create(invoice_vals)
                    if created_so:
                        rec.last_generated_date = next_date

                # make state into done state and no require any more new quotation.
#                 last_gen_date = fields.Date.from_string(rec.last_generated_date)
                if rec.end_date and end_date <= next_date:
                    rec.state = 'done'

    def create_order_manually(self):
        self.ensure_one()
        invoice_obj = self.env['account.move']
        if self:
            next_date = False
            if not self.last_generated_date:
                self.last_generated_date = self.start_date
                next_date = fields.Date.from_string(self.start_date)
            else:
                last_generated_date = fields.Date.from_string(
                    self.last_generated_date)
                if self.recurring_interval_unit == 'days':
                    next_date = last_generated_date + \
                        relativedelta(days=self.recurring_interval)
                elif self.recurring_interval_unit == 'weeks':
                    next_date = last_generated_date + \
                        relativedelta(weeks=self.recurring_interval)
                elif self.recurring_interval_unit == 'months':
                    next_date = last_generated_date + \
                        relativedelta(months=self.recurring_interval)
                elif self.recurring_interval_unit == 'years':
                    next_date = last_generated_date + \
                        relativedelta(years=self.recurring_interval)

            end_date = False

            #for life time contract create
            if not self.end_date:
                end_date = next_date

            #for fixed time contract create
            if self.end_date:
                end_date = fields.Date.from_string(self.end_date)

            # we still need to make new quotation
            if next_date <= end_date:
                invoice_vals = {}
                invoice_vals.update({
                    'partner_id': self.partner_id.id,
                    'invoice_date': next_date,
                    'sh_invoice_recurring_order_id': self.id,
                    'invoice_origin': self.name,
                    'journal_id': self.journal_id.id,
                    'move_type': self.type,
                })
                order_line_list = []
                order_move_line_list = []

                if self.order_line and self.type != 'entry':
                    for line in self.order_line:
                        # if line.product_id and line.product_id.uom_id:
                            order_line_vals = {
                                'product_id': line.product_id.id,
                                'account_id' : line.account_id.id,
                                'price_unit': line.price_unit,
                                'quantity': line.quantity,
                                'tax_ids' : [(6,0,line.tax_ids.ids)],
                                'discount': line.discount,
                                'product_uom_id': line.product_uom_id.id,
                                'name': line.name
                            }
                            order_line_list.append((0, 0, order_line_vals))
                
                if self.sh_move_line and self.type == 'entry':
                    for line in self.sh_move_line:
                        
                        order_line_vals = {
                                'account_id': line.account_id.id,
                                'partner_id': line.partner_id.id,
                                'name': line.name,
                                'debit':line.debit,
                                'credit':line.credit
                            }
                        order_move_line_list.append((0, 0, order_line_vals))

                if order_line_list:
                    invoice_vals.update({
                        'invoice_line_ids': order_line_list,
                    })
                
                if order_move_line_list:
                    invoice_vals.update({
                        'line_ids': order_move_line_list,
                    })

                created_so = invoice_obj.create(invoice_vals)
                if created_so:
                    self.last_generated_date = next_date

            # make state into done state and no require any more new quotation.
#             last_gen_date = fields.Date.from_string(self.last_generated_date)
            if self.end_date and end_date <= next_date:
                self.state = 'done'


class InvoiceRecurringLine(models.Model):
    _name = "invoice.recurring.line"
    _description = "Invoice Recurring Line"

    invoice_recurring_id = fields.Many2one(
        'invoice.recurring', string='Order Reference',
        required=True, ondelete='cascade', index=True, copy=False)
    product_id = fields.Many2one('product.product', string='Product')
    account_id = fields.Many2one('account.account',string = "Account",required = True)
    tax_ids = fields.Many2many('account.tax',string = "Taxes")
    product_uom_category_id = fields.Many2one('uom.category', related='product_id.uom_id.category_id')
    product_uom_id = fields.Many2one('uom.uom',string = "UoM",domain="[('category_id', '=', product_uom_category_id)]")
    name = fields.Text(string='Description', required=True)
    price_unit = fields.Float(
        'Unit Price', required=True, digits='Product Price', default=0.0)
    discount = fields.Float(string='Discount (%)',
                            digits="Discount", default=0.0)
    quantity = fields.Float(
        string='Quantity', digits='Product Unit of Measure',
        required=True, default=1.0)
    company_id = fields.Many2one("res.company",
                                 string="Company",
                                 default=lambda self: self.env.company)

    journal_id = fields.Many2one(related='invoice_recurring_id.journal_id', store=True, index=True, copy=False)
    
    @api.model
    def default_get(self, default_fields):
    
        values = super(InvoiceRecurringLine, self).default_get(default_fields)
        
        if 'account_id' in default_fields and not values.get('account_id') and (self._context.get('journal_id')):
            journal = self.env['account.journal'].browse(self._context['journal_id'])
            values['account_id'] = journal.default_account_id.id

        return values


    @api.onchange('product_id')
    def product_id_change(self):
        if self:
            for rec in self:
                if rec.product_id:
                    name = rec.product_id.name_get()[0][1]
                    if rec.product_id.description_sale:
                        name += '\n' + rec.product_id.description_sale
                    rec.name = name
                    rec.price_unit = rec.product_id.lst_price


class ReccuringMoveLine(models.Model):
    _name = 'recurring.move.line'
    _description = "Recurring Move Line"

    account_id = fields.Many2one('account.account',required = True)
    partner_id = fields.Many2one('res.partner')
    name = fields.Char()
    debit = fields.Float(string='Debit',)
    credit = fields.Float(string='Credit', )
    recurring_id = fields.Many2one(
        'invoice.recurring', string='Order Reference',
        required=True, ondelete='cascade', index=True, copy=False)