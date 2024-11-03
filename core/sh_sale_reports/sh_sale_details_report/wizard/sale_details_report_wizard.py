# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import datetime,timedelta
import pytz
import xlwt
import base64
from io import BytesIO
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class SaleDetailExcel(models.Model):
    _name = "sh.sales.detail.xls"
    _description = "Sales Detail XLS"

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.sales.detail.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class SalesDetailWizard(models.TransientModel):
    _name = "sh.sale.details.report.wizard"
    _description = "sh sale details report wizard model"

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return

    start_date = fields.Datetime(
        string="Start Date", required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(
        string="End Date", required=True, default=fields.Datetime.now)
    state = fields.Selection([
        ('all', 'All'),
        ('done', 'Done'),
    ], string='Status', default='all')

    team_ids = fields.Many2many(
        comodel_name="crm.team",
        relation="rel_sh_sale_details_report_wizard_crm_team",
        string="Sales Channel")
    company_ids = fields.Many2many(
        'res.company', string='Companies', default=default_company_ids)

    @api.model
    def default_get(self, fields):
        rec = super(SalesDetailWizard, self).default_get(fields)
        search_teams = self.env["crm.team"].sudo().search([])
        rec.update({
            "team_ids": [(6, 0, search_teams.ids)],
        })
        return rec

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        if self.filtered(lambda c: c.end_date and c.start_date > c.end_date):
            raise ValidationError(_('start date must be less than end date.'))

    def print_report(self):
        data = {'date_start': self.start_date, 'date_stop': self.end_date,
                'team_ids': self.team_ids.ids, 'company_ids': self.company_ids.ids, 'state': self.state}

        return self.env.ref('sh_sale_reports.sh_sale_details_report_action').report_action([], data=data)

    def print_sale_detail_xls_report(self,):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold_center = xlwt.easyxf(
            'font:height 225,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        b1 = xlwt.easyxf('font:bold True;align: horiz left')
        bold_right = xlwt.easyxf('align: horiz right')
        center = xlwt.easyxf('font:bold True;align: horiz center')
        date_start = False
        date_stop = False
        if self.start_date:
            date_start = fields.Datetime.from_string(self.start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.end_date:
            date_stop = fields.Datetime.from_string(self.end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        team_ids = False,
        data = {}
        data = dict(data or {})

        worksheet = workbook.add_sheet(u'Sale Details', cell_overwrite_ok=True)
        worksheet.write_merge(0, 1, 0, 3, 'Sale Details', heading_format)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.start_date),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT) 
        end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.end_date),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        worksheet.write_merge(2, 2, 0, 3, start_date +
                              " to " + end_date, center)
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(date_start)),
            ('date_order', '<=', fields.Datetime.to_string(date_stop)),
        ]
        if self.company_ids:
            domain.append(('company_id', 'in', self.company_ids.ids))
        if team_ids:
            domain.append(('team_id', 'in', self.team_ids.ids))

        if self.state and self.state == 'done':
            domain.append(('state', 'in', ['sale', 'done']))
        orders = self.env['sale.order'].sudo().search(domain)
        user_currency = self.env.company.currency_id

        total = 0.0
        products_sold = {}
        taxes = {}
        invoice_id_list = []
        for order in orders:
            if user_currency != order.pricelist_id.currency_id:
                total += order.pricelist_id.currency_id.compute(
                    order.amount_total, user_currency)
            else:
                total += order.amount_total
            currency = order.currency_id
            for line in order.order_line:
                if not line.display_type:
                    key = (line.product_id, line.price_unit, line.discount)
                    products_sold.setdefault(key, 0.0)
                    products_sold[key] += line.product_uom_qty
    
                    if line.tax_id:
                        line_taxes = line.tax_id.compute_all(line.price_unit * (1 - (line.discount or 0.0) / 100.0), currency,
                                                             line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_id or False)
                        for tax in line_taxes['taxes']:
                            taxes.setdefault(
                                tax['id'], {'name': tax['name'], 'total': 0.0})
                            taxes[tax['id']]['total'] += tax['amount']

            if order.invoice_ids:
                f_invoices = order.invoice_ids.filtered(
                    lambda inv: inv.state not in ['draft', 'cancel'])
                if f_invoices:
                    invoice_id_list += f_invoices.ids

        account_payment_obj = self.env["account.payment"]
        account_journal_obj = self.env["account.journal"]

        search_journals = account_journal_obj.sudo().search([
            ('type', 'in', ['bank', 'cash'])
        ])

        journal_wise_total_payment_list = []
        if invoice_id_list and search_journals:
            for journal in search_journals:
                invoice_domain = [
                    ('id', 'in', invoice_id_list)
                ]
                invoices = self.env['account.move'].sudo().search(
                    invoice_domain)
                payment_domain = []
                for invoice in invoices:
                    payment_domain.append(
                        ("payment_type", "in", ["inbound", "outbound"]))
                    payment_domain.append(("ref", "=", invoice.name))
                    payment_domain.append(("journal_id", "=", journal.id))
                payments = account_payment_obj.sudo().search(payment_domain)
                paid_total = 0.0
                if payments:
                    for payment in payments:
                        paid_total += payment.amount

                journal_wise_total_payment_list.append(
                    {"name": journal.name, "total": paid_total})
        else:
            journal_wise_total_payment_list = []

        var = {
            'currency_precision': user_currency.decimal_places,
            'total_paid': user_currency.round(total),
            'payments': journal_wise_total_payment_list,
            'company_name': self.env.company.name,
            'taxes': taxes.values(),
            'products': sorted([{
                'product_id': product.id,
                'product_name': product.name,
                'code': product.default_code,
                'quantity': qty,
                'price_unit': price_unit,
                'discount': discount,
                'uom': product.uom_id.name
            } for (product, price_unit, discount), qty in products_sold.items()], key=lambda l: l['product_name'])
        }
        list1 = var.get("products")
        worksheet.write_merge(4, 4, 0, 3, "Products", bold_center)
        worksheet.col(0).width = int(25 * 260)
        worksheet.col(1).width = int(25 * 260)
        worksheet.col(2).width = int(12 * 260)
        worksheet.col(3).width = int(14 * 260)

        worksheet.write(5, 0, "Product", bold)
        worksheet.write(5, 1, "Quantity", bold)
        worksheet.write(5, 2, "", bold)
        worksheet.write(5, 3, "Price Unit", bold)
        row = 6
        for rec in list1:
            worksheet.write(row, 0, rec['product_name'])
            worksheet.write(row, 1, str(rec['quantity']), bold_right)
            if rec['uom'] != 'Unit(s)':
                worksheet.write(row, 2, rec['uom'])
            worksheet.write(row, 3, str(rec['price_unit']), bold_right)
            row += 1
        row += 1
        list2 = var.get("payments")
        worksheet.write_merge(row, row, 0, 3, "Payments", bold_center)
        row += 1
        worksheet.write_merge(row, row, 0, 1, "Name", bold)
        worksheet.write_merge(row, row, 2, 3, "Total", bold)
        row += 1
        for rec1 in list2:
            worksheet.write_merge(row, row, 0, 1, rec1['name'])
            worksheet.write_merge(
                row, row, 2, 3, str(rec1['total']), bold_right)
            row += 1
        row += 1
        list3 = var.get("taxes")
        worksheet.write_merge(row, row, 0, 3, "Taxes", bold_center)
        row += 1
        worksheet.write_merge(row, row, 0, 1, "Name", bold)
        worksheet.write_merge(row, row, 2, 3, "Total", bold)
        row += 1
        for rec2 in list3:
            worksheet.write_merge(row, row, 0, 1, rec2['name'])
            worksheet.write_merge(row, row, 2, 3, rec2['total'], bold_right)
            row += 1
        row += 2
        list4 = var.get("total_paid")
        worksheet.write_merge(row, row, 0, 3, "Total: " + " " + str(list4), b1)
        filename = ('Sale Detail Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.sales.detail.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        return{
            'type': 'ir.actions.act_window',
            'name': 'Sales Details Report',
            'res_id': export_id.id,
            'res_model': 'sh.sales.detail.xls',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }
