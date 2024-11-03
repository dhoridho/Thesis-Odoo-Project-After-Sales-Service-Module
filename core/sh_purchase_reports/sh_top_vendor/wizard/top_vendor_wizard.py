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


class TopVendorExcelExtended(models.Model):
    _name = "sh.top.vendor.excel.extended"
    _description = 'Excel Extended'

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def download_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.top.vendor.excel.extended&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class ShTcTopVendorWizard(models.TransientModel):
    _name = "sh.tv.top.vendor.wizard"
    _description = 'Top Vendors'

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
    date_to = fields.Datetime(string='To Date', required=True,
                          default=fields.Datetime.now)
    date_compare_from = fields.Datetime(string='Compare From Date',default=fields.Datetime.now)
    date_compare_to = fields.Datetime(
        string='Compare To Date', default=fields.Datetime.now)
    no_of_top_item = fields.Integer(
        string='No of Items', required=True, default=10)
    amount_total = fields.Monetary(string="Total Purchase Amount")
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    company_ids = fields.Many2many(
        'res.company', string="Company", default=default_company_ids)

    @api.constrains('date_from', 'date_to')
    def _check_from_to_dates(self):
        if self.filtered(lambda c: c.date_to and c.date_from > c.date_to):
            raise ValidationError(_('from date must be less than to date.'))

    @api.constrains('date_compare_from', 'date_compare_to')
    def _check_compare_from_to_dates(self):
        if self.filtered(lambda c: c.date_compare_to and c.date_compare_from and c.date_compare_from > c.date_compare_to):
            raise ValidationError(
                _('compare from date must be less than compare to date.'))

    def print_top_vendor_report(self):
        self.ensure_one()
        data = {}

        # we read self because we use from date and start date in our core bi logic.(in abstract model)
        data = self.read()[0]
        return self.env.ref('sh_purchase_reports.sh_tv_top_vendors_report_action').report_action([], data=data)

    def print_top_vendor_xls_report(self,):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        bold_center = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        left = xlwt.easyxf('align: horiz left')
        row = 1

        data = {}
        data = self.read()[0]
        data = dict(data or {})
        currency_id = False
        purchase_order_obj = self.env['purchase.order']
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
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(basic_date_start)),
            ('date_order', '<=', fields.Datetime.to_string(basic_date_stop)),
            ('state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))

        purchase_orders = purchase_order_obj.sudo().search(domain)
        partner_total_amount_dic = {}
        if purchase_orders:
            for order in purchase_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id.name)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id.name: order.amount_total})

        final_partner_list = []
        final_partner_amount_list = []
        if partner_total_amount_dic:
            # sort partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)
            counter = 0

            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_partner_list.append(tuple_item[0])
                elif data['amount_total'] == 0:
                    final_partner_list.append(tuple_item[0])

                final_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        ##################################
        # for Compare partner from to
        purchase_orders = False
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
        domain = [
            ('date_order', '>=', fields.Datetime.to_string(compare_date_start)),
            ('date_order', '<=', fields.Datetime.to_string(compare_date_stop)),
            ('state', 'in', ['purchase', 'done']),
        ]
        if data.get('company_ids', False):
            domain.append(('company_id', 'in', data.get('company_ids', False)))

        purchase_orders = purchase_order_obj.sudo().search(domain)

        partner_total_amount_dic = {}
        if purchase_orders:
            for order in purchase_orders.sorted(key=lambda o: o.partner_id.id):
                if order.currency_id:
                    currency_id = order.currency_id

                if partner_total_amount_dic.get(order.partner_id.name, False):
                    amount = partner_total_amount_dic.get(
                        order.partner_id.name)
                    amount += order.amount_total
                    partner_total_amount_dic.update(
                        {order.partner_id.name: amount})
                else:
                    partner_total_amount_dic.update(
                        {order.partner_id.name: order.amount_total})

        final_compare_partner_list = []
        final_compare_partner_amount_list = []
        if partner_total_amount_dic:
            # sort compare partner dictionary by descending order
            sorted_partner_total_amount_list = sorted(
                partner_total_amount_dic.items(), key=operator.itemgetter(1), reverse=True)

            counter = 0
            for tuple_item in sorted_partner_total_amount_list:
                if data['amount_total'] != 0 and tuple_item[1] >= data['amount_total']:
                    final_compare_partner_list.append(tuple_item[0])

                elif data['amount_total'] == 0:
                    final_compare_partner_list.append(tuple_item[0])

                final_compare_partner_amount_list.append(tuple_item[1])
                # only show record by user limit
                counter += 1
                if counter >= data['no_of_top_item']:
                    break

        # find lost and new partner here
        lost_partner_list = []
        new_partner_list = []
        if final_partner_list and final_compare_partner_list:
            for item in final_partner_list:
                if item not in final_compare_partner_list:
                    lost_partner_list.append(item)

            for item in final_compare_partner_list:
                if item not in final_partner_list:
                    new_partner_list.append(item)

