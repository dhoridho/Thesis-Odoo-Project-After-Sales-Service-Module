import base64
import json
import os
import random
import warnings
from datetime import datetime
from math import sqrt
from random import random

import babel
import numpy as np
import pandas as pd
import pytz
from dateutil.relativedelta import relativedelta
from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import config
from pmdarima.arima import auto_arima
from sklearn.metrics import mean_squared_error
from statsmodels import api as ap
from statsmodels.tsa.ar_model import AutoReg
from statsmodels.tsa.arima_model import ARIMA
from statsmodels.tsa.arima_model import ARMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.holtwinters import SimpleExpSmoothing
from statsmodels.tsa.statespace import sarimax
from statsmodels.tsa.statespace.varmax import VARMAX
from statsmodels.tsa.vector_ar.var_model import VAR

warnings.simplefilter('ignore')


class KsSalesForecast(models.Model):
    _name = 'ks.sales.forecast'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'ks_name'
    _order = 'id desc'
    _description = 'This model is to predict sales on the bases of historical data with trending and seasonal factor'

    ks_name = fields.Char('Name', tracking=True, default=lambda self: _('New'), readonly=True, copy=False)
    ks_is_file = fields.Boolean(default=False, tracking=True, string="File")
    ks_file_type = fields.Selection([('csv', 'CSV'), ('xlx', 'Excel')], string=_('File Type'), default='csv',
                                    tracking=True)
    ks_import_file = fields.Binary(string=_('File'), tracking=True)
    ks_file_name = fields.Char(string=_('File Name'), tracking=True)
    ks_is_method_change = fields.Boolean(string="Method changed", default=False, tracking=True)
    ks_forecast_method = fields.Selection([
        ('ar', 'Autoregression (AR)'),
        ('ma', 'Moving Average (MA)'),
        ('arma', 'Autoregressive Moving Average (ARMA)'),
        ('arima', 'Autoregressive Integrated Moving Average (ARIMA)'),
        ('auto_arima', "Auto ARIMA"),
        ('sarima', 'Seasonal Autoregressive Integrated Moving Average (SARIMA)'),
        ('var', 'Vector Autoregression (VAR)'),
        ('varma', 'Vector Autoregression Moving-Average (VARMA)'),
        ('ses', 'Simple Exponential Smoothing (SES)'),
        ('hwes', 'Holt Winter’s Exponential Smoothing (HWES)')],
        tracking=True, store=True, string="Forecast Method")
    ks_default_forecast_method = fields.Selection([
        ('ar', 'Autoregression (AR)'),
        ('ma', 'Moving Average (MA)'),
        ('arma', 'Autoregressive Moving Average (ARMA)'),
        ('arima', 'Autoregressive Integrated Moving Average (ARIMA)'),
        ('auto_arima', "Auto ARIMA"),
        ('sarima', 'Seasonal Autoregressive Integrated Moving Average (SARIMA)'),
        ('var', 'Vector Autoregression (VAR)'),
        ('varma', 'Vector Autoregression Moving-Average (VARMA)'),
        ('ses', 'Simple Exponential Smoothing (SES)'),
        ('hwes', 'Holt Winter’s Exponential Smoothing (HWES)')],
        readonly=True, string="Default Forecast Method", compute="ks_default_forecast_method_value", store=True)
    ks_predicted_forecast_method = fields.Char('Predicted Method', store=True, copy=False)
    ks_model = fields.Many2one('ir.model', 'Model', default=lambda self: self.env.ref("sale.model_sale_order"),
                               readonly=True, invisible=True, tracking=True)
    ks_start_date = fields.Datetime(string=_('Start Date'), required=True, tracking=True)
    ks_end_date = fields.Datetime(string=_('End Date'), required=True, tracking=True)
    ks_forecast_base = fields.Selection([('all', 'All Products'), ('product', 'Specific Products')],
                                        string=_('Forecast Base'), default='product', tracking=True)
    ks_product_ids = fields.Many2many('product.product', string="Products", invisible=True, tracking=True)
    ks_p = fields.Integer(string=_('p Coefficient (Auto Regressive)'), copy=False)
    ks_d = fields.Integer(string=_('d Coefficient (Integrated)'), copy=False)
    ks_q = fields.Integer(string=_('q Coefficient (Moving Average)'), default=0, copy=False)
    ks_P = fields.Integer(string=_('P Coefficient (Seasonal Autoregressive order)'), copy=False)
    ks_D = fields.Integer(string=_('D Coefficient (Seasonal Difference order)'), copy=False)
    ks_Q = fields.Integer(string=_('Q Coefficient (Seasonal Moving Average order)'), copy=False)
    ks_m = fields.Integer(string=_('m Coefficient (Seasonal Time steps)'), default=12, copy=False)
    ks_trend = fields.Selection([('n', 'Normal Trend'), ('c', 'Constant trend'), ('t', 'linear trend with time'),
                                 ('ct', 'Both constant and linear trend')],
                                string='Seasonal Trend')
    ks_forecast_unit = fields.Integer(string=_('Forecast Unit'), tracking=True, required=True, default=1)
    ks_forecast_period = fields.Selection([('day', 'Day'), ('month', 'Month'), ('year', 'Year')],
                                          string=_('Forecast Period'), default='month', tracking=True, required=True)
    ks_is_predicted = fields.Boolean(string="Predicted", copy=False)
    ks_is_predicted_method = fields.Boolean(string="Predicted Method", compute='ks_compute_predicted_method')
    ks_chart_data = fields.Text(string=_("Chart Data"), default=0)
    ks_report_data = fields.Text(string="Report data", default=0)
    ks_graph_view = fields.Integer(string="Graph view", default=1)
    ks_outcome = fields.Boolean(string="Outcome", default=False, copy=False)
    ks_danger_outcome = fields.Boolean(string="Outcome", default=False, copy=False)
    ks_resp = fields.Integer(string="p Coefficient(Auto Regressive)", readonly=True, copy=False)
    ks_resd = fields.Integer(string="d Coefficient(Integrated)", readonly=True, copy=False)
    ks_resq = fields.Integer(string="q Coefficient(Moving Average)", readonly=True, copy=False)
    ks_sp = fields.Integer(string="P Coefficient (Seasonal Auto Regressive)", readonly=True, copy=False)
    ks_sd = fields.Integer(string="D Coefficient (Seasonal Difference)", readonly=True, copy=False)
    ks_sq = fields.Integer(string="Q Coefficient (Seasonal Moving Average)", readonly=True, copy=False)

    @api.onchange('ks_forecast_method')
    def ks_check_coefficient_value(self):
        for rec in self:
            if rec.ks_p > 0: rec.ks_p = 0
            if rec.ks_d > 0: rec.ks_d = 0
            if rec.ks_q > 0: rec.ks_q = 0
            if rec.ks_P > 0: rec.ks_P = 0
            if rec.ks_D > 0: rec.ks_D = 0
            if rec.ks_Q > 0: rec.ks_Q = 0

    @api.onchange('ks_forecast_method', 'ks_default_forecast_method', 'ks_predicted_forecast_method',
                  'ks_is_method_change')
    def ks_compute_predicted_method(self):
        for rec in self:
            if rec.ks_default_forecast_method == rec.ks_predicted_forecast_method and rec.ks_is_predicted:
                rec.ks_is_predicted_method = True
            else:
                rec.ks_is_predicted_method = False

    def ks_open_tuner(self):
        view = self.env.ref('ks_sales_forecast.ks_tuning_wizard_form_view')
        return {
            'type': 'ir.actions.act_window',
            'name': 'Hyper Parameter Tuner',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_model': 'ks.parameter.tuning.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ks_forecast_method': self.ks_default_forecast_method if not self.ks_is_method_change else self.ks_forecast_method,
                'default_ks_forecast': self.id}
        }

    @api.onchange('ks_forecast_method', 'ks_is_method_change')
    def ks_extend_dataset_map(self):
        for rec in self:
            rec.ks_outcome = False
            rec.ks_danger_outcome = False

    @api.depends('ks_forecast_unit')
    @api.onchange('ks_forecast_unit')
    def ks_forecast_unit_method(self):
        if self.ks_forecast_unit < 1:
            raise ValidationError(_('Please Enter a positive non-zero number.'))

    @api.model
    def create(self, values):
        if 'ks_name' not in values or values['ks_name'] == _('New'):
            values['ks_name'] = self.env['ir.sequence'].next_by_code('ks.sales.forecast') or _('New')

        if not values.get('ks_is_method_change'):
            values.update(
                {'ks_default_forecast_method': self.env['ir.config_parameter'].sudo().get_param('ks_forecast_method')})
        elif values.get('ks_forecast_method'):
            values.update({'ks_default_forecast_method': values.get('ks_forecast_method')})
        return super(KsSalesForecast, self).create(values)

    def write(self, values):
        if values.get('ks_forecast_method'):
            values.update({'ks_default_forecast_method': values.get('ks_forecast_method')})
        elif values.get('ks_is_method_change') == True:
            values.update({'ks_default_forecast_method': self.ks_forecast_method})
        elif values.get('ks_is_method_change') == False:
            values.update(
                {'ks_default_forecast_method': self.env['ir.config_parameter'].sudo().get_param('ks_forecast_method')})
        return super(KsSalesForecast, self).write(values)

    @api.onchange('ks_start_date', 'ks_end_date')
    def ks_onchange_dates(self):
        if self.ks_start_date and self.ks_end_date:
            if not self.ks_start_date < self.ks_end_date:
                self.ks_end_date = False
                raise ValidationError('Start Date should be less then End Date')

    @api.onchange('ks_forecast_method', 'ks_is_method_change')
    def ks_default_forecast_method_value(self):
        for rec in self:
            if not rec.ks_is_method_change:
                rec.ks_default_forecast_method = self.env['ir.config_parameter'].sudo().get_param('ks_forecast_method')
            elif rec.ks_forecast_method:
                rec.ks_default_forecast_method = rec.ks_forecast_method

    def ks_forecast_from_file(self, vals):
        temp_path = os.path.join(config.get('data_dir'), "temp")
        if not os.path.exists(temp_path):
            os.makedirs(temp_path)

        file_name = self.ks_file_name
        file_path = temp_path + '/' + file_name
        temp_file = open(file_path, 'wb')
        temp_file.write(base64.b64decode(self.ks_import_file))
        temp_file.close()

        previous_data = pd.read_csv(temp_file.name, index_col=['Date', 'Sales'])
        product_groups = previous_data.groupby(previous_data.Product).groups
        products = product_groups.keys()
        for product in products:
            sales_list = []
            product_id = self.env['product.product'].search([('name', '=', product)], limit=1)
            file_datas = product_groups[product].values
            for file_data in file_datas:
                sales_list.append(float(file_data[1]))
                sale_data = {
                    'ks_forecast_id': self.id,
                    'ks_date': datetime.strptime(file_data[0], tools.DEFAULT_SERVER_DATE_FORMAT),
                    'ks_value': float(file_data[1]),
                    'ks_product_id': product_id.id
                }
                vals.append(sale_data)
            sales_data = pd.read_csv(temp_file.name, index_col='Date', usecols=['Sales', 'Date'])
            forecast_method = self.env['ir.config_parameter'].sudo().get_param('ks_forecast_method')
            if self.ks_is_method_change:
                forecast_method = self.ks_forecast_method
            data_frame = pd.DataFrame(sales_list)
            if forecast_method:
                forecast_method_name = 'ks_%s_method' % forecast_method
                if hasattr(self, forecast_method_name):
                    method = getattr(self, forecast_method_name)
                    results = method(product_groups[product])
                for value, month in zip(results, results.index):
                    ks_date = datetime.strftime(month, tools.DEFAULT_SERVER_DATE_FORMAT)
                    forecast_data = {
                        'ks_forecast_id': self.id,
                        'ks_date': datetime.strptime(ks_date, tools.DEFAULT_SERVER_DATE_FORMAT),
                        'ks_value': value,
                        'ks_product_id': product_id.id
                    }
                    vals.append(forecast_data)
        self.env['ks.sales.forecast.result'].create(vals)
        return vals

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
            'end_date': end_date
        })
        self.env.cr.execute(query, query_data)
        result = self.env.cr.fetchall()  # now also contains unit price, handle it for [VAR]
        self.ks_check_sufficient_data(result)
        return result

    def ks_get_sum_of_same_date_sale_order(self, result):
        ks_result = {}

        for rec in result:
            if rec[2] not in ks_result:
                ks_result[rec[2]] = [[rec[0], rec[1]]]
            elif not [i for i in ks_result[rec[2]] if rec[0] in i]:
                ks_result[rec[2]].append([rec[0], rec[1]])
            elif [i for i in ks_result[rec[2]] if rec[0] in i]:
                [i for i in ks_result[rec[2]] if rec[0] in i][0][1] += rec[1]
        return ks_result

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

        for key in ks_result:
            if len(ks_result[key]) < 9:
                product_id = self.env['product.product'].browse(key)
                ks_product.append(product_id.display_name)
        if ks_product:
            raise UserError(
                _('You do not have sufficient data for "%s" products. We need minimum 9 "%ss" data.') % (
                    ks_product, self.ks_forecast_period))
        ks_product_not_in_ks_result = [i.display_name for i in self.ks_product_ids if i.id not in ks_result.keys()]
        if ks_product_not_in_ks_result:
            raise UserError(_("Sales data is not available for '%s' products.") % ks_product_not_in_ks_result)

    def ks_create_data_dict(self, vals, result):
        data_dict = {}
        for data in result:
            keys = data_dict.keys()
            sale_data = {
                'ks_forecast_id': self.id,
                'ks_date': data[0],
                'ks_value': float(data[1]),
                'ks_product_id': data[2],
                'ks_partner_id': data[4]
            }
            vals.append(sale_data)
            if data[2] in keys:
                data_dict[data[2]]['date'].append(data[0])
                data_dict[data[2]]['sales'].append(data[1])
                data_dict[data[2]]['cost'].append(data[3])
                data_dict[data[2]]['forecast_sales'].append(0.0)
            else:
                data_dict[data[2]] = {'date': [], 'sales': [], 'cost': [], 'forecast_sales': []}
                data_dict[data[2]]['date'].append(data[0])
                data_dict[data[2]]['sales'].append(data[1])
                data_dict[data[2]]['cost'].append(data[3])
                data_dict[data[2]]['forecast_sales'].append(0.0)
        return data_dict

    def ks_predict_sales(self):
        vals = []
        end_date = self.ks_end_date
        if self.ks_is_file:
            self.ks_forecast_from_file(vals)
        else:
            result = self.ks_get_data_from_database()
            data_dict = self.ks_create_data_dict(vals, result)
            product_keys = data_dict.keys()
            for product in product_keys:
                product_id = self.env['product.product'].browse(product)
                product_sales_data = data_dict[product]
                sales_list = product_sales_data.get('sales')
                cost_list = product_sales_data.get('cost')
                forecast_method = self.env['ir.config_parameter'].sudo().get_param('ks_forecast_method')
                if self.ks_is_method_change:
                    forecast_method = self.ks_forecast_method
                data_frame = np.array(sales_list)
                cost_factor = np.array([x + random() for x in cost_list])
                if forecast_method and len(data_frame) >= 9:
                    results = 0
                    try:
                        forecast_method_name = 'ks_%s_method' % forecast_method
                        if hasattr(self, forecast_method_name):
                            p = self.ks_p
                            q = self.ks_q
                            d = self.ks_d
                            sp = self.ks_P
                            sq = self.ks_Q
                            sd = self.ks_D
                            m = self.ks_m
                            trend = self.ks_trend
                            method = getattr(self, forecast_method_name)
                            results = method(data_frame, cost_factor, p, q, d, trend, sp, sq, sd, m)
                    except Exception as e:
                        return self.env['ks.message.wizard'].ks_pop_up_message(names='Error', message=e)
                    for (i, value) in zip(range(0, len(results)), results):
                        i = i + 1
                        if self.ks_forecast_period == 'day':
                            ks_date = end_date + relativedelta(days=i)
                        elif self.ks_forecast_period == 'month':
                            ks_date = end_date + relativedelta(months=i)
                        else:
                            ks_date = end_date + relativedelta(years=i)
                        forecast_data = {
                            'ks_forecast_id': self.id,
                            'ks_date': ks_date,
                            'ks_value': round(value, 3),
                            'ks_product_id': product_id.id,
                        }
                        data_dict[product_id.id]['date'].append(ks_date)
                        data_dict[product_id.id]['sales'].append(0.0)
                        data_dict[product_id.id]['forecast_sales'].append(value)
                        vals.append(forecast_data)
                elif not forecast_method:
                    raise UserError(_('Please select a forecast method.'))
            ks_sale_order_sum = self.ks_get_sum_of_same_date_sale_order(result)
            keys = data_dict.keys()
            final_dict = {}
            dict_data = {}
            if keys:
                dates = []
                for product in keys:
                    dates.extend(data_dict[product]['date'])
                dates = list(set(dates))
                dates.sort()
                labels = [self.format_label(values) for values in dates]
                final_dict.update({
                    'labels': labels,
                    'datasets': []
                })
                product_keys = data_dict.keys()
                for product in product_keys:
                    dict_data[product] = {
                        'sales': {},
                        'forecast_sales': {},
                    }
                    for final_date in dates:
                        if final_date in data_dict[product]['date']:
                            data_index = data_dict[product]['date'].index(final_date)
                            sales_value = [i for i in ks_sale_order_sum[product] if
                                           final_date in i] if ks_sale_order_sum else False
                            sales = sales_value[0][1] if sales_value else data_dict[product]['sales'][data_index]
                            dict_data[product]['sales'][final_date] = sales
                            dict_data[product]['forecast_sales'][final_date] = data_dict[product]['forecast_sales'][
                                data_index]
                        else:
                            dict_data[product]['sales'][final_date] = 0.0
                            dict_data[product]['forecast_sales'][final_date] = 0.0
            if dict_data:
                product_keys = data_dict.keys()
                for product in product_keys:
                    product_id = self.env['product.product'].browse(product)
                    # product_name = product_id.code + ' ' + product_id.name if product_id.code else product_id.name
                    product_name = product_id.display_name
                    final_dict['datasets'] = final_dict['datasets'] + [{
                        'data': list(dict_data[product]['sales'].values()),
                        'label': product_name + '/Previous',
                    }, {
                        'data': [round(x, 3) for x in dict_data[product]['forecast_sales'].values()],
                        'label': product_name + '/Forecast'
                    }]
                self.ks_chart_data = json.dumps(final_dict)
            forecast_result = self.env['ks.sales.forecast.result']
            forecast_records = forecast_result.search([('ks_forecast_id', '=', self.id)])
            if forecast_records.ids:
                for forecast_record in forecast_records:
                    forecast_record.unlink()
                forecast_result.create(vals)
            else:
                forecast_result.create(vals)
            self.ks_is_predicted = True
            self.ks_predicted_forecast_method = self.ks_default_forecast_method

    @api.model
    def format_label(self, value, ftype='datetime', display_format='MMMM yyyy'):
        if self.ks_forecast_period == 'day':
            display_format = 'dd MMMM yyyy'
        elif self.ks_forecast_period == 'year':
            display_format = 'yyyy'
        tz_convert = self._context.get('tz')
        locale = self._context.get('lang') or 'en_US'
        tzinfo = None
        if ftype == 'datetime':
            if tz_convert:
                value = pytz.timezone(self._context['tz']).localize(value)
                tzinfo = value.tzinfo
            return babel.dates.format_datetime(value, format=display_format, tzinfo=tzinfo, locale=locale)
        else:
            if tz_convert:
                value = pytz.timezone(self._context['tz']).localize(value)
                tzinfo = value.tzinfo
            return babel.dates.format_date(value, format=display_format, locale=locale)

    def ks_ar_method(self, data_frame, cost_factor=False, p=False, d=False, q=False, trend=False, sp=False, sq=False,
                     sd=False,
                     m=False):
        ks_ar_model = AutoReg(data_frame, lags=1)
        ks_fit_model = ks_ar_model.fit()
        forecast_period = self.ks_forecast_unit - 1
        forecast_value = ks_fit_model.predict(len(data_frame), len(data_frame) + forecast_period)
        return forecast_value

    def ks_ma_method(self, data_frame, cost_factor=False, p=False, d=False, q=False, trend=False, sp=False, sq=False,
                     sd=False,
                     m=False):
        ks_ma_model = ARMA(data_frame, order=(0, q))
        ks_fit_model = ks_ma_model.fit(disp=False)
        forecast_period = self.ks_forecast_unit - 1
        forecast_value = ks_fit_model.predict(len(data_frame), len(data_frame) + forecast_period)
        return forecast_value

    def ks_arma_method(self, data_frame, cost_factor=False, p=False, d=False, q=False, trend=False, sp=False, sq=False,
                       sd=False,
                       m=False):
        ks_arma_model = ARMA(data_frame, order=(p, q))
        ks_fit_model = ks_arma_model.fit(disp=False)
        forecast_period = self.ks_forecast_unit - 1
        forecast_value = ks_fit_model.predict(len(data_frame), len(data_frame) + forecast_period)
        return forecast_value

    def ks_arima_method(self, data_frame, cost_factor=False, p=False, d=False, q=False, trend=False, sp=False, sq=False,
                        sd=False,
                        m=False):
        ks_arima_model = ARIMA(data_frame, order=(p, d, q))
        ks_fit_model = ks_arima_model.fit(disp=False)
        forecast_period = self.ks_forecast_unit - 1
        forecast_value = ks_fit_model.predict(len(data_frame), len(data_frame) + forecast_period)
        return forecast_value

    def ks_auto_arima_method(self, data_frame, cost_factor=False, p=False, d=False, q=False, trend=False, sp=False,
                             sq=False, sd=False,
                             m=False):
        ks_auto_arima_model = auto_arima(data_frame, start_p=0, d=0, start_q=0,
                                         max_p=9, max_d=9, max_q=9,
                                         start_P=0, D=0, start_Q=0,
                                         max_P=9, max_D=9, max_Q=9, m=15,
                                         random_state=0, n_fits=15, n_jobs=-1)
        forecast_period = self.ks_forecast_unit
        forecasted_value = ks_auto_arima_model.predict(forecast_period)
        return forecasted_value

    def ks_sarima_method(self, data_frame, cost_factor=False, p=False, d=False, q=False, trend=False, sp=False,
                         sq=False, sd=False,
                         m=False):
        if trend == False:
            trend = None
        ks_sarima_model = sarimax.SARIMAX(data_frame, order=(p, d, q), seasonal_order=(sp, sd, sq, m), trend=trend,
                                          maxiter=60)
        ks_sarima_trained = ks_sarima_model.fit(disp=False)
        forecast_period = self.ks_forecast_unit - 1
        forecasted_value = ks_sarima_trained.predict(len(data_frame), len(data_frame) + forecast_period)
        return forecasted_value

    def ks_ses_method(self, data_frame, cost_factor=False, p=False, d=False, q=False, trend=False, sp=False, sq=False,
                      sd=False,
                      m=False):
        ks_ses_model = SimpleExpSmoothing(data_frame)
        ks_fit_model = ks_ses_model.fit()
        forecast_period = self.ks_forecast_unit - 1
        forecasted_value = ks_fit_model.predict(len(data_frame), len(data_frame) + forecast_period)
        return forecasted_value

    def ks_hwes_method(self, data_frame, cost_factor=False, p=False, d=False, q=False, trend=False, sp=False, sq=False,
                       sd=False,
                       m=False):
        ks_hwes_model = ExponentialSmoothing(data_frame)
        ks_fit_model = ks_hwes_model.fit()
        forecast_period = self.ks_forecast_unit - 1
        forecasted_value = ks_fit_model.predict(len(data_frame), len(data_frame) + forecast_period)
        return forecasted_value

    def ks_var_method(self, data_frame, cost_factor=False, p=False, d=False, q=False, trend=False, sp=False, sq=False,
                      sd=False,
                      m=False):
        train_data = list()
        for factor, data in zip(cost_factor, data_frame):
            train_data.append([factor, data])
        train_data = np.array(train_data)
        ks_var_model = VAR(endog=train_data)
        ks_trained_model = ks_var_model.fit()
        forecast_period = self.ks_forecast_unit
        ks_prediction = ks_trained_model.forecast(ks_trained_model.y, steps=(forecast_period))[:, 1]
        return ks_prediction

    def ks_varma_method(self, data_frame, cost_factor=False, p=False, d=False, q=False, trend=False, sp=False, sq=False,
                        sd=False,
                        m=False):
        train_data = list()
        for factor, data in zip(cost_factor, data_frame):
            train_data.append([factor, data])
        train_data = np.array(train_data)
        ks_varma_model = VARMAX(endog=train_data, order=(p, q),
                                enforce_stationarity=True, enforce_invertibility=True)
        ks_trained_model = ks_varma_model.fit(disp=False)
        forecast_period = self.ks_forecast_unit
        ks_prediction = ks_trained_model.forecast(steps=(forecast_period))[:, 1]
        return ks_prediction

    # Hyper Parameter Tunings
    def ks_train_test_split_data(self, dataframe):
        train_size = int(0.8 * len(dataframe))
        x_train = dataframe[:train_size]
        x_test = dataframe[train_size:]
        return x_train, x_test

    def ks_sarima_tune_forecast(self, train_data, configs):
        order, s_order = configs
        ks_sarima_model = sarimax.SARIMAX(train_data, order=order, seasonal_order=s_order,
                                          enforce_invertibility=False, enforce_stationarity=False)
        ks_trained_model = ks_sarima_model.fit(disp=False)
        ks_predictions = ks_trained_model.predict(len(train_data), len(train_data))
        return ks_predictions[0]

    def ks_evaluate_model(self, true, predicted):
        return sqrt(mean_squared_error(true, predicted))

    def ks_record_validations(self, dataframe, cfg):
        ks_predictions = list()
        train, test = self.ks_train_test_split_data(dataframe)

        ks_train = [x for x in train]
        for i in range(len(test)):
            yhat = self.ks_sarima_tune_forecast(ks_train, cfg)
            ks_predictions.append(yhat)
            ks_train.append(test[i])

        error = self.ks_evaluate_model(test, ks_predictions)
        return error

    def ks_score_sarima_model(self, data, cfg, debug=False):
        result = None
        key = str(cfg)
        if debug:
            result = self.ks_record_validations(data, cfg)
        else:
            try:
                result = self.ks_record_validations(data, cfg)
            except:
                error = None
        return (key, result)

    def ks_grid_search_sarima(self, data, cfg_list, parallel=True):
        scores = []
        if parallel:
            for cfg in cfg_list:
                scores.append(self.ks_score_sarima_model(data, cfg))
        scores = [r for r in scores if r[1] != None]
        scores.sort(key=lambda value: value[1])
        return scores

    def ks_tune_hyperparams(self, **kwargs):
        try:
            forecast = kwargs.get("forecast")
            raw_data = forecast.ks_get_data_from_database()
            vals = []
            data_frame = None
            cfg = {"p": None, "d": None, "q": None, 't': None, "P": None, "D": None, "Q": None}
            min_order = None
            min_seasonal_order = None
            data_dict = self.ks_create_data_dict(vals, raw_data)
            product_keys = data_dict.keys()
            for product in product_keys:
                product_id = self.env['product.product'].browse(product)
                product_sales_data = data_dict[product]
                sales_list = product_sales_data.get('sales')
                cost_list = product_sales_data.get('cost')
                data_frame = np.array(sales_list)
            forecast_method = forecast.ks_forecast_method if forecast.ks_is_method_change else forecast.ks_default_forecast_method
            if forecast_method == 'arma':
                resDif = ap.tsa.arma_order_select_ic(data_frame, max_ar=kwargs.get("max_p"), max_ma=kwargs.get("max_q"),
                                                     ic='aic',
                                                     trend='c')
                min_order = resDif['aic_min_order']
                cfg['p'] = min_order[0]
                cfg['q'] = min_order[1]

            elif forecast_method == 'sarima':
                models = list()
                ar_range = range(kwargs.get("min_p"), kwargs.get("max_p") + 1)
                dif_range = range(kwargs.get("min_d"), kwargs.get("max_d") + 1)
                ma_range = range(kwargs.get("min_q"), kwargs.get("max_q") + 1)
                sar_range = range(kwargs.get("min_sp"), kwargs.get("max_sp") + 1)
                sma_range = range(kwargs.get("min_sq"), kwargs.get("max_sq") + 1)
                sd_range = range(kwargs.get("min_sd"), kwargs.get("max_sd") + 1)
                for p in ar_range:
                    for d in dif_range:
                        for q in ma_range:
                            for sp in sar_range:
                                for sd in sd_range:
                                    for sq in sma_range:
                                        confg = [(p, d, q), (sp, sd, sq, 12)]
                                        models.append(confg)
                scores = self.ks_grid_search_sarima(data_frame, models, parallel=True)
                coeffs = eval(scores[0][0])
                order = coeffs[0]
                seasonal_orders = coeffs[1]
                cfg['p'] = order[0]
                cfg['d'] = order[1]
                cfg['q'] = order[2]
                cfg['P'] = seasonal_orders[0]
                cfg['D'] = seasonal_orders[1]
                cfg['Q'] = seasonal_orders[2]

            elif forecast_method in ['varma']:
                ks_auto_arima_model = auto_arima(data_frame, start_p=kwargs.get('min_p'), d=kwargs.get('min_d'),
                                                 start_q=kwargs.get('min_q'),
                                                 max_p=kwargs.get("max_p"), max_d=kwargs.get("max_d"),
                                                 max_q=kwargs.get("max_q"),
                                                 start_P=kwargs.get("min_sp"), D=kwargs.get("min_sd"),
                                                 start_Q=kwargs.get("min_sq"),
                                                 max_P=kwargs.get("max_sp"), max_D=kwargs.get("max_sd"),
                                                 max_Q=kwargs.get("max_sq"), m=15,
                                                 random_state=0, n_fits=15, n_jobs=-1,
                                                 ic="aic",
                                                 test=("kpss", "adf", "pp"),
                                                 seasonal_test="ocsb")
                order = ks_auto_arima_model.order
                seasonal_order = ks_auto_arima_model.seasonal_order
                cfg['p'] = order[0]
                cfg['q'] = order[2]

            elif forecast_method == 'ma':
                x_train, x_test = self.ks_train_test_split_data(data_frame)
                min_error = float('inf')
                ma_range = range(kwargs.get("min_q"), kwargs.get("max_q") + 1)
                for ma in ma_range:
                    try:
                        ks_ma_model = ARMA(x_train, order=(0, ma))
                        fit_model = ks_ma_model.fit()
                        predictions = fit_model.predict(len(x_train), len(x_train) + len(x_test) - 1)
                        error = mean_squared_error(x_test, predictions)
                        if error < min_error:
                            min_error = error
                            cfg['q'] = ma
                    except:
                        continue

            elif forecast_method == 'arima':
                x_train, x_test = self.ks_train_test_split_data(data_frame)
                min_error = float('inf')
                ar_range = range(kwargs.get("min_p"), kwargs.get("max_p") + 1)
                dif_range = range(kwargs.get("min_d"), kwargs.get("max_d") + 1)
                ma_range = range(kwargs.get("min_q"), kwargs.get("max_q") + 1)

                for i in ar_range:
                    for j in dif_range:
                        for k in ma_range:
                            try:
                                ks_arima_model = ARIMA(x_train, order=(i, j, k))
                                ks_fit_model = ks_arima_model.fit(disp=False)
                                predictions = ks_fit_model.predict(len(x_train), len(x_train) + len(x_test) - 1)
                                error = mean_squared_error(x_test, predictions)
                                if error < min_error:
                                    min_error = error
                                    cfg['p'] = i
                                    cfg['d'] = j
                                    cfg['q'] = k
                            except:
                                continue

            vals = {
                'ks_outcome': True,
                'ks_danger_outcome': False,
                'ks_resp': cfg.get('p') if cfg.get('p') != None else -1,
                'ks_resd': cfg.get('d') if cfg.get('d') != None else -1,
                'ks_resq': cfg.get('q') if cfg.get('q') != None else -1,
                'ks_sp': cfg.get('P') if cfg.get('P') != None else -1,
                'ks_sd': cfg.get('D') if cfg.get('D') != None else -1,
                'ks_sq': cfg.get('Q') if cfg.get('Q') != None else -1
            }
            if vals.get('ks_resp') < 0 and vals.get('ks_resd') < 0 and vals.get('ks_resq') < 0 and vals.get(
                    'ks_sp') < 0 and vals.get('ks_sd') < 0 and vals.get('ks_sq') < 0:
                vals['ks_danger_outcome'] = True
            forecast.write(vals)

        except Exception as e:
            raise UserError(_(e))
