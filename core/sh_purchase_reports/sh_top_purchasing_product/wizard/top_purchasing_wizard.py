# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import operator
import xlwt
import base64
from io import BytesIO
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import pytz
from datetime import datetime,timedelta


class TopPurchasingProductExcelExtended(models.Model):
    _name = "sh.top.purchasing.excel.extended"
    _description = 'Excel Extended'

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.top.purchasing.excel.extended&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class ShTspTopPurchasingProductWizard(models.TransientModel):
    _name = "sh.tsp.top.purchasing.product.wizard"
    _description = 'Top purchasing product Transient model to just filter products'

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return

    type = fields.Selection([
        ('basic', 'Basic'),
        ('compare', 'Compare'),
    ], string="Report Type", default="basic")

    date_from = fields.Datetime(string='From Date', required=True,default=fields.Datetime.now)
    date_to = fields.Datetime(string='To Date', required=True,default=fields.Datetime.now)

    date_compare_from = fields.Datetime(string='Compare From Date',default=fields.Datetime.now)
    date_compare_to = fields.Datetime(
        string='Compare To Date',default=fields.Datetime.now)

    no_of_top_item = fields.Integer(
        string='No of Items', required=True, default=10)

    product_qty = fields.Float(string="Total Qty. Purchased")

    company_ids = fields.Many2many(
        'res.company', string="Companies", default=default_company_ids)

    @api.constrains('date_from', 'date_to')
    def _check_from_to_dates(self):
        if self.filtered(lambda c: c.date_to and c.date_from > c.date_to):
            raise ValidationError(_('from date must be less than to date.'))

    @api.constrains('date_compare_from', 'date_compare_to')
    def _check_compare_from_to_dates(self):
        if self.filtered(lambda c: c.date_compare_to and c.date_compare_from and c.date_compare_from > c.date_compare_to):
            raise ValidationError(
                _('compare from date must be less than compare to date.'))

    @api.constrains('no_of_top_item')
    def _check_no_of_top_item(self):
        if self.filtered(lambda c: c.no_of_top_item <= 0):
            raise ValidationError(
                _('No of items must be positive. or not zero'))

    def filter_top_purchasing_product(self):
        domain = [
            ('order_id.state', 'in', ['purchase', 'done']),
        ]
        basic_date_start = False
        basic_date_stop = False
        if self.date_from:
            basic_date_start = fields.Datetime.from_string(self.date_from)
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            basic_date_start = today.astimezone(pytz.timezone('UTC'))

        if self.date_to:
            basic_date_stop = fields.Datetime.from_string(self.date_to)
            # avoid a date_stop smaller than date_start
            if (basic_date_stop < basic_date_start):
                basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        if self.company_ids:
            domain.append(('order_id.company_id', 'in', self.company_ids.ids))
        if self.date_from:
            domain.append(('order_id.date_order', '>=', fields.Datetime.to_string(basic_date_start)))
        if self.date_to:
            domain.append(('order_id.date_order', '<=', fields.Datetime.to_string(basic_date_stop)))

        # search order line product and add into product_qty_dictionary
        search_order_lines = self.env['purchase.order.line'].sudo().search(
            domain)
        product_qty_dic = {}
        if search_order_lines:
            for line in search_order_lines.sorted(key=lambda r: r.product_id.id):
                if product_qty_dic.get(line.product_id.id, False):
                    qty = product_qty_dic.get(line.product_id.id)
                    qty += line.product_qty
                    product_qty_dic.update({line.product_id.id: qty})
                else:
                    product_qty_dic.update(
                        {line.product_id.id: line.product_qty})

        # remove all the old  records before creating new one.
        top_purchasing_product_obj = self.env['sh.tsp.top.purchasing.product']
        search_records = top_purchasing_product_obj.sudo().search([])
        if search_records:
            search_records.unlink()

        if product_qty_dic:
            # sort product qty dictionary by descending order
            sorted_product_qty_list = sorted(
                product_qty_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0
            for tuple_item in sorted_product_qty_list:
                top_purchasing_product_obj.sudo().create({
                    'product_id': tuple_item[0],
                    'qty': tuple_item[1]
                })
                # only create record by user limit
                counter += 1
                if counter >= self.no_of_top_item:
                    break

    def print_top_purchasing_product_report(self):
        self.ensure_one()
        # we read self because we use from date and start date in our core bi logic.(in abstract model)
        data = self.read()[0]

        return self.env.ref('sh_purchase_reports.sh_top_purchasing_product_report_action').report_action([], data=data)

    def print_top_purchasing_product_xls_report(self):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold_center = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        left = xlwt.easyxf('align: horiz left')
        row = 1

        worksheet = workbook.add_sheet(
            u'Top Purchasing Products', cell_overwrite_ok=True)
        if self.type == 'basic':
            worksheet.write_merge(
                0, 1, 0, 2, 'Top Purchasing Products', heading_format)
        if self.type == 'compare':
            worksheet.write_merge(
                0, 1, 0, 6, 'Top Purchasing Products', heading_format)
        data = self.read()[0]
        data = dict(data or {})
        basic_date_start = False
        basic_date_stop = False
        if data['date_from']:
            basic_date_start = fields.Datetime.from_string(data['date_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            basic_date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_to']:
            basic_date_stop = fields.Datetime.from_string(data['date_to'])
            # avoid a date_stop smaller than date_start
            if (basic_date_stop < basic_date_start):
                basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            basic_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        basic_start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.date_from),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT) 
        basic_end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.date_to),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        if self.type == 'basic' or self.type == 'compare':
            worksheet.write(3, 0, 'Date From: ', bold)
            worksheet.write(3, 1, basic_start_date)

            worksheet.write(4, 0, 'Date To: ', bold)
            worksheet.write(4, 1, basic_end_date)

        purchase_order_line_obj = self.env['purchase.order.line']
        ##################################
        # for product from to
        domain = [
            ('order_id.state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('order_id.company_id', 'in',
                           data.get('company_ids', False)))
        if data.get('date_from', False):
            domain.append(('order_id.date_order', '>=', fields.Datetime.to_string(basic_date_start)))
        if data.get('date_to', False):
            domain.append(('order_id.date_order', '<=', fields.Datetime.to_string(basic_date_stop)))

        # search order line product and add into product_qty_dictionary
        search_order_lines = purchase_order_line_obj.sudo().search(domain)

        product_total_qty_dic = {}
        if search_order_lines:
            for line in search_order_lines.sorted(key=lambda o: o.product_id.id):

                if product_total_qty_dic.get(line.product_id.name, False):
                    qty = product_total_qty_dic.get(line.product_id.name)
                    qty += line.product_qty
                    product_total_qty_dic.update({line.product_id.name: qty})
                else:
                    product_total_qty_dic.update(
                        {line.product_id.name: line.product_qty})

        final_product_list = []
        final_product_qty_list = []
        if product_total_qty_dic:
            # sort partner dictionary by descending order
            sorted_product_total_qty_list = sorted(
                product_total_qty_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0
            if self.type == 'basic' or self.type == 'compare':
                worksheet.col(0).width = int(25 * 260)
                worksheet.col(1).width = int(25 * 260)
                worksheet.col(2).width = int(14 * 260)

                worksheet.write(6, 0, "#", bold)
                worksheet.write(6, 1, "Product", bold)
                worksheet.write(6, 2, "Qty Purchased", bold)
                row = 6
            no = 0
            for tuple_item in sorted_product_total_qty_list:
                no += 1
                row += 1
                if data['product_qty'] != 0 and tuple_item[1] >= data['product_qty']:
                    final_product_list.append(tuple_item[0])
                    if self.type == 'basic' or self.type == 'compare':
                        for product in final_product_list:
                            worksheet.write(row, 0, no, left)
                            worksheet.write(row, 1, product)

                elif data['product_qty'] == 0:
                    final_product_list.append(tuple_item[0])
                    if self.type == 'basic' or self.type == 'compare':
                        for product in final_product_list:
                            worksheet.write(row, 0, no, left)
                            worksheet.write(row, 1, product)

                final_product_qty_list.append(tuple_item[1])
                if self.type == 'basic' or self.type == 'compare':
                    for product_qty in final_product_qty_list:
                        worksheet.write(row, 2, product_qty)
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break
        compare_date_start = False
        compare_date_stop = False
        if data['date_compare_from']:
            compare_date_start = fields.Datetime.from_string(data['date_compare_from'])
        else:
            # start by default today 00:00:00
            user_tz = pytz.timezone(self.env.context.get('tz') or self.env.user.tz or 'UTC')
            today = user_tz.localize(fields.Datetime.from_string(fields.Date.context_today(self)))
            compare_date_start = today.astimezone(pytz.timezone('UTC'))

        if data['date_compare_to']:
            compare_date_stop = fields.Datetime.from_string(data['date_compare_to'])
            # avoid a date_stop smaller than date_start
            if (compare_date_stop < compare_date_start):
                compare_date_stop = compare_date_start + timedelta(days=1, seconds=-1)
        else:
            # stop by default today 23:59:59
            compare_date_stop = basic_date_start + timedelta(days=1, seconds=-1)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        compare_start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.date_compare_from),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT) 
        compare_end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.date_compare_to),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        ##################################
        # for Compare product from to
        if self.type == 'compare':

            worksheet.write(3, 5, 'Compare From Date: ', bold)
            worksheet.write(3, 6, compare_start_date)

            worksheet.write(4, 5, 'Compare To Date: ', bold)
            worksheet.write(4, 6, compare_end_date)
        search_order_lines = False
        domain = [
            ('order_id.state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('order_id.company_id', 'in',
                           data.get('company_ids', False)))
        if data.get('date_compare_from', False):
            domain.append(('order_id.date_order', '>=',
                           fields.Datetime.to_string(compare_date_start)))
        if data.get('date_compare_to', False):
            domain.append(('order_id.date_order', '<=',
                           fields.Datetime.to_string(compare_date_stop)))

        search_order_lines = purchase_order_line_obj.sudo().search(domain)

        product_total_qty_dic = {}
        if search_order_lines:
            for line in search_order_lines.sorted(key=lambda o: o.product_id.id):

                if product_total_qty_dic.get(line.product_id.name, False):
                    qty = product_total_qty_dic.get(line.product_id.name)
                    qty += line.product_qty
                    product_total_qty_dic.update({line.product_id.name: qty})
                else:
                    product_total_qty_dic.update(
                        {line.product_id.name: line.product_qty})

        final_compare_product_list = []
        final_compare_product_qty_list = []
        if product_total_qty_dic:
            # sort partner dictionary by descending order
            sorted_product_total_qty_list = sorted(
                product_total_qty_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0
            if self.type == 'compare':
                worksheet.col(4).width = int(25 * 260)
                worksheet.col(5).width = int(25 * 260)
                worksheet.col(6).width = int(14 * 260)

                worksheet.write(6, 4, "#", bold)
                worksheet.write(6, 5, "Compare Product", bold)
                worksheet.write(6, 6, "Qty Purchased", bold)

                row = 6
            no = 0
            for tuple_item in sorted_product_total_qty_list:
                no += 1
                row += 1
                if data['product_qty'] != 0 and tuple_item[1] >= data['product_qty']:
                    final_compare_product_list.append(tuple_item[0])
                    if self.type == 'compare':
                        for compare_partner in final_compare_product_list:
                            worksheet.write(row, 4, no, left)
                            worksheet.write(row, 5, compare_partner)
                elif data['product_qty'] == 0:
                    final_compare_product_list.append(tuple_item[0])
                    if self.type == 'compare':
                        for compare_partner in final_compare_product_list:
                            worksheet.write(row, 4, no, left)
                            worksheet.write(row, 5, compare_partner)

                final_compare_product_qty_list.append(tuple_item[1])
                if self.type == 'compare':
                    for compare_product_qty in final_compare_product_qty_list:
                        worksheet.write(row, 6, compare_product_qty)
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        row += 2
        # find lost and new partner here
        lost_product_list = []
        new_product_list = []

        if self.type == 'compare':
            worksheet.write_merge(row, row, 0, 2, 'New Products', bold_center)
            worksheet.write_merge(row, row, 4, 6, 'Lost Products', bold_center)
            row = row + 1
            row_after_heading = row
            if final_product_list and final_compare_product_list:
                for item in final_compare_product_list:
                    if item not in final_product_list:
                        new_product_list.append(item)
                for new in new_product_list:
                    worksheet.write_merge(row, row, 0, 2, new)
                    row = row+1
                row = row_after_heading
                for item in final_product_list:
                    if item not in final_compare_product_list:
                        lost_product_list.append(item)
                for lost in lost_product_list:
                    worksheet.write_merge(row, row, 4, 6, lost)
                    row = row+1

        filename = ('Top Purchasing Products Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.top.purchasing.excel.extended'].sudo().create({
            'excel_file': base64.encodebytes(fp.getvalue()),
            'file_name': filename,
        })

        return{
            'type': 'ir.actions.act_window',
            'name': 'Top Purchasing Products',
            'res_id': export_id.id,
            'res_model': 'sh.top.purchasing.excel.extended',
            'view_mode': 'form',
            'target': 'new',
        }