#       finally update data dictionary
        if not currency_id:
            self.env.user.company_id.sudo().currency_id

        if self.type == 'basic':
            row = 1
            worksheet = workbook.add_sheet(
                u'Top Vendors', cell_overwrite_ok=True)
            worksheet.write_merge(0, 1, 0, 2, 'Top Vendors', heading_format)
            worksheet.write(3, 0, 'Date From: ', bold)
            worksheet.write(3, 1, basic_start_date)

            worksheet.write(4, 0, 'Date To: ', bold)
            worksheet.write(4, 1, basic_end_date)
            worksheet.col(0).width = int(25*260)
            worksheet.col(1).width = int(25*260)
            worksheet.col(2).width = int(14*260)
            row = 6
            worksheet.write(row, 0, "#", bold)
            worksheet.write(row, 1, "Vendor", bold)
            worksheet.write(row, 2, "Purchase Amount", bold)
            no = 0
            row = 7
            for i in range(len(final_partner_list)):
                no = no+1
                worksheet.write(row, 0, no, left)
                worksheet.write(row, 1, final_partner_list[i], left)
                worksheet.write(row, 2, final_partner_amount_list[i], left)
                row = row+1
        elif self.type == 'compare':
            row = 1
            worksheet = workbook.add_sheet(
                u'Top Vendors', cell_overwrite_ok=True)
            worksheet.write_merge(0, 1, 0, 6, 'Top Vendors', heading_format)
            worksheet.write(3, 0, 'Date From: ', bold)
            worksheet.write(3, 1, basic_start_date)
            worksheet.write(4, 0, 'Date To: ', bold)
            worksheet.write(4, 1, basic_end_date)
            worksheet.write(3, 5, 'Compare From Date: ', bold)
            worksheet.write(3, 6, compare_start_date)

            worksheet.write(4, 5, 'Compare To Date: ', bold)
            worksheet.write(4, 6, compare_end_date)
            row = 7
            worksheet.col(0).width = int(25*260)
            worksheet.col(1).width = int(25*260)
            worksheet.col(2).width = int(14*260)
            worksheet.col(3).width = int(25*260)
            worksheet.col(4).width = int(25*260)
            worksheet.col(5).width = int(14*260)
            worksheet.col(6).width = int(14*260)
            worksheet.write(row, 0, "#", bold)
            worksheet.write(row, 1, "Vendor", bold)
            worksheet.write(row, 2, "Purchase Amount", bold)
            worksheet.write(row, 4, "#", bold)
            worksheet.write(row, 5, "Compare Vendor", bold)
            worksheet.write(row, 6, "Purchase Amount", bold)
            row = 8
            for i in range(len(final_partner_list)):
                worksheet.write(row, 0, i+1, left)
                worksheet.write(row, 1, final_partner_list[i], left)
                worksheet.write(row, 2, final_partner_amount_list[i], left)
                row = row+1
            row = 8
            for j in range(len(final_compare_partner_list)):
                worksheet.write(row, 4, j+1, left)
                worksheet.write(row, 5, final_compare_partner_list[j], left)
                worksheet.write(
                    row, 6, final_compare_partner_amount_list[j], left)
                row = row+1
            row = row+2
            worksheet.write_merge(row, row, 0, 2, 'New Vendors', bold_center)
            worksheet.write_merge(row, row, 4, 6, 'Lost Vendors', bold_center)
            row = row+1
            for new in new_partner_list:
                worksheet.write_merge(row, row, 0, 2, new, left)
                row = row+1
            for lost in lost_partner_list:
                worksheet.write_merge(row, row, 4, 6, lost, left)
                row = row+1

        filename = ('Top Vendor Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.top.vendor.excel.extended'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        return{
            'type': 'ir.actions.act_window',
            'name': 'Top Vendors',
            'res_id': export_id.id,
            'res_model': 'sh.top.vendor.excel.extended',
            'view_mode': 'form',
            'target': 'new',
        }
