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


class PurchaseAnalysisReportXLS(models.Model):
    _name = 'sh.purchase.analysis.xls'
    _description = 'Purchase Analysis Xls Report'
    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64, readonly=True)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.purchase.analysis.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class PurchaseAnalysisWizard(models.TransientModel):
    _name = 'sh.purchase.analysis.wizard'
    _description = 'Purchase Analysis Wizard'

    sh_start_date = fields.Datetime(
        'Start Date', required=True, default=fields.Datetime.now)
    sh_end_date = fields.Datetime(
        'End Date', required=True, default=fields.Datetime.now)
    sh_partner_ids = fields.Many2many(
        'res.partner', string='Vendors', required=True)
    sh_status = fields.Selection([('all', 'All'), ('draft', 'Draft'), ('sent', 'RFQ Sent'), (
        'purchase', 'Purchase Order'), ('done', 'Locked')], string="Status", default='all')
    report_by = fields.Selection(
        [('order', 'Purchase Order'), ('product', 'Products')], string='Report Print By', default='order')
    sh_product_ids = fields.Many2many('product.product', string='Products')
    company_ids = fields.Many2many(
        'res.company', default=lambda self: self.env.companies, string="Companies")

    @api.constrains('sh_start_date', 'sh_end_date')
    def _check_dates(self):
        if self.filtered(lambda c: c.sh_end_date and c.sh_start_date > c.sh_end_date):
            raise ValidationError(_('start date must be less than end date.'))

    def print_report(self):
        datas = self.read()[0]
        return self.env.ref('sh_purchase_reports.sh_vend_po_analysis_action').report_action([], data=datas)

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Vendor Purchase Analysis', bold_center)
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
        if self.report_by == 'order':
            worksheet.write_merge(
                0, 1, 0, 5, 'Vendor Purchase Analysis', heading_format)
            worksheet.write_merge(2, 2, 0, 5, start_date + " to " + end_date, bold)
        elif self.report_by == 'product':
            worksheet.write_merge(
                0, 1, 0, 6, 'Vendor Purchase Analysis', heading_format)
            worksheet.write_merge(2, 2, 0, 6, str(
                self.sh_start_date) + " to " + str(self.sh_end_date), bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        order_dic_by_orders = {}
        order_dic_by_products = {}
        for partner_id in self.sh_partner_ids:
            order_list = []
            domain = [
                ("date_order", ">=", fields.Datetime.to_string(date_start)),
                ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                ("partner_id", "=", partner_id.id),
            ]
            if self.sh_status == 'all':
                domain.append(('state', 'not in', ['cancel']))
            elif self.sh_status == 'draft':
                domain.append(('state', 'in', ['draft']))
            elif self.sh_status == 'sent':
                domain.append(('state', 'in', ['sent']))
            elif self.sh_status == 'purchase':
                domain.append(('state', 'in', ['purchase']))
            elif self.sh_status == 'done':
                domain.append(('state', 'in', ['done']))
            if self.company_ids:
                domain.append(
                    ('company_id', 'in', self.company_ids.ids))
            search_orders = self.env['purchase.order'].sudo().search(domain)
            if search_orders:
                for order in search_orders:
                    if self.report_by == 'order':
                        order_dic = {
                            'order_number': order.name,
                            'order_date': order.date_order.date(),
                            'user': order.user_id.name,
                            'purchase_amount': order.amount_total,
                            'purchase_currency_id': order.currency_id.symbol,
                        }
                        paid_amount = 0.0
                        if order.invoice_ids:
                            for invoice in order.invoice_ids:
                                if invoice.move_type == 'in_invoice':
                                    paid_amount += invoice.amount_total - invoice.amount_residual
                                elif invoice.move_type == 'in_refund':
                                    paid_amount += - \
                                        (invoice.amount_total -
                                         invoice.amount_residual)
                        order_dic.update({
                            'paid_amount': paid_amount,
                            'balance_amount': order.amount_total - paid_amount
                        })
                        order_list.append(order_dic)
                    elif self.report_by == 'product' and order.order_line:
                        lines = False
                        if self.sh_product_ids:
                            lines = order.order_line.sudo().filtered(
                                lambda x: x.product_id.id in self.sh_product_ids.ids)
                        else:
                            products = self.env['product.product'].sudo().search(
                                [])
                            lines = order.order_line.sudo().filtered(
                                lambda x: x.product_id.id in products.ids)
                        if lines:
                            for line in lines:
                                order_dic = {
                                    'order_number': line.order_id.name,
                                    'order_date': line.order_id.date_order.date(),
                                    'product_name': line.product_id.name_get()[0][1],
                                    'price': line.price_unit,
                                    'qty': line.product_uom_qty,
                                    'tax': line.price_tax,
                                    'subtotal': line.price_subtotal,
                                    'purchase_currency_id': order.currency_id.symbol,
                                }
                                order_list.append(order_dic)
            if self.report_by == 'order':
                order_dic_by_orders.update(
                    {partner_id.name_get()[0][1]: order_list})
            elif self.report_by == 'product':
                order_dic_by_products.update(
                    {partner_id.name_get()[0][1]: order_list})
        row = 4
        if self.report_by == 'order':
            if order_dic_by_orders:
                for key in order_dic_by_orders.keys():
                    worksheet.write_merge(
                        row, row, 0, 5, key, bold_center)
                    row = row + 2
                    total_purchase_amount = 0.0
                    total_amount_paid = 0.0
                    total_balance = 0.0
                    worksheet.write(row, 0, "Order Number", bold)
                    worksheet.write(row, 1, "Order Date", bold)
                    worksheet.write(row, 2, "Purchase Representative", bold)
                    worksheet.write(row, 3, "Purchase Amount", bold)
                    worksheet.write(row, 4, "Amount Paid", bold)
                    worksheet.write(row, 5, "Balance", bold)
                    row = row + 1
                    for rec in order_dic_by_orders[key]:
                        worksheet.write(row, 0, rec.get(
                            'order_number'), center)
                        worksheet.write(row, 1, str(
                            rec.get('order_date')), center)
                        worksheet.write(row, 2, rec.get('user'), center)
                        worksheet.write(row, 3, str(rec.get(
                            'purchase_currency_id'))+str("{:.2f}".format(rec.get('purchase_amount'))), center)
                        worksheet.write(row, 4, str(rec.get(
                            'purchase_currency_id')) + str("{:.2f}".format(rec.get('paid_amount'))), center)
                        worksheet.write(row, 5, str(rec.get(
                            'purchase_currency_id')) + str("{:.2f}".format(rec.get('balance_amount'))), center)
                        total_purchase_amount = total_purchase_amount + \
                            rec.get('purchase_amount')
                        total_amount_paid = total_amount_paid + \
                            rec.get('paid_amount')
                        total_balance = total_balance + \
                            rec.get('balance_amount')
                        row = row + 1
                    worksheet.write(row, 2, "Total", left)
                    worksheet.write(row, 3, "{:.2f}".format(
                        total_purchase_amount), bold_center_total)
                    worksheet.write(row, 4, "{:.2f}".format(
                        total_amount_paid), bold_center_total)
                    worksheet.write(row, 5, "{:.2f}".format(
                        total_balance), bold_center_total)
                    row = row + 2
        elif self.report_by == 'product':
            if order_dic_by_products:
                for key in order_dic_by_products.keys():
                    worksheet.write_merge(
                        row, row, 0, 6, key, bold_center)
                    row = row + 2
                    total_tax = 0.0
                    total_subtotal = 0.0
                    total_balance = 0.0
                    worksheet.write(row, 0, "Number", bold)
                    worksheet.write(row, 1, "Date", bold)
                    worksheet.write(row, 2, "Product", bold)
                    worksheet.write(row, 3, "Price", bold)
                    worksheet.write(row, 4, "Quantity", bold)
                    worksheet.write(row, 5, "Tax", bold)
                    worksheet.write(row, 6, "Subtotal", bold)
                    row = row + 1
                    for rec in order_dic_by_products[key]:
                        worksheet.write(row, 0, rec.get(
                            'order_number'), center)
                        worksheet.write(row, 1, str(
                            rec.get('order_date')), center)
                        worksheet.write(row, 2, rec.get(
                            'product_name'), center)
                        worksheet.write(row, 3, str(
                            rec.get('purchase_currency_id'))+str("{:.2f}".format(rec.get('price'))), center)
                        worksheet.write(row, 4, rec.get('qty'), center)
                        worksheet.write(row, 5, str(
                            rec.get('purchase_currency_id'))+str("{:.2f}".format(rec.get('tax'))), center)
                        worksheet.write(row, 6, str(rec.get(
                            'purchase_currency_id'))+str("{:.2f}".format(rec.get('subtotal'))), center)
                        total_tax = total_tax + rec.get('tax')
                        total_subtotal = total_subtotal + rec.get('subtotal')
                        row = row + 1
                    worksheet.write(row, 4, "Total", left)
                    worksheet.write(row, 5, "{:.2f}".format(
                        total_tax), bold_center_total)
                    worksheet.write(row, 6, "{:.2f}".format(
                        total_subtotal), bold_center_total)
                    row = row + 2
        filename = ('Vendor Purchase Analysis' + '.xls')
        fp = BytesIO()
        workbook.save(fp)
        export_id = self.env['sh.purchase.analysis.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Vendor Purchase Analysis',
            'res_id': export_id.id,
            'res_model': 'sh.purchase.analysis.xls',
            'view_mode': 'form',
            'target': 'new',
        }
