# -*- coding: utf-8 -*-
import math
from odoo import models, fields, api,tools, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class RecurringInvoices(models.Model):
    _inherit = 'invoice.recurring'

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False)
    created_by = fields.Many2one(comodel_name='res.users', string='Created By', default=lambda self: self.env.user, tracking=True)
    created_date = fields.Date(string='Created Date', default=fields.Datetime.now, tracking=True)    
    prepayment_journal = fields.Selection([('customer', 'Customer'), ('vendor', 'Vendor')])
    analytic_group_ids = fields.Many2many('account.analytic.tag', string='Analytic Groups', default=lambda self: self.env.user.analytic_tag_ids.ids)
    subtotal = fields.Float("Subtotal", compute='_get_subtotal')
    total = fields.Float("Total", compute='_get_subtotal')
    total_taxes = fields.Float("Total", compute='_get_taxes_total')
    invoice_ids = fields.Many2many('account.move', string="Invoices", compute='_getinvoice_ids')
    remaining_journal_entry = fields.Integer('Remaining Journal Entry', compute='_compute_remaining_entry')
    reference = fields.Many2one('account.move.template', string='Journal Entries Template')
    # journal_id_domain = fields.Char(compute='_compute_journal_id_domain')

    # @api.model
    # def default_get(self, fields_list):
    #     res = super(RecurringInvoices, self).default_get(fields_list)
    #     company_id = res.get('company_id', self.env.company.id)
    #     move_type = self._context.get('default_type', 'entry')
    #     # Execute the SQL query to fetch journal IDs for the selected company
    #     self.env.cr.execute("""
    #         SELECT id
    #         FROM account_journal
    #         WHERE company_id = %s AND move_type = %s
    #     """, (company_id, move_type))
    #     journal_ids = [row[0] for row in self.env.cr.fetchall()]

    #     # Set the domain for the journal_id field based on the fetched journal IDs
    #     res.update({
    #         'journal_id_domain': [('id', 'in', journal_ids)]
    #     })
    #     return res


    @api.onchange('reference')
    def _onchange_reference(self):        
        if self.reference:
            self.sh_move_line = [(5, 0, 0)]
            # self.journal_id = self.reference.journal_id
            line_ids = []
            for line in self.reference.line_ids:
                tmp_line_ids =  {
                                    'account_id': line.account_id.id,
                                    'partner_id': line.partner_id.id,
                                    'name' : line.name,
                                    'analytic_group_ids': line.analytic_tag_ids.ids,
                                    'debit': line.debit,
                                    'credit': line.credit,
                                }
                line_ids.append((0, 0, tmp_line_ids))
            self.sh_move_line = line_ids

    def _getinvoice_ids(self):
        payment_ids = []
        for invoice in self:
            invoice_obj = self.env['account.move']
            invoices = invoice_obj.sudo().search([
                ('sh_invoice_recurring_order_id', '=', invoice.id),
                ('move_type', 'in', ['out_invoice'])
            ])
            invoice.invoice_ids = [(6, 0, invoices.ids)]
    
    
    @api.constrains('sh_move_line')
    def check_balance(self):
        if sum(self.sh_move_line.mapped('debit')) != sum(self.sh_move_line.mapped('credit')):
            raise UserError("Cannot create unbalanced journal entry \n Differences debit - credit: %s" %(sum(self.sh_move_line.mapped('debit'))-sum(self.sh_move_line.mapped('credit'))))
        for i in self.sh_move_line:
            if i.debit > 0 and i.credit > 0:
                 raise UserError("Check your journal line its not allowed to fill both side in one line")
                 
    @api.depends('order_line.tax_ids')
    def _get_taxes_total(self):
        for rec in self:
            total_taxes = 0
            for line in rec.order_line:
                total_taxes += line.price_tax
            rec.total_taxes = total_taxes




    @api.depends('sh_invoice_recurring_count')
    def _get_subtotal(self):
        for rec in self:
            subtotal = 0
            total = 0
            invoice_obj = self.env['account.move']
            invoices = invoice_obj.sudo().search([
                ('sh_invoice_recurring_order_id', '=', rec.id),
                ('move_type', 'in', ['out_invoice'])
            ])
            for inv in invoices:
                subtotal += inv.amount_untaxed
                total += inv.amount_total
            
            rec.subtotal = subtotal
            rec.total = total            


    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        # sys.setdefaultencoding("utf-8")
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.model
    def create(self, vals):
        if 'company_id' in vals:
            self = self.with_company(vals['company_id'])

        if vals.get('name', ('New')) == ('New'):
            seq_date = None
            if 'start_date' in vals:
                seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['start_date']))

            if vals['type'] == 'out_invoice':
                vals['name'] = self.env['ir.sequence'].next_by_code('recurring.in.invoice.seq', sequence_date=seq_date)
            elif vals['type'] == 'in_invoice':
                vals['name'] = self.env['ir.sequence'].next_by_code('recurring.out.invoice.seq',
                                                                     sequence_date=seq_date)
            elif vals['type'] == 'entry':
                vals['name'] = self.env['ir.sequence'].next_by_code('recurring.entry.seq', sequence_date=seq_date)
                if vals['prepayment_journal'] == 'customer':
                    vals['name'] = self.env['ir.sequence'].next_by_code('recurring.customer.prepayment.seq',
                                                                         sequence_date=seq_date)
                elif vals['prepayment_journal'] == 'vendor':
                    vals['name'] = self.env['ir.sequence'].next_by_code('recurring.vendor.prepayment.seq',
                                                                         sequence_date=seq_date)

        result = super(RecurringInvoices, self).create(vals)
        self.confirm()
        return result

    def confirm(self):
        for rec in self:
            rec.state = 'confirm'

    def pending(self):
        for rec in self:
            rec.state = 'pending'

    def done(self):
        for rec in self:
            rec.state = 'done'

    def cancel(self):
        for rec in self:
            rec.state = 'cancel'

    @api.onchange('company_id')
    def _get_domain(self):
        for rec in self:
            field = ''
            if rec.type == 'out_invoice':
                field = ['sale', '']
            elif rec.type == 'in_invoice':
                field = ['purchase', '']
            if rec.type == 'entry':
                field = ['general', 'bank', 'cash']

            if rec.type in ('out_invoice', 'in_invoice'):
                getval = self.env['account.journal'].search([('type', 'in', field)])
                rec.journal_id = getval[0]

        return {
            'domain': {

                'branch_id': f"[('id', 'in', {self.env.branches.ids}), ('company_id','=', {self.env.company.id})]",
                'journal_id': f"[('type','in',{field})]"
            }
        }

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
                        'branch_id': rec.branch_id.id,
                        'company_id': rec.company_id.id,
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
                                    'name': line.name,
                                    'analytic_tag_ids' : [(6,0,line.analytic_group_ids.ids)]
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

                    # created_so = invoice_obj.create(invoice_vals)
                    # Set the context with the default_journal_id to bypass the validation
                    context = dict(self.env.context, default_journal_id=rec.journal_id.id)
                    created_so = invoice_obj.with_context(context).create(invoice_vals)

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
                    'branch_id': self.branch_id.id,
                    'company_id': self.company_id.id,
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
                                'name': line.name,
                                'analytic_tag_ids' : [(6,0,line.analytic_group_ids.ids)]
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

    # @api.model
    # def recurring_order_cron(self):
    #     res = super(RecurringInvoices, self).recurring_order_cron()
    #     print('res otomatis')
    #     print(res)
    #     res.order_line_vals.update({
    #         'analytic_tag_ids': [(6, 0, self.analytic_group_ids.ids)]
    #     })
    #     res.invoice_vals.update({
    #         'invoice_line_ids': res.order_line_vals,
    #     })
    #     return res

    # def create_order_manually(self):
    #     res = super(RecurringInvoices, self).create_order_manually()
    #     print('res MAnual')
    #     print(res)
    #     res.order_line_vals.update({
    #         'analytic_tag_ids': [(6, 0, self.analytic_group_ids.ids)]
    #     })
    #     res.invoice_vals.update({
    #         'invoice_line_ids': res.order_line_vals,
    #     })
    #     return res

    # @api.onchange('analytic_group_ids', 'order_line')
    # def set_account_order_line_tag(self):
    #     for res in self:
    #         for line in res.order_line:
    #             line.update({'analytic_group_ids': [(6, 0, res.analytic_group_ids.ids)],})
    #
    # @api.onchange('analytic_group_ids', 'sh_move_line')
    # def set_account_sh_move_line_tag(self):
    #     for res in self:
    #         for line in res.sh_move_line:
    #             line.update({'analytic_group_ids': [(6, 0, res.analytic_group_ids.ids)],})

    def _compute_remaining_entry(self):
        for rec in self:
            rec.remaining_journal_entry = math.floor(rec.stop_recurring_interval / rec.recurring_interval - rec.sh_journal_entry_recurring_count)


class InvoiceRecurringLine(models.Model):
    _inherit = "invoice.recurring.line"

    analytic_group_ids = fields.Many2many('account.analytic.tag', string='Analytic Groups')
    subtotal = fields.Float("Subtotal", compute='_get_subtotal')
    price_tax = fields.Float(string='Tax Amount', compute='_get_price_tax')
    
    @api.depends('price_unit','quantity')
    def _get_subtotal(self):
        for rec in self:
            subtotal = 0
            if rec.price_unit and rec.quantity:
                subtotal = rec.price_unit * rec.quantity
            rec.subtotal = subtotal


    @api.depends('price_unit', 'tax_ids')
    def _get_price_tax(self):
        for res in self:
            total = 0.0
            for rec in res.tax_ids:
                total += rec.amount
            res.price_tax = res.subtotal * (total / 100)


    @api.onchange('product_id', 'account_id')
    def set_account_order_line_tag(self):
        for res in self:
            res.update({'analytic_group_ids': [(6, 0, res.invoice_recurring_id.analytic_group_ids.ids)],
                        'tax_ids': [(6, 0, res.product_id.supplier_taxes_id.ids)],})