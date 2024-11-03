# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, api
from datetime import datetime,timedelta
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import xlwt
import base64
from io import BytesIO
import pytz
from odoo.exceptions import ValidationError


class DayWiseExcel(models.Model):
    _name = "sh.day.wise.sales.xls"
    _description = "Day wise Sales XLS"

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def so_day_wise_report(self):

        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=sh.day.wise.sales.xls&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class SaleOrderReport(models.Model):
    _name = 'sale.order.report'
    _description = 'Sale Order Report'

    @api.model
    def default_company_ids(self):
        is_allowed_companies = self.env.context.get(
            'allowed_company_ids', False)
        if is_allowed_companies:
            return is_allowed_companies
        return

    start_date = fields.Datetime("Start Date", required=True, readonly=False,default=fields.Datetime.now)
    end_date = fields.Datetime("End Date", required=True,
                           default=fields.Datetime.now, readonly=False)
    company_ids = fields.Many2many(
        'res.company', string='Companies', default=default_company_ids)

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        if self.filtered(lambda c: c.end_date and c.start_date > c.end_date):
            raise ValidationError(_('start date must be less than end date.'))

    def get_product(self):
        product_detail = []
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
        if self.start_date and self.end_date:
            if len(self.company_ids.ids) >= 1:
                self._cr.execute('''select pt.name as product_name,
                                        so.date_order as order_date,
                                        sum(sl.product_uom_qty) as sold_cnt
                                        from sale_order as so 
                                        left join sale_order_line as sl on so.id = sl.order_id
                                        left join product_product as pr on pr.id = sl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date(%s) and date(date_order) <= date(%s) and so.state in ('sale','done') and so.company_id in %s
                                        group by pt.name,so.date_order''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop), tuple(self.company_ids.ids)))
                product_detail = self._cr.dictfetchall()
            else:
                self._cr.execute('''select pt.name as product_name,
                                        so.date_order as order_date,
                                        sum(sl.product_uom_qty) as sold_cnt
                                        from sale_order as so 
                                        left join sale_order_line as sl on so.id = sl.order_id
                                        left join product_product as pr on pr.id = sl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date(%s) and date(date_order) <= date(%s) and so.state in ('sale','done')
                                        group by pt.name,so.date_order''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop)))
                product_detail = self._cr.dictfetchall()
            output_data = {}
            data_list = []
            final_list = []
            if len(product_detail) > 0:
                current_product = product_detail[0]['product_name']
                last_product = product_detail[-1]['product_name']
                count = 1
                for product_dic in product_detail:
                    if product_dic['product_name'] != current_product:
                        data_list.append(output_data)
                        output_data = {}
                        current_product = product_dic['product_name']
                        output_data['product'] = current_product
                        output_data['monday'] = None
                        output_data['tuesday'] = None
                        output_data['wednesday'] = None
                        output_data['thursday'] = None
                        output_data['friday'] = None
                        output_data['saturday'] = None
                        output_data['sunday'] = None

                        order_date = product_dic['order_date']
                        if order_date.weekday() == 0:
                            output_data['monday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 1:
                            output_data['tuesday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 2:
                            output_data['wednesday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 3:
                            output_data['thursday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 4:
                            output_data['friday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 5:
                            output_data['saturday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 6:
                            output_data['sunday'] = int(
                                product_dic['sold_cnt'])
                        if product_dic['product_name'] == last_product:
                            data_list.append(output_data)

                    else:
                        if count == 1:
                            count = 0
                            output_data = {}
                            current_product = product_dic['product_name']
                            output_data['product'] = current_product
                            order_date = product_dic['order_date']
                            output_data['monday'] = None
                            output_data['tuesday'] = None
                            output_data['wednesday'] = None
                            output_data['thursday'] = None
                            output_data['friday'] = None
                            output_data['saturday'] = None
                            output_data['sunday'] = None

                            if order_date.weekday() == 0:
                                output_data['monday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 1:
                                output_data['tuesday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 2:
                                output_data['wednesday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 3:
                                output_data['thursday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 4:
                                output_data['friday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 5:
                                output_data['saturday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 6:
                                output_data['sunday'] = int(
                                    product_dic['sold_cnt'])
                        else:
                            output_data['product'] = current_product
                            order_date = product_dic['order_date']
                            if order_date.weekday() == 0:
                                tmp = output_data['monday'] or 0
                                output_data['monday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 1:
                                tmp = output_data['tuesday'] or 0
                                output_data['tuesday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 2:
                                tmp = output_data['wednesday'] or 0
                                output_data['wednesday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 3:
                                tmp = output_data['thursday'] or 0
                                output_data['thursday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 4:
                                tmp = output_data['friday'] or 0
                                output_data['friday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 5:
                                tmp = output_data['saturday'] or 0
                                output_data['saturday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 6:
                                tmp = output_data['sunday'] or 0
                                output_data['sunday'] = tmp + \
                                    int(product_dic['sold_cnt'])

                            if product_dic['product_name'] == last_product:
                                data_list.append(output_data)
            for data in data_list:
                if data not in final_list:
                    final_list.append(data)
            return final_list

    def generate_report_data(self):
        return self.env.ref('sh_sale_reports.action_report_sale_order_day_wise_report').report_action(self)

    def print_sale_order_day_wise(self):
        workbook = xlwt.Workbook()
        heading_format = xlwt.easyxf(
            'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
        bold = xlwt.easyxf(
            'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
        center = xlwt.easyxf('font:bold True;align: horiz center')
        right = xlwt.easyxf('font:bold True;align: horiz right')
        worksheet = workbook.add_sheet(
            u'Sale Order Day Wise', cell_overwrite_ok=True)
        worksheet.write_merge(
            0, 1, 0, 8, 'Sales Order - Product Sold Day Wise', heading_format)
        user_tz = self.env.user.tz or pytz.utc
        local = pytz.timezone(user_tz)
        start_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.start_date),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT) 
        end_date = datetime.strftime(pytz.utc.localize(datetime.strptime(str(self.end_date),
        DEFAULT_SERVER_DATETIME_FORMAT)).astimezone(local),DEFAULT_SERVER_DATETIME_FORMAT)
        worksheet.write_merge(3, 3, 0, 0, "Start Date : ", bold)
        worksheet.write_merge(3, 3, 1, 1, start_date)
        worksheet.write_merge(3, 3, 6, 7, "End Date : ", bold)
        worksheet.write_merge(3, 3, 8, 8, end_date)
        product_detail = []

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

        if self.start_date and self.end_date:
            if len(self.company_ids.ids) >= 1:
                self._cr.execute('''select pt.name as product_name,
                                        so.date_order as order_date,
                                        sum(sl.product_uom_qty) as sold_cnt
                                        from sale_order as so 
                                        left join sale_order_line as sl on so.id = sl.order_id
                                        left join product_product as pr on pr.id = sl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date(%s) and date(date_order) <= date(%s) and so.state in ('sale','done') and so.company_id in %s
                                        group by pt.name,so.date_order''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop), tuple(self.company_ids.ids)))
                product_detail = self._cr.dictfetchall()
            else:
                self._cr.execute('''select pt.name as product_name,
                                        so.date_order as order_date,
                                        sum(sl.product_uom_qty) as sold_cnt
                                        from sale_order as so 
                                        left join sale_order_line as sl on so.id = sl.order_id
                                        left join product_product as pr on pr.id = sl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date(%s) and date(date_order) <= date(%s) and so.state in ('sale','done')
                                        group by pt.name,so.date_order''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop)))
                product_detail = self._cr.dictfetchall()
            output_data = {}
            data_list = []

            if len(product_detail) > 0:

                current_product = product_detail[0]['product_name']
                last_product = product_detail[-1]['product_name']
                count = 1
                for product_dic in product_detail:

                    if product_dic['product_name'] != current_product:
                        data_list.append(output_data)
                        output_data = {}
                        current_product = product_dic['product_name']
                        output_data['product'] = current_product
                        output_data['monday'] = None
                        output_data['tuesday'] = None
                        output_data['wednesday'] = None
                        output_data['thursday'] = None
                        output_data['friday'] = None
                        output_data['saturday'] = None
                        output_data['sunday'] = None

                        order_date = product_dic['order_date']
                        if order_date.weekday() == 0:
                            output_data['monday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 1:
                            output_data['tuesday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 2:
                            output_data['wednesday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 3:
                            output_data['thursday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 4:
                            output_data['friday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 5:
                            output_data['saturday'] = int(
                                product_dic['sold_cnt'])
                        elif order_date.weekday() == 6:
                            output_data['sunday'] = int(
                                product_dic['sold_cnt'])

                        if product_dic['product_name'] == last_product:
                            data_list.append(output_data)

                    else:
                        if count == 1:
                            count = 0
                            output_data = {}
                            current_product = product_dic['product_name']
                            output_data['product'] = current_product
                            order_date = product_dic['order_date']
                            output_data['monday'] = None
                            output_data['tuesday'] = None
                            output_data['wednesday'] = None
                            output_data['thursday'] = None
                            output_data['friday'] = None
                            output_data['saturday'] = None
                            output_data['sunday'] = None

                            if order_date.weekday() == 0:
                                output_data['monday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 1:
                                output_data['tuesday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 2:
                                output_data['wednesday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 3:
                                output_data['thursday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 4:
                                output_data['friday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 5:
                                output_data['saturday'] = int(
                                    product_dic['sold_cnt'])
                            elif order_date.weekday() == 6:
                                output_data['sunday'] = int(
                                    product_dic['sold_cnt'])
                        else:
                            output_data['product'] = current_product
                            order_date = product_dic['order_date']
                            if order_date.weekday() == 0:
                                tmp = output_data['monday'] or 0
                                output_data['monday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 1:
                                tmp = output_data['tuesday'] or 0
                                output_data['tuesday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 2:
                                tmp = output_data['wednesday'] or 0
                                output_data['wednesday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 3:
                                tmp = output_data['thursday'] or 0
                                output_data['thursday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 4:
                                tmp = output_data['friday'] or 0
                                output_data['friday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 5:
                                tmp = output_data['saturday'] or 0
                                output_data['saturday'] = tmp + \
                                    int(product_dic['sold_cnt'])
                            elif order_date.weekday() == 6:
                                tmp = output_data['sunday'] or 0
                                output_data['sunday'] = tmp + \
                                    int(product_dic['sold_cnt'])

                            if product_dic['product_name'] == last_product:
                                data_list.append(output_data)

        product = data_list
        final_list = []
        worksheet.col(0).width = int(25*260)
        worksheet.col(1).width = int(14*260)
        worksheet.col(2).width = int(14*260)
        worksheet.col(3).width = int(14*260)
        worksheet.col(4).width = int(14*260)
        worksheet.col(5).width = int(14*260)
        worksheet.col(6).width = int(14*260)
        worksheet.col(7).width = int(14*260)
        worksheet.col(8).width = int(14*260)

        worksheet.write(5, 0, "Product Name", bold)
        worksheet.write(5, 1, "Monday", bold)
        worksheet.write(5, 2, "Tuesday", bold)
        worksheet.write(5, 3, "Wednesday", bold)
        worksheet.write(5, 4, "Thursday", bold)
        worksheet.write(5, 5, "Friday", bold)
        worksheet.write(5, 6, "Saturday", bold)
        worksheet.write(5, 7, "Sunday", bold)
        worksheet.write(5, 8, "Total", bold)
        monday_total = 0
        tuesday_total = 0
        wednesday_total = 0
        thursday_total = 0
        friday_total = 0
        saturday_total = 0
        sunday_total = 0
        row = 6
        for data in product:
            if data not in final_list:
                final_list.append(data)
        for p in final_list:
            reg = 0
            worksheet.write(row, 0, p['product'])
            worksheet.write(row, 1, p['monday'])
            worksheet.write(row, 2, p['tuesday'])
            worksheet.write(row, 3, p['wednesday'])
            worksheet.write(row, 4, p['thursday'])
            worksheet.write(row, 5, p['friday'])
            worksheet.write(row, 6, p['saturday'])
            worksheet.write(row, 7, p['sunday'])
            if p['monday']:
                monday_total += p['monday']
                reg += p['monday']
            if p['tuesday']:
                tuesday_total += p['tuesday']
                reg += p['tuesday']
            if p['wednesday']:
                wednesday_total += p['wednesday']
                reg += p['wednesday']
            if p['thursday']:
                thursday_total += p['thursday']
                reg += p['thursday']
            if p['friday']:
                friday_total += p['friday']
                reg += p['friday']
            if p['saturday']:
                saturday_total += p['saturday']
                reg += p['saturday']
            if p['sunday']:
                sunday_total += p['sunday']
                reg += p['sunday']
            worksheet.write(row, 8, reg)
            row += 1
        row += 1
        worksheet.write(row, 0, "Total", center)
        worksheet.write(row, 1, monday_total, right)
        worksheet.write(row, 2, tuesday_total, right)
        worksheet.write(row, 3, wednesday_total, right)
        worksheet.write(row, 4, thursday_total, right)
        worksheet.write(row, 5, friday_total, right)
        worksheet.write(row, 6, saturday_total, right)
        worksheet.write(row, 7, sunday_total, right)
        worksheet.write(row, 8, monday_total+tuesday_total+wednesday_total +
                        thursday_total+friday_total+saturday_total+sunday_total, right)

        filename = ('Sale Order Day Wise Xls Report' + '.xls')
        fp = BytesIO()
        workbook.save(fp)

        export_id = self.env['sh.day.wise.sales.xls'].sudo().create({
            'excel_file': base64.encodestring(fp.getvalue()),
            'file_name': filename,
        })

        return{
            'type': 'ir.actions.act_window',
            'name': 'Day Wise Sales Report',
            'res_id': export_id.id,
            'res_model': 'sh.day.wise.sales.xls',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }
