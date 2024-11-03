from datetime import timedelta
import pytz
from odoo import api, fields, models
from odoo import tools
from odoo.tools import float_is_zero
from datetime import datetime

class UserOrderDic(models.TransientModel):
    _inherit = "user.order.dic"

    payment_report_id = fields.Many2one('sh.payment.report.wizard')
    list_pay = fields.One2many('list.pay', 'order_dic_id')

class JournalPaymentReport(models.TransientModel):
    _name = "journal.payment.report"
    _description = "Journal Payment Report"

    name = fields.Char('Name')
    total = fields.Float('Total')
    report_id = fields.Many2one('sh.payment.report.wizard')

class ListPay(models.TransientModel):
    _name = "list.pay"
    _description = "List Pay"

    order_dic_id = fields.Many2one('user.order.dic')
    cash = fields.Float("Cash")
    bank = fields.Float("Bank")
    total = fields.Float("Total")
    invoice = fields.Char("Invoice")
    customer = fields.Char("Customer")
    invoice_date = fields.Datetime("Invoice Date")
    payments_date = fields.Datetime("Payment Date")
    salesperson = fields.Char("Sales Person")

class SHPaymentReportWizard(models.TransientModel):
    _inherit = "sh.payment.report.wizard"

    def domain_company(self):
        return [('id', 'in', self.env.companies.ids)]

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        # return self.env.company_branches.ids
        return self.env.branches.ids


    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids)]

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id, domain=domain_company)
    company_ids = fields.Many2many(
        'res.company', string='Companies', domain=domain_company)
    currency_precision = fields.Integer("Currency Precision")
    user_data_dic = fields.One2many('user.order.dic', 'payment_report_id')
    grand_journal_dic = fields.One2many('journal.payment.report', 'report_id')
    branch_ids = fields.Many2many('res.branch', default=_default_branch, domain=_domain_branch, string="Branch")

    def print_report(self):
        order_dic_obj = self.env['user.order.dic']
        list_order_obj = self.env['list.pay']
        journal_obj = self.env['journal.payment.report']
        datas = self.read()[0]
        datas.update(self._get_report_values(datas))
        self.write({
            'user_data_dic': [(6,0,[])],
            'grand_journal_dic': [(6,0,[])]
        })
        for user in datas['user_ids']:
            name = self.env['res.users'].browse(user).name
            dic = order_dic_obj.create({
                'payment_report_id': self.id,
                'saleperson': name,
            })
            for line in datas['user_data_dic'][name]['pay']:
                cash = 0
                bank = 0
                if 'Cash' in line:
                    cash = line['Cash']
                if 'Bank' in line:
                    bank = line['Bank']
                list_order_obj.create({
                    'order_dic_id': dic.id,
                    'cash': cash,
                    'bank': bank,
                    'total': line['Total'],
                    'invoice': line['Invoice'],
                    'customer': line['Customer'],
                    'invoice_date': line['Invoice Date'],
                    'payments_date': line['Payment Date'],
                    'salesperson': line['Salesperson'],
                })
        for journal in list(datas['grand_journal_dic'].items()):
            journal_obj.create({
                'report_id': self.id,
                'name': journal[0],
                'total': journal[1]
            })
        self.write({
            'date_start': datas['date_start'],
            'date_end': datas['date_end'],
            'user_ids': [(6,0,datas['user_ids'])],
            'state': datas['state'],
            'company_ids': [(6,0,datas['company_ids'])],
            'currency_precision': datas['currency']
        })
        return self.env.ref('equip3_sale_report.payment_report_action').report_action(self)

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
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
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.model
    def _get_report_values(self, data=None):

        data = dict(data or {})
        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]

        journal_domain = [('type','in',['bank','cash'])]
        if data.get('company_ids', False):
            journal_domain.append(('company_id','in',data.get('company_ids', False)))
        search_journals = account_journal_obj.sudo().search(journal_domain)

        final_col_list = ["Invoice", "Invoice Date", "Salesperson", "Customer"]
        final_total_col_list = []
        for journal in search_journals:
            if journal.name not in final_col_list:
                final_col_list.append(journal.name)
            if journal.name not in final_total_col_list:
                final_total_col_list.append(journal.name)

        final_col_list.append("Total")
        final_total_col_list.append("Total")

        currency = False
        grand_journal_dic = {}
        j_refund = 0.0

        user_data_dic = {}
        if data.get("user_ids", False):

            for user_id in data.get("user_ids"):
                invoice_pay_dic = {}
                invoice_domain = [
                    ('invoice_user_id', '=', user_id)
                ]
                if data.get("state", False):
                    state = data.get("state")
                    if state == 'all':
                        invoice_domain.append(
                            ('state', 'not in', ['draft', 'cancel']))
                    elif state == 'open':
                        invoice_domain.append(('state', '=', 'posted'))
                    elif state == 'paid':
                        invoice_domain.append(('state', '=', 'posted'))
                invoice_domain.append(
                    ('invoice_date', '>=', data['date_start']))
                invoice_domain.append(('invoice_date', '<=', data['date_end']))
                if data.get('company_ids', False):
                    invoice_domain.append(
                        ("company_id", "in", data.get('company_ids', False)))
                if data.get('branch_ids', False):
                    invoice_domain.append(
                        ("branch_id", "in", data.get('branch_ids', False)))
                # journal wise payment first we total all bank, cash etc etc.
                invoice_ids = self.env['account.move'].sudo().search(
                    invoice_domain)
                if invoice_ids:
                    for invoice in invoice_ids:
                        pay_term_line_ids = invoice.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                        partials = pay_term_line_ids.mapped(
                            'matched_debit_ids') + pay_term_line_ids.mapped('matched_credit_ids')
                        if partials:
                            # journal wise payment first we total all bank, cash etc etc.
                            for partial in partials:
                                counterpart_lines = partial.debit_move_id + partial.credit_move_id
                                counterpart_line = counterpart_lines.filtered(
                                    lambda line: line.id not in invoice.line_ids.ids)
                                foreign_currency = invoice.currency_id if invoice.currency_id != self.env.company.currency_id else False
                                if foreign_currency and partial.company_currency_id == foreign_currency:
                                    payment_amount = partial.amount_currency
                                else:
                                    payment_amount = partial.company_currency_id._convert(
                                        partial.amount, invoice.currency_id, self.env.company, fields.Date.today())

                                if float_is_zero(payment_amount, precision_rounding=invoice.currency_id.rounding):
                                    continue
                                if not currency:
                                    currency = invoice.currency_id
                                if invoice.move_type == "out_invoice":
                                    if invoice_pay_dic.get(invoice.name, False):
                                        pay_dic = invoice_pay_dic.get(
                                            invoice.name)
                                        total = pay_dic.get("Total")
                                        if pay_dic.get(counterpart_line.payment_id.journal_id.name, False):
                                            amount = pay_dic.get(
                                                counterpart_line.payment_id.journal_id.name)
                                            total += payment_amount
                                            amount += payment_amount
                                            pay_dic.update(
                                                {counterpart_line.payment_id.journal_id.name: amount, "Total": total})
                                        else:
                                            total += payment_amount
                                            pay_dic.update(
                                                {counterpart_line.payment_id.journal_id.name: payment_amount, "Total": total})

                                        invoice_pay_dic.update(
                                            {invoice.name: pay_dic})
                                    else:
                                        invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: payment_amount, "Total": payment_amount, "Invoice": invoice.name, "Customer": invoice.partner_id.name,
                                                                               "Invoice Date": invoice.invoice_date, "Payment Date": invoice.payments_date, "Salesperson": invoice.invoice_user_id.name if invoice.invoice_user_id else "", "style": 'border: 1px solid black;'}})
                                if invoice.move_type == "out_refund":
                                    j_refund += payment_amount
                                    if invoice_pay_dic.get(invoice.name, False):
                                        pay_dic = invoice_pay_dic.get(
                                            invoice.name)
                                        total = pay_dic.get("Total")
                                        if pay_dic.get(counterpart_line.payment_id.journal_id.name, False):
                                            amount = pay_dic.get(
                                                counterpart_line.payment_id.journal_id.name)
                                            total -= payment_amount
                                            amount -= payment_amount
                                            pay_dic.update(
                                                {counterpart_line.payment_id.journal_id.name: amount, "Total": total})
                                        else:
                                            total -= invoice.amount_total_signed
                                            pay_dic.update(
                                                {counterpart_line.payment_id.journal_id.name: -1 * (payment_amount), "Total": total})

                                        invoice_pay_dic.update(
                                            {invoice.name: pay_dic})

                                    else:
                                        invoice_pay_dic.update({invoice.name: {counterpart_line.payment_id.journal_id.name: -1 * (payment_amount), "Total": -1 * (payment_amount), "Invoice": invoice.name, "Customer": invoice.partner_id.name,
                                                                               "Invoice Date": invoice.invoice_date, "Payment Date": invoice.payments_date, "Salesperson": invoice.invoice_user_id.name if invoice.invoice_user_id else "", "style": 'border: 1px solid black;color:red'}})

                # all final list and [{},{},{}] format
                # here we get the below total.
                # total journal amount is a grand total and format is : {} just a dictionary
                final_list = []
                total_journal_amount = {}
                for key, value in invoice_pay_dic.items():
                    final_list.append(value)
                    for col_name in final_total_col_list:
                        if total_journal_amount.get(col_name, False):
                            total = total_journal_amount.get(col_name)
                            total += value.get(col_name, 0.0)

                            total_journal_amount.update({col_name: total})

                        else:
                            total_journal_amount.update(
                                {col_name: value.get(col_name, 0.0)})

                # finally make user wise dic here.
                search_user = self.env['res.users'].search([
                    ('id', '=', user_id)
                ], limit=1)
                if search_user:
                    user_data_dic.update({
                        search_user.name: {'pay': final_list,
                                           'grand_total': total_journal_amount}
                    })

                for col_name in final_total_col_list:
                    j_total = 0.0
                    j_total = total_journal_amount.get(col_name, 0.0)
                    j_total += grand_journal_dic.get(col_name, 0.0)
                    grand_journal_dic.update({col_name: j_total})

            j_refund = j_refund * -1
            grand_journal_dic.update({'Refund': j_refund})

        data.update({
            'date_start': data['date_start'],
            'date_end': data['date_end'],
            'columns': final_col_list,
            'user_data_dic': user_data_dic,
            'currency': currency,
            'grand_journal_dic': grand_journal_dic,
        })

        return data

class AccountMove(models.Model):
    _inherit = 'account.move'

    payments_date = fields.Datetime("Payment Date", readonly=False)

    @api.constrains('payment_state')
    def set_payment_date(self):
        for inv in self:
            if inv.payment_state in ('paid','partial'):
                inv.payments_date = datetime.now()
