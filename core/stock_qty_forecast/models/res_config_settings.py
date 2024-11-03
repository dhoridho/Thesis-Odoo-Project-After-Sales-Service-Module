# -*- coding: utf-8 -*-

from odoo import _, api, fields, models


PARAMS = [
    ("stock_qty_forecast_interval", str, "month"),
    ("stock_qty_forecast_method", str, "_ar_method"),
    ("stock_qty_predicted_periods", int, 1),
]


class res_config_settings(models.TransientModel):
    """
    Overwrite to add forecasting defaults
    """
    _inherit = "res.config.settings"

    def forecast_method_selection(self):
        """
        The method to return available interval types
        """
        return [
            ("_ar_method", "Autoregression (AR)"),
            ("_ma_method", "Moving Average (MA)"),
            ("_arima_method", "Autoregressive Integrated Moving Average (ARIMA)"),
            ("_sarima_method", "Seasonal Autoregressive Integrated Moving-Average (SARIMA)"),
            ("_hwes_method", "Holt Winter’s Exponential Smoothing (HWES)"),
            ("_ses_method", "Simple Exponential Smoothing (SES)"),
        ]

    def interval_selection(self):
        """
        The method to return available interval types
        """
        return [
            ("day", "Daily"),
            ("week", "Weekly"),
            ("month", "Monthly"),
            ("quarter", "Quarterly"),
            ("year", "Yearly"),
        ]

    stock_qty_forecast_method = fields.Selection(forecast_method_selection, string="Forecast method")
    stock_qty_forecast_interval = fields.Selection(interval_selection, string="Data Series Interval")
    stock_qty_predicted_periods = fields.Integer(string="Number of predicted periods")

    _sql_constraints = [
        (
            'stock_qty_predicted_periods_check',
            'check (stock_qty_predicted_periods>0)',
            _('Number of periods should be positive ')
        ),
    ]

    @api.model
    def get_values(self):
        """
        Overwrite to add new system params
        """
        Config = self.env['ir.config_parameter'].sudo()
        res = super(res_config_settings, self).get_values()
        values = {}
        for field_name, getter, default in PARAMS:
            values[field_name] = getter(str(Config.get_param(field_name, default)))
        res.update(**values)
        return res

    def set_values(self):
        """
        Overwrite to add new system params
        """
        Config = self.env['ir.config_parameter'].sudo()
        super(res_config_settings, self).set_values()
        for field_name, getter, default in PARAMS:
            value = getattr(self, field_name, default)
            Config.set_param(field_name, value)
