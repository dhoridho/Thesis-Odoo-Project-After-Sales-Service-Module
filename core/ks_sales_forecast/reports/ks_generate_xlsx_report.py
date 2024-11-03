import pytz
from odoo import models, _
from io import BytesIO
from odoo.tools.misc import xlsxwriter
from dateutil.relativedelta import relativedelta


class KsSalesForecast(models.Model):
    _inherit = 'ks.sales.forecast'

    def _ks_get_historic_data_from_database(self, unit, forecast_id, product_id, start_date, end_date):
        query = """
                select date_trunc(%(unit)s, res.ks_date) as date,
                sum(res.ks_value) from ks_sales_forecast_result as res 
                where res.ks_forecast_id = %(forecast_uid)s and res.ks_product_id = %(product_uid)s
                and res.ks_date >= %(start_date)s and res.ks_date <= %(end_date)s
                group by date,res.ks_value order by date
                """
        if unit == 'year':
            start_date = start_date + relativedelta(month=1, day=1)
        elif unit == 'month':
            start_date = start_date + relativedelta(day=1)

        self.env.cr.execute(query, {
            'unit': unit,
            'forecast_uid': forecast_id,
            'product_uid': product_id,
            'start_date': start_date,
            'end_date': end_date
        })
        result = self.env.cr.fetchall()
        ks_result = []
        for rec in result:
            if not [i for i in ks_result if rec[0] in i]:
                ks_result.append(rec)
            elif [i for i in ks_result if rec[0] in i]:
                sale_data = [i for i in ks_result if rec[0] in i]
                updated_data = list(sale_data[0])
                updated_data[1] += rec[1]
                sale_data = tuple(updated_data)
                ks_result[-1] = sale_data
        return ks_result

    def _ks_get_future_data_from_database(self, unit, forecast_id, product_id, start_date):
        query = """
                select date_trunc(%(unit)s, res.ks_date) as date,
                res.ks_value from ks_sales_forecast_result as res
                where res.ks_forecast_id = %(forecast_uid)s and res.ks_product_id = %(product_uid)s
                and res.ks_date > %(start_date)s group by date, res.ks_value order by date
        """

        self.env.cr.execute(query, {
            'unit': unit,
            'forecast_uid': forecast_id,
            'product_uid': product_id,
            'start_date': start_date,
        })
        result = self.env.cr.fetchall()
        return result

    def _ks_get_data_to_reportify(self):
        if self.ks_forecast_base == 'all':
            ks_report_products = self.env['ks.sales.forecast.result'].search([('ks_forecast_id', '=', self.id)]).ks_product_id
        else:
            ks_report_products = self.ks_product_ids
        ks_sale_data = {}
        user_tz = pytz.timezone(self.env.user.tz)
        ks_start_date = pytz.utc.localize(self.ks_start_date).astimezone(user_tz)
        ks_end_date = pytz.utc.localize(self.ks_end_date).astimezone(user_tz)
        for product in ks_report_products:
            ks_sale_data[product.display_name] = {'Past Date': [], 'Past Sales': [], "Future Date": [],
                                                  "Future Sales": []}
            historic_data = self._ks_get_historic_data_from_database(unit=self.ks_forecast_period,
                                                                     forecast_id=self.id,
                                                                     product_id=product.id,
                                                                     start_date=ks_start_date.date(),
                                                                     end_date=ks_end_date.date())
            for data in historic_data:
                ks_sale_data[product.display_name]['Past Date'].append(data[0].date())
                ks_sale_data[product.display_name]['Past Sales'].append(data[-1])

            future_data = self._ks_get_future_data_from_database(unit=self.ks_forecast_period,
                                                                 forecast_id=self.id,
                                                                 product_id=product.id,
                                                                 start_date=self.ks_end_date.date())
            for data in future_data:
                ks_sale_data[product.display_name]["Future Date"].append(data[0].date())
                ks_sale_data[product.display_name]["Future Sales"].append(data[-1])

        return ks_sale_data

    sales_data = {'product_name': {'past date': [], 'past_sales': [], 'upcoming_dates': [], 'forecasted_sales': []}}

    def _ks_generate_xlsx_report(self, workbook):
        merge_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'font_size': 26,
            'bold': True})
        raw_data = self._ks_get_data_to_reportify()
        format_sub_head = workbook.add_format({'font_size': 12, 'bold': True, 'align': 'center'})
        format_sub_head.set_border()
        format_sub_head.set_text_wrap()
        format_product_names = workbook.add_format()
        format_product_names.set_border()
        format_product_names.set_text_wrap()
        format_product_names.set_align('center')
        format_h_date = workbook.add_format()
        format_h_date.set_border()
        format_h_date.set_text_wrap()
        format_h_date.set_align('center')
        format_h_date.set_font_color('#800000')
        format_h_value = workbook.add_format()
        format_h_value.set_text_wrap()
        format_h_value.set_border()
        format_h_value.set_align('center')
        format_h_value.set_font_color('#800000')
        format_f_date = workbook.add_format()
        format_f_date.set_text_wrap()
        format_f_date.set_border()
        format_f_date.set_align('center')
        format_f_date.set_font_color('#008000')
        format_f_value = workbook.add_format()
        format_f_value.set_text_wrap()
        format_f_value.set_border()
        format_f_value.set_align('center')
        format_f_value.set_font_color('#008000')

        format_merge = workbook.add_format({'border': 1,
                                            'align': 'center',
                                            'font_size': 15,
                                            'bold': True})
        model_format = workbook.add_format({
            'border': 1,
            'align': 'center',
            'font_size': 15
        })

        ks_forecast_model = ''
        if self.ks_predicted_forecast_method or self.ks_default_forecast_method:
            ks_forecast_model = self.ks_predicted_forecast_method.upper() if self.ks_predicted_forecast_method else self.ks_default_forecast_method.upper()
        sheet = workbook.add_worksheet("Sales Forecast")
        sheet.merge_range(0, 0, 0, 4, "Sales Forecast Report", merge_format)
        sheet.merge_range(1, 0, 1, 4, "Forecasting model used :- " + str(ks_forecast_model), model_format)
        sheet.merge_range(2, 1, 2, 2, "Historical", format_merge)
        sheet.merge_range(2, 3, 2, 4, "Forecasted", format_merge)
        if not self.ks_is_predicted:
            sheet.merge_range(3, 0, 3, 4, "Data not Found, Probably you have not predicted the sales", model_format)
        if self.ks_is_predicted:
            sub_heads = ["Product Name", "Date", "Sales",
                         "Date", "Sales"]
            for i in range(len(sub_heads)):
                if i == 0:
                    sheet.merge_range(2, 0, 3, 0, sub_heads[0], format_sub_head)
                    sheet.set_column(0, 0, 20)
                    continue
                sheet.write(3, i, sub_heads[i], format_sub_head)
                sheet.set_column(i, i, 15)

            product_index = h_date_index = h_value_index = f_date_index = f_value_index = 4
            for key, values in raw_data.items():
                parent_key = key
                sheet.write(product_index, 0, key, format_product_names)
                for key, value in values.items():
                    if key == "Past Date":
                        for item in value:
                            sheet.write(h_date_index, 1, str(item), format_h_date)
                            h_date_index += 1
                    elif key == "Past Sales":
                        for item in value:
                            sheet.write(h_value_index, 2, str(round(item, 2)), format_h_value)
                            h_value_index += 1
                    elif key == "Future Date":
                        for item in value:
                            sheet.write(f_date_index, 3, str(item), format_f_date)
                            f_date_index += 1
                    elif key == 'Future Sales':
                        for item in value:
                            sheet.write(f_value_index, 4, str(round(item, 2)), format_f_value)
                            f_value_index += 1
                if abs(h_date_index - f_date_index) != 0:
                    merge_format = workbook.add_format({
                        'border': 1,
                        'align': 'vcenter'})
                    merge_format.set_text_wrap()
                    max_index = max(h_date_index, f_date_index)
                    min_index = min(h_date_index, f_date_index)
                    sheet.merge_range(first_row=product_index, first_col=0, last_row=max_index - 1,
                                      last_col=0,
                                      data=parent_key, cell_format=merge_format)
                    if max_index == h_date_index:
                        to_write_index = [3, 4]
                        for l in to_write_index:
                            for k in range(min_index, max_index):
                                sheet.write(k, l, '', merge_format)
                    elif max_index == f_date_index:
                        to_write_index = [1, 2]
                        for j in to_write_index:
                            for i in range(min_index, max_index):
                                sheet.write(i, j, '', merge_format)
                product_index = max(h_date_index, f_date_index) + 1
                h_date_index = h_value_index = f_value_index = f_date_index = product_index

    def ks_create_xlsx_report(self, response):
        ks_file_data = BytesIO()
        ks_workbook = xlsxwriter.Workbook(ks_file_data, {})
        self._ks_generate_xlsx_report(ks_workbook)
        ks_workbook.close()
        ks_file_data.seek(0)
        response.stream.write(ks_file_data.read())
        return ks_file_data.close()

    def ks_sale_forecast_xlsx_report(self):
        return {
            'type': 'ks.sales.forecast.report',
            'data': {'model': 'ks.sales.forecast',
                     'output_format': 'xlsx',
                     'options': self.id,
                     'report_name': 'Sale Forecast Report', }
        }

