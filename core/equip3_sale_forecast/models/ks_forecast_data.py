import pytz
from dateutil.relativedelta import relativedelta
from odoo import models, _
from odoo.exceptions import UserError


class KsSalesForecast(models.Model):
    _inherit = 'ks.sales.forecast'

    def ks_get_data_from_database(self):
        user_tz = pytz.timezone(self.env.user.tz)
        start_date = pytz.utc.localize(self.ks_start_date).astimezone(user_tz)
        end_date = pytz.utc.localize(self.ks_end_date).astimezone(user_tz)
        query_data = {}

        if self.ks_forecast_base == 'product':
            query_data['product_condition'] = tuple(self.ks_product_ids.ids)
        else:
            query_data['product_condition'] = tuple(self.env['product.product'].search([]).ids)

        query = """
                    select
                        date_trunc(%(unit)s, so.date_order) as date,
                        sum(sol.price_subtotal),
                        sol.product_id,sol.price_unit,so.partner_id
                    from sale_order_line as sol
                        inner join sale_order as so
                            on sol.order_id = so.id
                    where
                        date_order >= %(start_date)s and date_order <= %(end_date)s  and sol.product_id in %(product_condition)s
                        and sol.company_id = %(company_id)s     
                        group by date, sol.product_id, sol.price_unit, so.partner_id
                        order by date
                """
        if self.ks_forecast_period == 'month':
            if end_date.day > 15:
                end_date = end_date + relativedelta(day=31)
            else:
                end_date = end_date + relativedelta(day=1)

        query_data.update({
            'unit': self.ks_forecast_period,
            'start_date': start_date,
            'end_date': end_date,
            'company_id': self.env.company.id
        })
        self.env.cr.execute(query, query_data)
        result = self.env.cr.fetchall()  # now also contains unit price, handle it for [VAR]
        self.ks_check_sufficient_data(result)
        return result

    def ks_check_sufficient_data(self, result):

        ks_result = {}
        ks_product = []
        if len(result) == 0:
            raise UserError(_("Sales data is not available for these products."))

        for rec in result:
            if self.ks_forecast_period == 'day':
                if rec[2] not in ks_result:
                    ks_result[rec[2]] = [rec[0]]
                elif rec[0] not in ks_result[rec[2]]:
                    ks_result[rec[2]].append(rec[0])
            elif self.ks_forecast_period == 'month':
                if rec[2] not in ks_result:
                    ks_result[rec[2]] = [rec[0]]
                elif rec[0] not in ks_result[rec[2]]:
                    ks_result[rec[2]].append(rec[0])
            elif self.ks_forecast_period == 'year':
                if rec[2] not in ks_result:
                    ks_result[rec[2]] = [rec[0].year]
                elif rec[0].year not in ks_result[rec[2]]:
                    ks_result[rec[2]].append(rec[0].year)

        # for key in ks_result:
        #     if len(ks_result[key]) < 9:
        #         product_id = self.env['product.product'].browse(key)
        #         ks_product.append(product_id.display_name)
        # if ks_product:
        #     raise UserError(
        #         _('You do not have sufficient data for "%s" products. We need minimum 9 "%ss" data.') % (
        #             ks_product, self.ks_forecast_period))
        ks_product_not_in_ks_result = [i.display_name for i in self.ks_product_ids if i.id not in ks_result.keys()]
        # if ks_product_not_in_ks_result:
        #     raise UserError(_("Sales data is not available for '%s' products.") % ks_product_not_in_ks_result)
