# -*- coding: utf-8 -*-

import base64
import logging
import tempfile

from calendar import monthcalendar
from calendar import monthrange
from dateutil.relativedelta import relativedelta
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import pandas as pd
except:
    raise UserError(_("The python library 'pandas' is not installed"))
try:
    import statsmodels.tsa as tsa
except:
    raise UserError(_("The python library 'statsmodels' is not installed"))
try:
    import xlsxwriter
except ImportError:
    raise UserError(_("The python library 'xlsxwriter' is not installed"))


NODATATITLE = _("Not enough stock operations in the period")
NODATAWARNING = _("No historical data is defined for the specified period")


class open_stock_series(models.TransientModel):
    """
    The model to prepare stock demand by date and forecast trend

    Used materials:
     * https://www.digitalocean.com/community/tutorials/a-guide-to-time-series-forecasting-with-arima-in-python-3
     * https://people.duke.edu/~rnau/411arim.htm
     * https://machinelearningmastery.com/time-series-forecasting-methods-in-python-cheat-sheet/
    """
    _name = 'open.stock.series'
    _description = 'Calculate trend and forecast'

    def interval_selection(self):
        """
        The method to return available interval types
        """
        return self.env['res.config.settings'].sudo().interval_selection()

    def forecast_method_selection(self):
        """
        The method to return available forecast methods
        """
        return self.env['res.config.settings'].sudo().forecast_method_selection()

    @api.model
    def default_predicted_periods(self):
        """
        Default method for predicted_periods
        """
        return int(self.env['ir.config_parameter'].sudo().get_param("stock_qty_predicted_periods", 1))

    @api.model
    def default_interval(self):
        """
        Default method for interval
        """
        return self.env['ir.config_parameter'].sudo().get_param("stock_qty_forecast_interval", "month")

    @api.model
    def default_forecast_method(self):
        """
        Default method for forecast_method
        """
        return self.env['ir.config_parameter'].sudo().get_param("stock_qty_forecast_method", "_ar_method")

    @api.onchange("interval")
    def _onchange_interval(self):
        """
        Onchange method for interval to pass the last dare of the previous period

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        today = fields.Date.from_string(fields.Date.today())
        res_date = today
        interval = self.interval
        if interval == "day":
            res_date = today - relativedelta(days=1)
            seasons = 7
        elif interval == "week":
            res_date = today - relativedelta(days=today.weekday() + 1)
            seasons = 1
        elif interval == "month":
            last_month_date = today - relativedelta(months=1)
            res_date = date(
                year=last_month_date.year,
                month=last_month_date.month,
                day=monthrange(last_month_date.year, last_month_date.month)[1],
            )
            seasons = 3
        elif interval == "quarter":
            last_quarter_date = today - relativedelta(months=3)
            last_quarter_month = int(3 * (int((last_quarter_date.month - 1)) / 3  + 1))
            res_date = date(
                year=last_quarter_date.year,
                month=last_quarter_month,
                day=monthrange(last_quarter_date.year, last_quarter_month)[1],
            )
            seasons = 2
        elif interval == "year":
            last_year_date = today - relativedelta(years=1)
            res_date = date(
                year=last_year_date.year,
                month=12,
                day=monthrange(last_year_date.year, 12)[1],
            )
            seasons = 1
        self.date_end = res_date
        self.seasons = seasons

    @api.onchange("forecast_method")
    def _onchange_forecast_method(self):
        """
        Onchange method for forecast

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        if self.forecast_method in ["_hwes_method", "_ses_method"]:
            predicted_periods = 1
        else:
            predicted_periods = int(self.env['ir.config_parameter'].sudo().get_param("stock_qty_predicted_periods", 1))
        self.predicted_periods = predicted_periods


    stats_type = fields.Selection(
        [("location", "Location demand"), ("all", "Company demand"),],
        string="Analytics by",
        default="location",
        help=""" * Location demands means that all out of that location done moves are included into data series
        * Company demand means that all out stock done moves are included into data series
          Out done moves imply all moveds made to customers, production, inventory, suppliers, etc disregarding
          to which location, warehouse or company destination location belongs to"""
    )
    stats_for = fields.Selection(
        [("product", "Product"), ("template", "Template")],
        string="Analytics for",
        default="product",
    )
    product_id = fields.Many2one("product.product", string="Product")
    template_id = fields.Many2one("product.template", string="Product Template")
    location_id = fields.Many2one("stock.location", string="Location")
    include_children = fields.Boolean(
        string="Include child locations",
        help="""If selected demand is calculated as all done moves from this location and its children out. Demand will 
        not include within-this-location moves""",
        default=True,
    )
    date_start = fields.Date(
        string="Data Series",
        help="""Using Data Series Start and End you indicate which historical data is used for prediction
        If no defined, all historical data would be used, including one from a current period""",
    )
    date_end = fields.Date(string="Data Series End")
    predicted_periods = fields.Integer(string="Number of predicted periods", default=default_predicted_periods,)
    interval = fields.Selection(interval_selection, string="Data Series Interval", default=default_interval)
    forecast_method = fields.Selection(
        forecast_method_selection,
        string="Forecast method",
        default=default_forecast_method,
    )
    seasons = fields.Integer(string="Seasons", default=1)
    p_coefficient = fields.Integer(string="P coefficient (auto regressive)", default=1)
    d_coefficient = fields.Integer(string="D coefficient (integrated)", default=1)
    q_coefficient = fields.Integer(string="Q coefficient (moving average)", default=1)
    seasonal_p_coefficient = fields.Integer(string="Seasonal P coefficient (auto regressive)", default=1)
    seasonal_d_coefficient = fields.Integer(string="Seasonal D coefficient (integrated)", default=1)
    seasonal_q_coefficient = fields.Integer(string="Seasonal Q coefficient (moving average)", default=1)

    _sql_constraints = [
        (
            'predicted_periods_check',
            'check (predicted_periods>0)',
            _('Number of periods should be positive ')
        ),
        (
            'dates_check',
            'check (date_end>date_start)',
            _('Date end should be after date start')
        ),
    ]

    def action_calculate(self):
        """
        The method to open odoo report with current and forecast time series

        Methods:
         * _calculate_data

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        moves = self._calculate_data()
        if not moves:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': NODATATITLE,
                    'message': NODATAWARNING,
                    'sticky': False,
                }
            }
        demands = self.env["report.stock.demand"].create(moves)
        action = self.env.ref("stock_qty_forecast.report_stock_demand_action").read()[0]
        action["domain"] = [('id', 'in', demands.ids)]
        interval = self.interval
        ctx = interval == 'day' and {"search_default_day" : 1} \
              or interval == 'week' and {"search_default_week" : 1} \
              or interval == 'month' and {"search_default_month" : 1} \
              or interval == 'quarter' and {"search_default_quarter" : 1} \
              or {"search_default_year" : 1}
        action["context"] = ctx
        return action

    def action_export_to_xlsx(self):
        """
        The method to prepare an xlsx table of data series

        1. Prepare workbook and styles
        2. Prepare header row
          2.1 Get column name like 'A' or 'S' (ascii char depends on counter)
        3. Make a line from each data period
        4. Create and upload an attachment

        Methods:
         * _calculate_data

        Returns:
         * action of downloading the xlsx table

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        xlsx_name = u"{}#{}.xlsx".format(self.stats_for == "product" and self.product_id.name
                                         or self.template_id.name, fields.Date.today())
        # 1
        file_path = tempfile.mktemp(suffix='.xlsx')
        workbook = xlsxwriter.Workbook(file_path)
        styles = {
            'main_header_style': workbook.add_format({
                'bold': True,
                'font_size': 11,
                'border': 1,
            }),
            'main_data_style': workbook.add_format({
                'font_size': 11,
                'border': 1,
            }),
            'red_main_data_style': workbook.add_format({
                'font_size': 11,
                'border': 1,
                'font_color': 'blue',
            }),
            'data_time_format': workbook.add_format({
                'font_size': 11,
                'border': 1,
                'num_format': 'yy/mm/dd',
            }),
            'red_data_time_format': workbook.add_format({
                'font_size': 11,
                'border': 1,
                'num_format': 'yy/mm/dd',
                'font_color': 'blue',
            }),
        }
        worksheet = workbook.add_worksheet(xlsx_name)

        # 2
        cur_column = 0
        for column in [_("Date"), _("Demand")]:
            worksheet.write(0, cur_column, column, styles.get("main_header_style"))
            # 2.1
            col_letter = chr(cur_column + 97).upper()
            column_width = 20
            worksheet.set_column('{c}:{c}'.format(c=col_letter), column_width)
            cur_column += 1
        # 3
        moves = self._calculate_data()
        if not moves:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': NODATATITLE,
                    'message': NODATAWARNING,
                    'sticky': False,
                }
            }
        moves = sorted(moves, key=lambda k: k['date_datetime'], reverse=True)
        row = 1
        for move in moves:
            red = move.get("forecast") and "red_" or ""
            instance = (
                move.get("date_datetime"),
                move.get("quantity"),
            )
            for counter, column in enumerate(instance):
                value = column
                worksheet.write(
                    row,
                    counter,
                    value,
                    counter == 0 and styles.get(red+"data_time_format") or styles.get(red+"main_data_style")
                )
            row += 1
        workbook.close()
        # 4
        with open(file_path, 'rb') as r:
            xls_file = base64.b64encode(r.read())
        att_vals = {
            'name':  xlsx_name,
            'type': 'binary',
            'datas': xls_file,
        }
        attachment_id = self.env['ir.attachment'].create(att_vals)
        self.env.cr.commit()
        action = {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment_id.id,),
            'target': 'self',
        }
        return action

    def _calculate_data(self):
        """
        The method to calculate data series + forecast

        1. Fetch all moves grouped by interval from SQL
        2. Make pandas dataframe and fill in missing values
        3. Apply related forecast method to get predicted values if possible
        4. Make single list of dicts of stock demands

        Methods:
         * _build_dynamic_clause

        Returns:
         * list of dicts:
          ** date
          ** quantity
          ** whether it is forecast

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        where_clause, with_clause  = self._build_dynamic_clause()
        interval = self.interval
        freq = interval[0]
        # 1
        query = with_clause + """
            SELECT
                DATE_TRUNC(%(interval)s, date) as date_gr,
                SUM(product_qty) as qty
            FROM stock_move
            WHERE
                state = 'done'
                AND company_id = %(company_id)s
        """ + where_clause + \
        """
            GROUP BY date_gr
            ORDER BY date_gr
        """
        options = {
            "interval": interval,
            "product_id": self.product_id.id,
            "template_id": self.template_id.id,
            "location_id": self.location_id.id,
            "date_start": self.date_start,
            "date_end": self.date_end,
            "company_id": self.env.user.company_id.id,
        }
        self._cr.execute(query, options)
        moves = self._cr.dictfetchall()
        # 2
        if not moves:
            return False
        if self.date_start and moves[0].get("date_gr") > fields.Datetime.from_string(self.date_start):
            moves.append({"date_gr": fields.Datetime.from_string(self.date_start), "qty": 0.0})
        if self.date_end and moves[-1].get("date_gr") < fields.Datetime.from_string(self.date_end):
            moves.append({"date_gr": fields.Datetime.from_string(self.date_end), "qty": 0.0})
        moves_table = pd.DataFrame(moves, columns=['date_gr', "qty"])
        moves_table.set_index(moves_table.date_gr, inplace=True)
        moves_table = moves_table.resample(freq).sum().fillna(0.0)
        # 3
        method_to_call = getattr(self, self.forecast_method)
        forecast = method_to_call(moves_table)
        # 4
        res_moves = [{"date_datetime": key.date(), "quantity": value} \
                     for key, value in moves_table.to_dict().get("qty").items()]
        if type(forecast) != bool:
            forecast_moves = [{
                                "date_datetime": key.date(),
                                "quantity": value > 0 and round(value, 2) or 0.0,
                                "forecast": True
                              } \
                              for key, value in forecast.to_dict().items()]
            res_moves += forecast_moves
        return res_moves

    def _build_dynamic_clause(self):
        """
        The method to build where for sql statement (by date, locations) and with as helpers for where
        # 1 based on location restriction
        # 2 based on variant or template
        # 3 based on used data series

        Returns:
         * str, str (both are sql query without params)

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        where_clause = ""
        with_clause = ""
        # 1
        if self.stats_type == "location":
            if self.include_children:
                with_clause += """
                    WITH RECURSIVE child_locs AS(
                    SELECT id, location_id
                    FROM stock_location
                    WHERE (location_id = %(location_id)s OR id = %(location_id)s) AND usage = 'internal'

                    UNION

                    SELECT stock_location.id, stock_location.location_id
                    FROM stock_location
                        JOIN child_locs
                            ON stock_location.location_id = child_locs.id
                )"""
                where_clause += """
                AND (
                    location_id IN (SELECT id FROM child_locs)
                    AND location_dest_id NOT IN (SELECT id FROM child_locs)
                )
                """
            else:
                where_clause += """
                AND location_id = %(location_id)s
                """
        else:
            with_clause += """
                WITH internal_locations AS (
                SELECT id
                FROM stock_location
                WHERE company_id = %(company_id)s
                      AND usage = 'internal'
            )"""
            where_clause += """
                AND (
                    location_id IN (SELECT id FROM internal_locations)
                    AND location_dest_id NOT IN (SELECT id FROM internal_locations)
                )
            """
        # 2
        if self.stats_for == "product":
            where_clause += """
            AND product_id = %(product_id)s
            """
        else:
            start_with_clause = with_clause and " , " or " WITH "
            with_clause += """
            """ + start_with_clause + \
            """ templ_products AS (
                SELECT id
                FROM product_product
                WHERE product_tmpl_id = %(template_id)s
            )
            """
            where_clause += """
                AND product_id IN (SELECT id FROM templ_products)
            """
        # 3
        if self.date_start:
            where_clause += """
                AND date::date >= %(date_start)s
            """
        if self.date_end:
            where_clause += """
                AND date::date <= %(date_end)s
            """
        return where_clause, with_clause

    def _ar_method(self, data):
        """
        The method to reveal a trend as autoregression

        Args:
         * data - pd series

        Returns:
         * predicted series or False if data is not sufficient

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        try:
            from statsmodels.tsa.ar_model import AR
            model = AR(data)
            model_fit = model.fit()
            prediction = model_fit.predict(start=len(data), end=len(data)+self.predicted_periods-1)
        except Exception as er:
            _logger.warning(u"The data is not sufficient to make prediction. Error: {}".format(er))
            prediction = False
        return prediction

    def _ma_method(self, data):
        """
        The method to reveal a trend as moving average

        Args:
         * data - pd series

        Returns:
         * predicted series or False if data is not sufficient

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        try:
            from statsmodels.tsa.arima_model import ARMA
            model = ARMA(data, order=(self.p_coefficient, self.d_coefficient))
            model_fit = model.fit(disp=False)
            prediction = model_fit.predict(start=len(data), end=len(data)+self.predicted_periods-1)
        except Exception as er:
            _logger.warning(u"The data is not sufficient to make prediction. Error: {}".format(er))
            prediction = False
        return prediction

    def _arima_method(self, data):
        """
        The method to reveal a trend as auto regressive integrated moving average

        Args:
         * data - pd series

        Returns:
         * predicted series or False if data is not sufficient

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        try:
            from statsmodels.tsa.arima_model import ARIMA
            model = ARIMA(data, order=(self.p_coefficient, self.d_coefficient, self.q_coefficient))
            model_fit = model.fit(disp=False)
            prediction = model_fit.predict(start=len(data), end=len(data)+self.predicted_periods-1, typ='levels')
        except Exception as er:
            _logger.warning(u"The data is not sufficient to make prediction. Error: {}".format(er))
            prediction = False
        return prediction

    def _sarima_method(self, data):
        """
        The method to reveal a trend as seasonal auto regressive integrated moving average

        Args:
         * data - pd series

        Returns:
         * predicted series or False if data is not sufficient

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        try:
            from statsmodels.tsa.statespace.sarimax import SARIMAX
            model = SARIMAX(
                data,
                order=(self.p_coefficient, self.d_coefficient, self.q_coefficient),
                seasonal_order=(
                    self.seasonal_p_coefficient,
                    self.seasonal_d_coefficient,
                    self.seasonal_q_coefficient, self.seasons
                )
            )
            model_fit = model.fit(disp=False)
            prediction = model_fit.predict(start=len(data), end=len(data)+self.predicted_periods-1)
        except Exception as er:
            _logger.warning(u"The data is not sufficient to make prediction. Error: {}".format(er))
            prediction = False
        return prediction

    def _hwes_method(self, data):
        """
        The method to reveal a trend as Holt Winter’s Exponential Smoothing

        Args:
         * data - pd series

        Returns:
         * predicted series or False if data is not sufficient

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        try:
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            model = ExponentialSmoothing(data)
            model_fit = model.fit()
            prediction = model_fit.predict(start=len(data), end=len(data)+self.predicted_periods-1)
        except Exception as er:
            _logger.warning(u"The data is not sufficient to make prediction. Error: {}".format(er))
            prediction = False
        return prediction

    def _ses_method(self, data):
        """
        The method to reveal a trend as Simple Exponential Smoothing (SES)

        Args:
         * data - pd series

        Returns:
         * predicted series or False if data is not sufficient

        Extra info:
         * Expected singleton
        """
        self.ensure_one()
        try:
            from statsmodels.tsa.holtwinters import SimpleExpSmoothing
            model = SimpleExpSmoothing(data)
            model_fit = model.fit()
            prediction = model_fit.predict(start=len(data), end=len(data)+self.predicted_periods-1)
        except Exception as er:
            _logger.warning(u"The data is not sufficient to make prediction. Error: {}".format(er))
            prediction = False
        return prediction
