from odoo import fields, models, api, tools, _
from datetime import date


class SetuCashForecastReport(models.Model):
    _name = 'setu.cash.forecast.report'
    _description = "Setu Cash Forecast Report"
    _auto = False
    _order = 'forecast_period_id.start_date'

    name = fields.Char(string="Name")
    acc_forecast_period_id = fields.Many2one('sh.account.period', string="Forecast Period")
    acc_fiscal_year_id = fields.Many2one("sh.fiscal.year", string="Fiscal Year")
    forecast_type_id = fields.Many2one('setu.cash.forecast.type', string="Forecast Type")
    cash_forecast_category_id = fields.Many2one('setu.cash.forecast.categories', string="Categories Name")
    forecast_value = fields.Float(string="Forecast Value")
    real_value = fields.Float(string="Real Value")
    difference_value = fields.Float(string="Difference Value")
    percentage_by_type = fields.Float(string="Forecast (%)")
    forecast_type = fields.Selection([('income', 'Cash In'), ('expense', 'Cash Out'),
                                      ('opening', 'Opening Forecast'), ('closing', 'Closing Forecast')],
                                     string="Group")
    company_id = fields.Many2one("res.company", string='Company')
    #unused
    forecast_period_id = fields.Many2one('cash.forecast.fiscal.period', string="Forecast Period")
    fiscal_year_id = fields.Many2one("cash.forecast.fiscal.year", string="Fiscal Year")

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute("""
            CREATE or REPLACE view {} as (
                SELECT
                    row_number() OVER() AS id,
                    cf.name AS name,
                    ft.id AS forecast_type_id,
                    fg.id AS cash_forecast_category_id,
                    fg.type AS forecast_type,
                    cp.id AS acc_forecast_period_id,
                    fy.id AS acc_fiscal_year_id,
                    cf.forecast_value AS forecast_value,
                    cf.real_value as real_value,
                    cf.real_value - cf.forecast_value as difference_value,
                    cf.company_id,
                    case when cf.forecast_value > 0 then
                    (cf.forecast_value*100) / sum(cf.forecast_value) over(partition by ft.type, cf.acc_forecast_period_id)
                    else 0 end as percentage_by_type 
                FROM setu_cash_forecast cf
                JOIN setu_cash_forecast_type ft on ft.id = cf.forecast_type_id
                JOIN setu_cash_forecast_categories fg on fg.id = ft.cash_forecast_category_id
                JOIN sh_account_period cp on cp.id =  cf.acc_forecast_period_id
                JOIN sh_fiscal_year fy on fy.id = cp.fiscal_year_id
                WHERE 
                    cf.company_id in (select id from res_company) 
                ORDER BY 
                    fy.date_start
              
            );
        """.format(self._table))
