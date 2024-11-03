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


class SaleByCategoryXLS(models.Model):
    _name = 'sh.sale.category.xls'
    _description = 'Sale by Category Xls Report'
    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64, readonly=True)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.sale.category.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class SaleByCategoryWizard(models.TransientModel):
    _name = 'sh.sale.category.wizard'
    _description = 'Sale By Category Wizard'

    sh_start_date = fields.Datetime(
        'Start Date', required=True, default=fields.Datetime.now)
    sh_end_date = fields.Datetime(
        'End Date', required=True, default=fields.Datetime.now)
    sh_category_ids = fields.Many2many('product.category', string='Categories')
    company_ids = fields.Many2many(
        'res.company', default=lambda self: self.env.companies, string="Companies")

    @api.constrains('sh_start_date', 'sh_end_date')
    def _check_dates(self):
        if self.filtered(lambda c: c.sh_end_date and c.sh_start_date > c.sh_end_date):
            raise ValidationError(_('start date must be less than end date.'))

    def print_report(self):
        datas = self.read()[0]
        return self.env.ref('sh_sale_reports.sh_sale_by_category_action').report_action([], data=datas)

    def print_xls_report(self):
        workbook = xlwt.Workbook(encoding='utf-8')
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True,height 215;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold_center = xlwt.easyxf(
            'font:height 240,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center;')
        worksheet = workbook.add_sheet(
            'Sales By Product Category', bold_center)
        worksheet.write_merge(
            0, 1, 0, 8, 'Sales By Product Category', heading_format)
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
        worksheet.write_merge(2, 2, 0, 8, start_date + " to " + end_date, bold)
        worksheet.col(0).width = int(30 * 260)
        worksheet.col(1).width = int(30 * 260)
        worksheet.col(2).width = int(18 * 260)
        worksheet.col(3).width = int(18 * 260)
        worksheet.col(4).width = int(33 * 260)
        worksheet.col(5).width = int(15 * 260)
        worksheet.col(6).width = int(15 * 260)
        worksheet.col(7).width = int(15 * 260)
        sale_order_obj = self.env["sale.order"]
        category_order_dic = {}
        categories = False
        if self.sh_category_ids:
            categories = self.sh_category_ids
        else:
            categories = self.env['product.category'].sudo().search([])
        if categories:
            for category in categories:
                order_list = []
                domain = [
                    ("date_order", ">=", fields.Datetime.to_string(date_start)),
                    ("date_order", "<=", fields.Datetime.to_string(date_stop)),
                    ('state', 'in', ['sale', 'done'])
                ]
                if self.company_ids:
                    domain.append(
                        ('company_id', 'in', self.company_ids.ids))
                search_orders = sale_order_obj.sudo().search(domain)
                if search_orders:
                    for order in search_orders:
                        if order.order_line:
                            order_dic = {}
                            for line in order.order_line.sudo().filtered(lambda x: x.product_id.categ_id.id == category.id):
                                line_dic = {
                                    'order_number': order.name,
                                    'order_date': order.date_order.date(),
                                    'product': line.product_id.name_get()[0][1],
                                    'qty': line.product_uom_qty,
                                    'uom': line.product_uom.name,
                                    'sale_price': line.price_unit,
                                    'tax': line.price_tax,
                                    'sale_currency_id': line.currency_id.symbol
                                }
                                if order_dic.get(line.product_id.id, False):
                                    qty = order_dic.get(
                                        line.product_id.id)['qty']
                                    qty = qty + line.product_uom_qty
                                    line_dic.update({
                                        'qty': qty,
                                    })
                                order_dic.update(
                                    {line.product_id.id: line_dic})
                            for key, value in order_dic.items():
                                order_list.append(value)
                category_order_dic.update({category.display_name: order_list})
        row = 4
        if category_order_dic:
            for key in category_order_dic.keys():
                total_qty = 0.0
                total_price = 0.0
                total_tax = 0.0
                total_subtotal = 0.0
                total = 0.0
                worksheet.write_merge(
                    row, row, 0, 8, key, bold_center)
                row = row + 2
                worksheet.write(row, 0, "Order Number", bold)
                worksheet.write(row, 1, "Order Date", bold)
                worksheet.write(row, 2, "Product", bold)
                worksheet.write(row, 3, "Quantity", bold)
                worksheet.write(row, 4, "UOM", bold)
                worksheet.write(row, 5, "Price", bold)
                worksheet.write(row, 6, "Tax", bold)
                worksheet.write(row, 7, "Subtotal", bold)
                worksheet.write(row, 8, "Total", bold)
                row = row + 1
                for rec in category_order_dic[key]:
                    total_qty += rec.get('qty')
                    total_price += rec.get('sale_price')
                    total_tax += rec.get('tax')
                    total_subtotal += rec.get('qty', 0.0) * \
                        rec.get('sale_price', 0.0)
                    total += (rec.get('sale_price') *
                              rec.get('qty', '')) + rec.get('tax')
                    worksheet.write(row, 0, rec.get('order_number'), center)
                    worksheet.write(row, 1, str(rec.get('order_date')), center)
                    worksheet.write(row, 2, rec.get('product'), center)
                    worksheet.write(row, 3, str(
                        "{:.2f}".format(rec.get('qty'))), center)
                    worksheet.write(row, 4, rec.get('uom'), center)
                    worksheet.write(row, 5, str(rec.get(
                        'sale_currency_id')) + str("{:.2f}".format(rec.get('sale_price'))), center)
                    worksheet.write(row, 6, str(
                        rec.get('sale_currency_id')) + str("{:.2f}".format(rec.get('tax'))), center)
                    worksheet.write(row, 7, str(rec.get('sale_currency_id')) + str(
                        "{:.2f}".format(rec.get('sale_price') * rec.get('qty', ''))), center)
                    worksheet.write(row, 8, str(rec.get('sale_currency_id')) + str("{:.2f}".format(
                        (rec.get('sale_price') * rec.get('qty', '')) + rec.get('tax'))), center)
                    row = row + 1
                worksheet.write(row, 2, "Total", bold_center_total)
                worksheet.write(row, 3, "{:.2f}".format(
                    total_qty), bold_center_total)
                worksheet.write(row, 5, "{:.2f}".format(
                    total_price), bold_center_total)
                worksheet.write(row, 6, "{:.2f}".format(
                    total_tax), bold_center_total)
                worksheet.write(row, 7, "{:.2f}".format(
                    total_subtotal), bold_center_total)
                worksheet.write(row, 8, "{:.2f}".format(
                    total), bold_center_total)
                row = row + 2
        filename = ('Sales By Product Category' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.sale.category.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        fp.close()
        return{
            'type': 'ir.actions.act_window',
            'name': 'Sales by Product Category',
            'res_id': export_id.id,
            'res_model': 'sh.sale.category.xls',
            'view_mode': 'form',
            'target': 'new',
        }
