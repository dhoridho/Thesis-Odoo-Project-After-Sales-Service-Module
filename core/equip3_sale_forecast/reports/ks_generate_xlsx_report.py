from odoo import models
from dateutil.relativedelta import relativedelta


class KsSalesForecast(models.Model):
    _inherit = 'ks.sales.forecast'

    def _ks_get_historic_data_from_database(self, unit, forecast_id, product_id, start_date, end_date):
        query = """
                select date_trunc(%(unit)s, res.ks_date) as date,
                sum(res.ks_value) from ks_sales_forecast_result as res 
                where res.ks_forecast_id = %(forecast_uid)s and res.ks_product_id = %(product_uid)s
                and res.ks_date >= %(start_date)s and res.ks_date <= %(end_date)s and res.company_id = %(company_id)s
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
            'end_date': end_date,
            'company_id': self.env.company.id
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
                and res.ks_date > %(start_date)s and res.company_id = %(company_id)s group by date, res.ks_value order by date
        """

        self.env.cr.execute(query, {
            'unit': unit,
            'forecast_uid': forecast_id,
            'product_uid': product_id,
            'start_date': start_date,
            'company_id': self.env.company.id
        })
        result = self.env.cr.fetchall()
        return result
