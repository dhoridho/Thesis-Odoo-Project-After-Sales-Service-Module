
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    payment_proof = fields.Binary(string='Payment Proof', tracking=True)
    tax_payment_date = fields.Date(string='Tax Payment Date', tracking=True)
    payment_fields_boolean = fields.Boolean(string="Make Payment fields Visible", compute='_compute_payment_boolean', store=True)
    ppn = fields.Html(string='PPN',readonly=True)
    pph = fields.Html(string='PPH',readonly=True)
    tax_paid_status = fields.Selection([
            ('unpaid', 'Unpaid'),
            ('paid', 'Paid'),
        ], string='Tax Paid Status', default='unpaid',
       )
    file_name = fields.Char(string="File Name")
    payment_date = fields.Date(string='Payment Date')
    tax_payment_move_id = fields.Many2one('account.move', string='Tax Payment Journal')
    tax_pay_seprately_amount = fields.Float(string='Tax Pay Separately', compute='_compute_tax_pay_seprately', store=True)
    is_edit_data = fields.Boolean(string="Edit Data", default=True)

    @api.onchange('tax_payment_date','payment_proof')
    def onchange_tax_payment_date(self):
        self.is_edit_data = True


    def write(self, vals):
        context = self._context
        if context.get('search_default_unpaid_tax'):
            vals['is_edit_data'] = False
            if self.tax_payment_date == False and self.payment_proof == False:
                vals['is_edit_data'] = True
            if 'tax_payment_date' in vals and vals['tax_payment_date'] == False and self.payment_proof == False:
                vals['is_edit_data'] = True
            if 'payment_proof' in vals and vals['payment_proof'] and self.tax_payment_date == False:
                vals['is_edit_data'] = True
            if 'payment_proof' in vals and vals['payment_proof'] and 'tax_payment_date' in vals and vals['tax_payment_date'] == False:
                vals['is_edit_data'] = True



            
        res = super(AccountMove, self).write(vals)
        return res


    @api.depends('line_ids')
    def _compute_tax_pay_seprately(self):
        for record in self:
            total_amount = 0
            for line in record.line_ids.filtered(lambda r:r.tax_repartition_line_id):
                tax_id = line.tax_repartition_line_id.invoice_tax_id
                if tax_id.pay_separately:
                    line_amount = line.debit if line.debit > 0 else line.credit
                    total_amount += line_amount
            record.tax_pay_seprately_amount = total_amount

    @api.depends('invoice_line_ids')
    def _compute_payment_boolean(self):
        for record in self:
            pay_seprately_tax = record.invoice_line_ids.mapped('tax_ids').filtered(lambda tax: tax.pay_separately)
            if pay_seprately_tax:
                record.payment_fields_boolean = True
            else:
                record.payment_fields_boolean = False

    def open_invoice(self):
        domain = []
        _name = ''
        rq_tree = rq_form = ''
        domain = [('id', '=', self.id)]
        _name = self.name
        model = 'account.move'
        rq_form = self.env.ref('account.view_move_form', False)
        views = [(rq_form.id, 'form')]
        if rq_form:
            return {
                'name': _name,
                'type': 'ir.actions.act_window',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': model,
                'views': views,
                'res_id': self.id,
                'view_id': rq_form.id,
                'target': 'current',
                'domain': domain,
            }

    def action_tax_invoice_open(self):
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft']):
            pass
        for invoice in self:
            if not invoice.tax_payment_date:
                raise UserError(_('Payment date is empty. Please select the payment date!'))
            if not invoice.payment_proof:
                raise UserError(_('Please upload the payment proof!'))
            else:
                invoice.action_tax_move_create()
                invoice.tax_paid_status = 'paid'
        return to_open_invoices.action_invoice_paid()


    def action_bill_tax_invoice_open(self):
        to_open_invoices = self.filtered(lambda inv: inv.state != 'open')
        if to_open_invoices.filtered(lambda inv: inv.state not in ['proforma2', 'draft']):
            pass
        for invoice in self:
            if not invoice.tax_payment_date:
                raise UserError(_('Payment date is empty. Please select the payment date!'))
            if not invoice.payment_proof:
                raise UserError(_('Please upload the payment proof!'))
            else:
                invoice.action_bill_tax_move_create()
                invoice.tax_paid_status = 'paid'
        return to_open_invoices.action_invoice_paid()

    def button_cancel(self):
        res = super(AccountMove, self).button_cancel()
        for invoice in self:
            invoice.payment_proof = ''
            invoice.payment_date = ''
            invoice.tax_paid_status = 'unpaid'
        return res

    def action_tax_move_create(self):
        account_move = self.env['account.move']
        for inv in self:
            move_vals = {
                'move_type': 'entry',
                'date': inv.tax_payment_date,
                'journal_id': inv.journal_id.id,
                'line_ids': [],
                'ref': 'Payment Tax :' + inv.name,
            }
            tax_line_ids = []
            tax_temp_data = []
            lines_ids = []
            fp_list = []
            for line in self.line_ids.filtered(lambda r:r.tax_repartition_line_id):
                tax_id = line.tax_repartition_line_id.invoice_tax_id
                factor_percent = line.tax_repartition_line_id.factor_percent
                if tax_id.pay_separately:
                    line_amount = line.debit if line.debit > 0 else line.credit
                    if factor_percent < 0:
                        credit_amount = 0
                        debit_amount = ((line_amount * factor_percent)/100)*-1
                    else:
                        credit_amount = ((line_amount * factor_percent)/100)
                        debit_amount = 0

                    move_line_vals = {
                        'account_id': line.account_id.id,
                        'partner_id': line.partner_id.id,
                        'name': 'Payment Tax : '+ inv.name,
                        'currency_id': line.currency_id.id,
                        'credit': credit_amount,
                        'debit': debit_amount,
                    }
                    
                    fp_list.append((0, 0, line.tax_repartition_line_id.factor_percent))

                    if tax_id.id not in tax_temp_data:
                        tax_temp_data.append(tax_id.id)
                        tax_line_ids.append({'tax_id': tax_id, 'tax_amount': line_amount, 'factor_percent': factor_percent})

                    else:
                        filter_line = list(filter(lambda r:r.get('tax_id') == tax_id, tax_line_ids))
                        if filter_line:
                            filter_line[0]['tax_amount'] += line_amount
                            filter_line[0]['factor_percent'] += factor_percent
                            # filter_line[0]['tax_amount'] += credit_amount
                    lines_ids.append((0, 0, move_line_vals))

            for tax_line in tax_line_ids:
                if tax_id.pay_separately :
                    credit_value = 0
                    debit_value = tax_line.get('tax_amount') * tax_line.get('factor_percent') / 100
                    move_line_vals1 = {
                        'account_id': tax_line.get('tax_id').tax_paid_account.id,
                        'partner_id': inv.partner_id.id,
                        'name': 'Payment Tax : '+ inv.name,
                        'currency_id': inv.currency_id.id,
                        'credit': credit_value,
                        'debit': debit_value,
                    }
                    lines_ids.append((0, 0, move_line_vals1))
            move_vals.update({'line_ids': lines_ids})
            move = account_move.create(move_vals)
            inv.tax_payment_move_id = move.id
            move.action_post()
        return True


    def action_bill_tax_move_create(self):
        account_move = self.env['account.move']
        for inv in self:
            move_vals = {
                'move_type': 'entry',
                'date': inv.tax_payment_date,
                'journal_id': inv.journal_id.id,
                'line_ids': [],
                'ref': 'Payment Tax :' + inv.name,
            }
            tax_line_ids = []
            tax_temp_data = []
            lines_ids = []
            for line in self.line_ids.filtered(lambda r:r.tax_repartition_line_id):
                tax_id = line.tax_repartition_line_id.invoice_tax_id
                factor_percent = line.tax_repartition_line_id.factor_percent
                if tax_id.pay_separately:
                    line_amount = line.debit if line.debit > 0 else line.credit
                    # paid_tax = amt_tax * factor_percent / 100
                    if factor_percent < 0:
                        credit_amount = ((line_amount * factor_percent)/100)*-1
                        debit_amount = 0
                    else:
                        credit_amount = 0
                        debit_amount = ((line_amount * factor_percent)/100)
                    
                    move_line_vals = {
                        'account_id': line.account_id.id,
                        'partner_id': line.partner_id.id,
                        'name': 'Payment Tax : '+ inv.name,
                        'currency_id': line.currency_id.id,
                        'debit': debit_amount,
                        'credit': credit_amount,
                    }
                    if tax_id.id not in tax_temp_data:
                        tax_temp_data.append(tax_id.id)
                        tax_line_ids.append({'tax_id': tax_id, 'tax_amount': line_amount, 'factor_percent': factor_percent})
                    else:
                        filter_line = list(filter(lambda r:r.get('tax_id') == tax_id, tax_line_ids))
                        if filter_line:
                            filter_line[0]['tax_amount'] += line_amount
                            filter_line[0]['factor_percent'] += factor_percent
                    lines_ids.append((0, 0, move_line_vals))

            for tax_line in tax_line_ids:
                if tax_id.pay_separately :
                    credit_value = tax_line.get('tax_amount') * tax_line.get('factor_percent') / 100
                    debit_value = 0

                    move_line_vals1 = {
                        'account_id': tax_line.get('tax_id').tax_paid_account.id,
                        'partner_id': inv.partner_id.id,
                        'name': 'Payment Tax : '+ inv.name,
                        'currency_id': inv.currency_id.id,
                        'debit': debit_value,
                        'credit': credit_value,
                    }
                    lines_ids.append((0, 0, move_line_vals1))
            move_vals.update({'line_ids': lines_ids})
            move = account_move.create(move_vals)
            inv.tax_payment_move_id = move.id
            move.action_post()
        return True
