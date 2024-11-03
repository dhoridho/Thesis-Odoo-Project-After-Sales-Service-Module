# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import xlwt
import base64
from io import BytesIO
import pytz
from datetime import datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


class PurchaseReportXLS(models.Model):
    _name = 'sh.purchase.bill.summary.xls'
    _description = 'Purchase Bill Summary Xls Report'
    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64, readonly=True)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.purchase.bill.summary.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class PurchaseBillSummaryWizard(models.TransientModel):
    _name = 'sh.purchase.bill.summary.wizard'
    _description = 'Purchase Bill Summary Wizard'

    sh_start_date = fields.Datetime(
        'Start Date', required=True, default=fields.Datetime.now)
    sh_end_date = fields.Datetime(
        'End Date', required=True, default=fields.Datetime.now)
    sh_partner_ids = fields.Many2many(
        'res.partner', string='Vendors', required=True)
    sh_status = fields.Selection(
        [('both', 'Both'), ('open', 'Open'), ('paid', 'Paid')], string="Status", default='both')
    company_ids = fields.Many2many(
        'res.company', default=lambda self: self.env.companies, string="Companies")

    @api.constrains('sh_start_date', 'sh_end_date')
    def _check_dates(self):
        if self.filtered(lambda c: c.sh_end_date and c.sh_start_date > c.sh_end_date):
            raise ValidationError(_('start date must be less than end date.'))

    def print_report(self):
        datas = self.read()[0]
        return self.env.ref('sh_purchase_reports.sh_po_bill_summary_action').report_action([], data=datas)

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Purchase Bill Summary', bold_center)
        worksheet.write_merge(
            0, 1, 0, 6, 'Purchase Bill Summary', heading_format)
        left = xlwt.easyxf('align: horiz center;font:bold True')
        center = xlwt.easyxf('align: horiz center;')
        bold_center_total = xlwt.easyxf('align: horiz center;font:bold True')
        date_start = False
        date_stop = False
        if self.sh_start_date:
            date_start = fields.Datetime.from_string(self.sh_start_date)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            date_start = today.astimezone(pytz.timezone('UTC'))

        if self.sh_end_date:
            date_stop = fields.Datetime.from_string(self.sh_end_date)
            # avoid a date_stop smaller than date_start
            if (date_stop < date_start):
                date_stop = date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            date_stop = date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_start_date),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT) 
        end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.sh_end_date),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        worksheet.write_merge(2, 2, 0, 6, start_date + " to " + end_date, bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        vendor_order_dic = {}
        for partner_id in self.sh_partner_ids:
            order_list = []
            domain = [
                ("date_order", ">=", fields.Datetime.to_string(date_start)),
                ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                ("partner_id", "=", partner_id.id),
                ('state', 'in', ['purchase', 'done']),
            ]
            if self.sh_status == 'both':
                domain.append(('invoice_ids.state', 'in', ['posted']))
            elif self.sh_status == 'open':
                domain.append(('invoice_ids.state', 'in', ['posted']))
                domain.append(('invoice_ids.amount_residual', '!=', 0.0))
            elif self.sh_status == 'paid':
                domain.append(('invoice_ids.state', 'in', ['posted']))
                domain.append(('invoice_ids.amount_residual', '=', 0.0))
            if self.company_ids:
                domain.append(
                    ('company_id', 'in', self.company_ids.ids))
            search_orders = self.env['purchase.order'].sudo().search(domain)
            invoice_ids = []
            if search_orders:
                for order in search_orders:
                    if order.invoice_ids:
                        for invoice in order.invoice_ids:
                            if invoice.id not in invoice_ids:
                                invoice_ids.append(invoice.id)
                            order_dic = {
                                'order_number': order.name,
                                'order_date': order.date_order.date(),
                                'invoice_number': invoice.name,
                                'invoice_date': invoice.invoice_date,
                                'invoice_currency_id': invoice.currency_id.symbol,
                            }
                            if invoice.move_type == 'in_invoice':
                                order_dic.update({
                                    'invoice_amount': invoice.amount_total,
                                    'invoice_paid_amount': invoice.amount_total - invoice.amount_residual,
                                    'due_amount': invoice.amount_residual,
                                })
                            elif invoice.move_type == 'in_refund':
                                order_dic.update({
                                    'invoice_amount': -(invoice.amount_total),
                                    'invoice_paid_amount': -(invoice.amount_total - invoice.amount_residual),
                                    'due_amount': -(invoice.amount_residual),
                                })
                            order_list.append(order_dic)
            vendor_order_dic.update({partner_id.name_get()[0][1]: order_list})
        row = 4
        if vendor_order_dic:
            for key in vendor_order_dic.keys():
                worksheet.write_merge(
                    row, row, 0, 6, key, bold_center)
                row = row + 2
                total_amount_invoiced = 0.0
                total_amount_paid = 0.0
                total_amount_due = 0.0
                worksheet.write(row, 0, "Order Number", bold)
                worksheet.write(row, 1, "Order Date", bold)
                worksheet.write(row, 2, "Bill Number", bold)
                worksheet.write(row, 3, "Bill Date", bold)
                worksheet.write(row, 4, "Amount Billed", bold)
                worksheet.write(row, 5, "Amount Paid", bold)
                worksheet.write(row, 6, "Amount Due", bold)
                row = row + 1
                for rec in vendor_order_dic[key]:
                    worksheet.write(row, 0, rec.get('order_number'), center)
                    worksheet.write(row, 1, str(rec.get('order_date')), center)
                    worksheet.write(row, 2, rec.get('invoice_number'), center)
                    worksheet.write(row, 3, str(
                        rec.get('invoice_date')), center)
                    worksheet.write(row, 4, str(rec.get(
                        'invoice_currency_id')) + str("{:.2f}".format(rec.get('invoice_amount'))), center)
                    worksheet.write(row, 5, str(rec.get(
                        'invoice_currency_id')) + str("{:.2f}".format(rec.get('invoice_paid_amount'))), center)
                    worksheet.write(row, 6, str(rec.get(
                        'invoice_currency_id')) + str("{:.2f}".format(rec.get('due_amount'))), center)
                    total_amount_invoiced = total_amount_invoiced + \
                        rec.get('invoice_amount')
                    total_amount_paid = total_amount_paid + \
                        rec.get('invoice_paid_amount')
                    total_amount_due = total_amount_due + rec.get('due_amount')
                    row = row + 1
                worksheet.write(row, 3, "Total", left)
                worksheet.write(row, 4, "{:.2f}".format(
                    total_amount_invoiced), bold_center_total)
                worksheet.write(row, 5, "{:.2f}".format(
                    total_amount_paid), bold_center_total)
                worksheet.write(row, 6, "{:.2f}".format(
                    total_amount_due), bold_center_total)
                row = row + 2
        filename = ('Purchase Bill Summary' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.purchase.bill.summary.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Purchase Bill Summary',
            'res_id': export_id.id,
            'res_model': 'sh.purchase.bill.summary.xls',
            'view_mode': 'form',
            'target': 'new',
        }
