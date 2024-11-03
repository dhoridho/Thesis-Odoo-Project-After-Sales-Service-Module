from datetime import date, datetime, timedelta
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class SetuCashForecast(models.Model):
    _name = 'setu.cash.forecast'
    _description = "Cash Forecast"
    _inherit = ['mail.thread']

    name = fields.Char('Name')
    company_id = fields.Many2one('res.company', string='Company')
    forecast_type = fields.Selection([('income', 'Cash In'), ('expense', 'Cash OUT'),
                                      ('opening', 'Opening Forecast'), ('net_forecast', 'Net Forecasting'),
                                      ('closing', 'Closing Forecast')],
                                     string="Group")
    forecast_value = fields.Float('Forecast Value')
    auto_calculate = fields.Boolean("Auto Calculate", default=True)
    account_ids = fields.Many2many('account.account', string='Account')
    # parent_forecast_id = fields.Many2one('setu.cash.forecast', string='Parent Forecast')
    # child_forecast_ids = fields.One2many('setu.cash.forecast', 'parent_forecast_id', string="Child Forecast")
    real_value = fields.Float('Real Value')
    difference_value = fields.Float('Difference Value',compute='_compute_difference')
    forecast_date = fields.Date('Forecast Date')
    forecast_period_id = fields.Many2one('cash.forecast.fiscal.period', string='Forecast Period')

    acc_forecast_period_id = fields.Many2one('sh.account.period', string='Forecast Period')

    forecast_type_id = fields.Many2one('setu.cash.forecast.type', string='Forecast Type')
    cash_forecast_category_id = fields.Many2one('setu.cash.forecast.categories', string="Categories Name")
    forecast_property = fields.Selection([('over', 'Over Forecast'),
                                          ('under', 'Under Forecast'),
                                          ('true', 'True Value')], compute='_compute_difference', string="Forecast Property", readonly=True)
    dep_forecast_ids = fields.Many2many('setu.cash.forecast.type', 'cash_forecast_dependent_rel',
                                        string='Dependant Forecast Type')
    # Forecast calculate formula
    # calculate_from = fields.Selection(
    #     [('past_sales', 'Past Sales'), ('past_account_entries', 'Past Accounting Entries'),
    #      ('past_period_forecasting_entries', 'Past Period Forecasting Entries'),
    #      ('pending', 'Pending Payable / Receivable'),
    #      ('dependant', 'Base on Dependant Forecast')],
    #     string="Calculate from")
    # calculation_pattern = fields.Selection([('average', 'Average Value of Last X Days'),
    #                                         ('seasonal', 'Same Period Previous Year')],
    #                                        string="Calculation pattern")
    # multiply_by = fields.Float(string="Multiply by")
    # average_value_of_days = fields.Integer(string="Number of days", default=90)
    # number_of_period_months = fields.Integer(string='Number Of Periods', default=1)

    def _compute_difference(self):
        for frc in self:
            if frc.forecast_value and frc.acc_forecast_period_id and frc.acc_forecast_period_id.date_start < date.today():
                difference_value = frc.real_value - frc.forecast_value
                if (difference_value > 0 and frc.forecast_type == 'income') or \
                        (difference_value < 0 and frc.forecast_type == 'expense'):
                    forecast_property = 'under'
                elif (difference_value < 0 and frc.forecast_type in ['income', 'opening', 'closing']) or \
                        (difference_value > 0 and frc.forecast_type == 'expense'):
                    forecast_property = 'over'
                else:
                    forecast_property = 'true'
                frc.difference_value = difference_value
                frc.forecast_property = forecast_property
            else:
                frc.difference_value = 0
                frc.forecast_property = ''

    @api.constrains('account_ids', 'acc_forecast_period_id', 'forecast_type_id')
    def check_unique(self):
        if duplicate_records := self.search([('id', '!=', self.id), ('account_ids', 'in', self.account_ids.ids),
                                             ('acc_forecast_period_id', '=', self.acc_forecast_period_id.id),
                                             ('forecast_type_id', '=', self.forecast_type_id.id)]):
            raise ValidationError(_('Forecast data not unique.'))

    def _get_opening_balance(self, forecast_type_id, forecast_period_id):
        prev_period_id = self.env['sh.account.period'].search(
            [('date_end', '=', forecast_period_id.date_start - timedelta(days=1))])
        if previous_cash_forecast := self.env['setu.cash.forecast'].search(
                [('forecast_type', '=', 'closing'), ('acc_forecast_period_id', '=', prev_period_id.id)], limit=1):
            return previous_cash_forecast.real_value
        query = """select
                        sum(debit)-sum(credit) as balance
                    from
                        account_move_line
                    where
                        date < '{}' and account_id {} {} 
                """.format(forecast_period_id.date_start, 'in' if len(forecast_type_id.account_ids.ids) > 1 else '=',
                           tuple(forecast_type_id.account_ids.ids) if len(
                               forecast_type_id.account_ids.ids) > 1 else forecast_type_id.account_ids.id)
        self._cr.execute(query)
        return self._cr.fetchall()[0][0]

    def get_forecast_type_real_value(self):
        forecast_type_id = self.forecast_type_id
        forecast_period_id = self.acc_forecast_period_id
        start_date = datetime.combine(forecast_period_id.date_start, datetime.min.time())
        end_date = datetime.combine(forecast_period_id.date_end, datetime.max.time())
        real_values = 0

        if forecast_type_id.type == 'opening':
            real_values = self._get_opening_balance(forecast_type_id, forecast_period_id)

        elif forecast_type_id.type in ['closing', 'net_forecast']:
            current_period_forecasts = self.env['setu.cash.forecast'].search(
                [('acc_forecast_period_id', '=', forecast_period_id.id)])
            opening_forecast_id = current_period_forecasts.filtered(lambda frc: frc.forecast_type == 'opening')
            period_income_forecast_ids = current_period_forecasts.filtered(lambda frc: frc.forecast_type == 'income')
            period_expense_forecast_ids = current_period_forecasts.filtered(lambda frc: frc.forecast_type == 'expense')
            period_income = sum(
                period_income_forecast_ids.mapped('real_value')) if period_income_forecast_ids else 0
            period_expense = sum(
                period_expense_forecast_ids.mapped('real_value')) if period_expense_forecast_ids else 0

            real_values = opening_forecast_id.real_value \
                if forecast_type_id.type == 'closing' else 0 + period_income - period_expense

        elif move_line := self.env['account.move.line'].search(
                [('company_id', '=', self.company_id.id),
                 ('date', '>=', start_date), ('date', '<=', end_date), ('account_id', 'in', self.account_ids.ids)]):
            liability_line = move_line.filtered(lambda line: line.account_id.internal_group in ['liability'])
            liability_amount = sum(liability_line.mapped('debit'))

            asset_line = move_line.filtered(lambda line: line.account_id.internal_group in ['asset'])
            asset_amount = sum(asset_line.mapped('credit'))

            credited_line = move_line.filtered(lambda line: line.account_id.internal_group in ['income'])
            credited_amount = sum(credited_line.mapped('credit')) - sum(credited_line.mapped('debit'))

            debited_line = move_line.filtered(lambda line: line.account_id.internal_group in ['expense'])
            debited_amount = sum(debited_line.mapped('debit')) - sum(debited_line.mapped('credit'))

            real_values = liability_amount + credited_amount + debited_amount + asset_amount

        if forecast_type_id.auto_calculate and forecast_type_id.calculate_from == 'past_account_entries' \
                    and self.forecast_type not in ['opening', 'net_forecast', 'closing'] \
                    and forecast_type_id.real_value_multiply_by:
            real_values *= forecast_type_id.real_value_multiply_by
        return real_values

    def get_real_values(self, period_id=False):
        if period_id:
            period_id = self.env['sh.account.period'].browse(period_id)
            forecast_records = self.search([('acc_forecast_period_id.date_start', '<=', period_id.date_end)])
        else:
            forecast_records = self.search([('acc_forecast_period_id.date_end', '<=', date.today()),
                                            ('real_value', '=', False)])
        period_ids = forecast_records.mapped('acc_forecast_period_id')
        for period in period_ids:
            for forecast_record in forecast_records.filtered(lambda x: x.acc_forecast_period_id.id == period.id
                                                             ).sorted(lambda x: x.forecast_type_id.sequence):
                real_value = forecast_record.get_forecast_type_real_value()
                forecast_record.real_value = real_value

        return True
