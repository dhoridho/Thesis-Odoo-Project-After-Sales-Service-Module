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


class DayPurchaseWiseExcelExtended(models.Model):
    _name = "excel.extended"
    _description = 'Day Purchase Wise Excel Extended'

    excel_file = fields.Binary('Download report Excel')
    file_name = fields.Char('Excel File', size=64)

    def po_day_wise_report(self):
        return{
            'type': 'ir.actions.act_url',
            'url': 'web/content/?model=excel.extended&field=excel_file&download=true&id=%s&filename=%s' % (self.id, self.file_name),
            'target': 'new',
        }


class PurchaseOrderReport(models.Model):
    _name = 'purchase.order.report'
    _description = 'Purchase Order Report'

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
        for rec in self:
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
            if rec.start_date and rec.end_date:
                if len(rec.company_ids.ids) >= 1:
                    rec._cr.execute('''CREATE EXTENSION IF NOT EXISTS tablefunc;
                                        select * from crosstab (
                                        'select pt.name as product_name,
                                        to_char(po.date_order,''day'') as order_date,
                                        sum(case when pt.name is not null then 1 else 0 end) as purchase_cnt
                                        from purchase_order as po 
                                        left join purchase_order_line as pl on po.id = pl.order_id
                                        left join product_product as pr on pr.id = pl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date('%s') and date(date_order) <= date('%s') and po.company_id in %s and 
                                        po.state in (''purchase'',''done'')
                                        group by pt.name,to_char(po.date_order,''day'')
                                        order by 1,2'
                        ,'SELECT to_char(date ''2007-01-01'' + (n || ''day'')::interval, ''day'') As short_mname FROM generate_series(0,6) n'                
                        )AS Final(product text,monday Int,tuesday Int,wednesday Int,thursday Int,friday Int,saturday Int,sunday Int);''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop), tuple(rec.company_ids.ids)))

                    product_detail = rec._cr.dictfetchall()
                else:
                    rec._cr.execute('''CREATE EXTENSION IF NOT EXISTS tablefunc;
                                        select * from crosstab (
                                        'select pt.name as product_name,
                                        to_char(po.date_order,''day'') as order_date,
                                        sum(case when pt.name is not null then 1 else 0 end) as purchase_cnt
                                        from purchase_order as po 
                                        left join purchase_order_line as pl on po.id = pl.order_id
                                        left join product_product as pr on pr.id = pl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date('%s') and date(date_order) <= date('%s') and 
                                        po.state in (''purchase'',''done'')
                                        group by pt.name,to_char(po.date_order,''day'')
                                        order by 1,2'
                        ,'SELECT to_char(date ''2007-01-01'' + (n || ''day'')::interval, ''day'') As short_mname FROM generate_series(0,6) n'                
                        )AS Final(product text,monday Int,tuesday Int,wednesday Int,thursday Int,friday Int,saturday Int,sunday Int);''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop)))

                    product_detail = rec._cr.dictfetchall()
            return product_detail

    def generate_report_data(self):

        return self.env.ref('sh_purchase_reports.action_report_purchase_order_day_wise_report').report_action(self)

    def print_purchase_order_day_wise(self):
        for data in self:
            workbook = xlwt.Workbook()
            heading_format = xlwt.easyxf(
                'font:height 300,bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
            bold = xlwt.easyxf(
                'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz left')
            bold_center = xlwt.easyxf(
                'font:bold True;pattern: pattern solid, fore_colour gray25;align: horiz center')
            center = xlwt.easyxf('font:bold True;align: horiz center')
            right = xlwt.easyxf('font:bold True;align: horiz right')
            left = xlwt.easyxf('align: horiz left')
            row = 1

            worksheet = workbook.add_sheet(
                u'Purchase Order Day Wise', cell_overwrite_ok=True)
            worksheet.write_merge(
                0, 1, 0, 8, 'Purchase Order - Product Purchased Day Wise', heading_format)
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
            if data.start_date and data.end_date:
                if len(data.company_ids.ids) >= 1:
                    data._cr.execute('''CREATE EXTENSION IF NOT EXISTS tablefunc;
                                        select * from crosstab (
                                        'select pt.name as product_name,
                                        to_char(po.date_order,''day'') as order_date,
                                        sum(case when pt.name is not null then 1 else 0 end) as purchase_cnt
                                        from purchase_order as po 
                                        left join purchase_order_line as pl on po.id = pl.order_id
                                        left join product_product as pr on pr.id = pl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date('%s') and date(date_order) <= date('%s') and po.company_id in %s and 
                                        po.state in (''purchase'',''done'')
                                        group by pt.name,to_char(po.date_order,''day'')
                                        order by 1,2'
                        ,'SELECT to_char(date ''2007-01-01'' + (n || ''day'')::interval, ''day'') As short_mname FROM generate_series(0,6) n'                
                        )AS Final(product text,monday Int,tuesday Int,wednesday Int,thursday Int,friday Int,saturday Int,sunday Int);''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop), tuple(data.company_ids.ids)))

                    product_detail = data._cr.dictfetchall()
                else:
                    data._cr.execute('''CREATE EXTENSION IF NOT EXISTS tablefunc;
                                        select * from crosstab (
                                        'select pt.name as product_name,
                                        to_char(po.date_order,''day'') as order_date,
                                        sum(case when pt.name is not null then 1 else 0 end) as purchase_cnt
                                        from purchase_order as po 
                                        left join purchase_order_line as pl on po.id = pl.order_id
                                        left join product_product as pr on pr.id = pl.product_id
                                        left join product_template as pt on  pr.product_tmpl_id = pt.id
                                        where date(date_order) >= date('%s') and date(date_order) <= date('%s') and 
                                        po.state in (''purchase'',''done'')
                                        group by pt.name,to_char(po.date_order,''day'')
                                        order by 1,2'
                        ,'SELECT to_char(date ''2007-01-01'' + (n || ''day'')::interval, ''day'') As short_mname FROM generate_series(0,6) n'                
                        )AS Final(product text,monday Int,tuesday Int,wednesday Int,thursday Int,friday Int,saturday Int,sunday Int);''', (fields.Datetime.to_string(date_start), fields.Datetime.to_string(date_stop)))

                    product_detail = data._cr.dictfetchall()
            product = product_detail
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
            row = 6
            reg = 0
            for p in product:
                worksheet.write(row, 0, p['product'])
                worksheet.write(row, 1, p['monday'])
                worksheet.write(row, 2, p['tuesday'])
                worksheet.write(row, 3, p['wednesday'])
                worksheet.write(row, 4, p['thursday'])
                worksheet.write(row, 5, p['friday'])
                worksheet.write(row, 6, p['saturday'])
                worksheet.write(row, 7, p['sunday'])
                if p['monday']:
                    worksheet.write(row, 8, reg+p['monday'])
                if p['tuesday']:
                    worksheet.write(row, 8, reg+p['tuesday'])
                if p['wednesday']:
                    worksheet.write(row, 8, reg+p['wednesday'])
                if p['thursday']:
                    worksheet.write(row, 8, reg+p['thursday'])
                if p['friday']:
                    worksheet.write(row, 8, reg+p['friday'])
                if p['saturday']:
                    worksheet.write(row, 8, reg+p['saturday'])
                if p['sunday']:
                    worksheet.write(row, 8, reg+p['sunday'])
                row += 1
            row += 1
            worksheet.write(row, 0, "Total", center)
            reg1 = 0
            reg2 = 0
            for i in product:
                if i['monday']:
                    reg1 += i['monday']
                    worksheet.write(row, 1, reg1, right)
                else:
                    worksheet.write(row, 1, 0, right)
                if i['tuesday']:
                    reg1 += i['tuesday']
                    worksheet.write(row, 2, reg1, right)
                else:
                    worksheet.write(row, 2, 0, right)
                if i['wednesday']:
                    reg1 += i['wednesday']
                    worksheet.write(row, 3, reg1, right)
                else:
                    worksheet.write(row, 3, 0, right)
                if i['thursday']:
                    reg1 += i['thursday']
                    worksheet.write(row, 4, reg1, right)
                else:
                    worksheet.write(row, 4, 0, right)
                if i['friday']:
                    reg1 += i['friday']
                    worksheet.write(row, 5, reg1, right)
                else:
                    worksheet.write(row, 5, 0, right)
                if i['saturday']:
                    reg1 += i['saturday']
                    worksheet.write(row, 6, reg1, right)
                else:
                    worksheet.write(row, 6, 0, right)
                if i['sunday']:
                    reg1 += i['sunday']
                    worksheet.write(row, 7, reg1, right)
                else:
                    worksheet.write(row, 7, 0, right)

                if i['monday']:
                    reg2 += i['monday']
                if i['tuesday']:
                    reg2 += i['tuesday']
                if i['wednesday']:
                    reg2 += i['wednesday']
                if i['thursday']:
                    reg2 += i['thursday']
                if i['friday']:
                    reg2 += i['friday']
                if i['saturday']:
                    reg2 += i['saturday']
                if i['sunday']:
                    reg2 += i['sunday']
                worksheet.write(row, 8, reg2, right)

            filename = ('Purchase Order Day Wise Xls Report' + '.xls')
            fp = BytesIO()
            workbook.save(fp)

            export_id = data.env['excel.extended'].sudo().create({
                'excel_file': base64.encodestring(fp.getvalue()),
                'file_name': filename,
            })

            return{
                'type': 'ir.actions.act_window',
                'name': 'Day Wise Purchase Report',
                'res_id': export_id.id,
                'res_model': 'excel.extended',
                'view_type': 'form',
                'view_mode': 'form',
                'target': 'new',
            }
