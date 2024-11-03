from odoo import models, fields, _
from odoo.exceptions import ValidationError


class KsHyperparamtertuningWizard(models.TransientModel):
    _name = "ks.parameter.tuning.wizard"
    _description = "Parameter Tuner"
    ks_forecast = fields.Many2one("ks.sales.forecast", readonly=True)
    ks_forecast_method = fields.Selection([
        ('ma', 'Moving Average (MA)'),
        ('arma', 'Autoregressive Moving Average (ARMA)'),
        ('arima', 'Autoregressive Integrated Moving Average (ARIMA)'),
        ('sarima', 'Seasonal Autoregressive Integrated Moving Average (SARIMA)'),
        ('varma', 'Vector Autoregression Moving-Average (VARMA)')], string="Forecast Method",
        readonly=True)

    min_p = fields.Integer(string="Min. Value of p Coefficient (Auto Regressive)")
    max_p = fields.Integer(string="Max. Value of p Coefficient (Auto Regressive)")
    min_d = fields.Integer(string="Min. Value of d Coefficient (Integrated)")
    max_d = fields.Integer(string="Max. Value of d Coefficient (Integrated)")
    min_q = fields.Integer(string="Min. Value of q Coefficient (Moving Average)")
    max_q = fields.Integer(string="Max. Value of q Coefficient (Moving Average)")
    min_sp = fields.Integer(string="Min. Value of P Coefficient (Seasonal Auto Regressive)")
    max_sp = fields.Integer(string="Max. Value of P Coefficient (Seasonal Auto Regressive)")
    min_sd = fields.Integer(string="Min. Value of D Coefficient (Seasonal Difference)")
    max_sd = fields.Integer(string="Max. Value of D Coefficient (Seasonal Difference)")
    min_sq = fields.Integer(string="Min. Value of Q Coefficient (Seasonal Moving Average)")
    max_sq = fields.Integer(string="Max. Value of Q Coefficient (Seasonal Moving Average)")

    def ks_initiate_tuning(self):
        if self.min_p < 0 or self.max_p < 0 or self.min_q < 0 or self.max_q < 0 or self.min_d < 0 or self.max_d < 0 or self.min_sp < 0 or self.max_sp < 0 or self.min_sq < 0 or self.max_sq < 0 or self.min_sd < 0 or self.max_sd < 0:
            raise ValidationError(_("Input value can not be negative."))
        if self.min_p > self.max_p or self.min_sp > self.max_sp:
            raise ValidationError(_("Min. value of p coefficient can not be greater than Max. value of p coefficient."))
        elif self.min_q > self.max_q or self.min_sq > self.max_sq:
            raise ValidationError(_("Min. value of q coefficient can not be greater than Max. value of q coefficient."))
        elif self.min_d > self.max_d or self.min_sd > self.max_sd:
            raise ValidationError(_("Min. value of d coefficient can not be greater than Max. value of d coefficient."))

        self.env['ks.sales.forecast'].ks_tune_hyperparams(forecast=self.ks_forecast, min_p=self.min_p, max_p=self.max_p,
                                                          min_d=self.min_d, max_d=self.max_d,
                                                          min_q=self.min_q, max_q=self.max_q,
                                                          min_sp=self.min_sp, max_sp=self.max_sp,
                                                          min_sd=self.min_sd, max_sd=self.max_sd,
                                                          min_sq=self.min_sq, max_sq=self.max_sq)
