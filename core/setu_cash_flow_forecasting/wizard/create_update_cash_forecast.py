import json
from datetime import date
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class CreateUpdateCashForecast(models.TransientModel):
    _name = 'create.update.cash.forecast'
    _description = 'Create or Update Cash Forecast from wizard'

    # period_ids = fields.Many2many('cash.forecast.fiscal.period', 'create_update_periods_rel',
    #                               'wizard_id', 'period_id', string="Fiscal Period")
    period_domain = fields.Many2many("cash.forecast.fiscal.period")
    period_id = fields.Many2one('cash.forecast.fiscal.period', string="Fiscal Period")

    acc_period_domain = fields.Many2many("sh.account.period", compute="_compute_period_domain")
    acc_period_id = fields.Many2one('sh.account.period', string="Fiscal Period")

    calculate = fields.Selection([('real', 'Real Value'), ('forecast', 'Forecast Value')], string="Calculate")

    cash_forecast_type_ids = fields.Many2many('setu.cash.forecast.type',
                                              'create_update_cash_forecast_type_rel',
                                              'wizard_id', 'cash_forecast_type_id',
                                              string='Cash Forecast Type')
    help_for_wizard = fields.Text("Help", default='NOTE: \nCash Forecast will be calculated for all months upto the '
                                                  'Fiscal Period that is selected, based on Cash Forecast '
                                                  'Configuration set while creating Cash Forecast Type ')

    @api.depends('calculate')
    def _compute_period_domain(self):
        if self.calculate:
            period_domain = [('date_end', '>=', date.today().strftime('%Y-%m-%d'))] if self.calculate == 'forecast' else [
                    ('date_start', '<', date.today().strftime('%Y-%m-%d'))]
            self.acc_period_domain = [(6, 0, self.env['sh.account.period'].search(period_domain).ids)]
        else:
            self.acc_period_domain = [(6, 0, [])]

    def prepare_create_manual_cash_forecast(self, cash_forecast_type_id, period_id):
        forecast_value = cash_forecast_type_id._get_forecast_value(period_id) or 0.0
        return {
            'name': cash_forecast_type_id.name,
            'forecast_type': cash_forecast_type_id.type,
            'company_id': cash_forecast_type_id.company_id.id,
            'forecast_value': forecast_value,
            'account_ids': [(6, 0, cash_forecast_type_id.account_ids.ids)],
            'dep_forecast_ids': [(6, 0, cash_forecast_type_id.dep_forecast_ids.ids)],
            'acc_forecast_period_id': period_id.id,
            'forecast_type_id': cash_forecast_type_id.id,
            'cash_forecast_category_id': cash_forecast_type_id.cash_forecast_category_id.id,
            # 'forecast_calculation_id': cash_forecast_type_id.calculation_type_id.id,
            'forecast_date': date.today()
        }

    def create_manual_cash_forecast(self, period_id):
        cash_forecast_obj = self.env['setu.cash.forecast']
        cash_forecast_type_ids = self.cash_forecast_type_ids
        if not cash_forecast_type_ids:
            cash_forecast_type_ids = self.env['setu.cash.forecast.type'].search(
                                            ['|', ('calculate_from', '=', 'pending'),
                                             ('acc_forecast_start_period.date_start', '<=', period_id.date_start),
                                             '|', ('acc_forecast_end_period.date_end', '>=', period_id.date_end),
                                             ('acc_forecast_end_period', '=', False)])
        # add opening and closing type
        cash_forecast_type_ids |= self.env['setu.cash.forecast.type'].search([('type', 'in', ['opening', 'closing', 'net_forecast'])])
        if self.cash_forecast_type_ids.dep_forecast_ids:
            cash_forecast_type_ids |= cash_forecast_type_ids.dep_forecast_ids

        for cash_forecast_type_id in cash_forecast_type_ids.sorted('sequence'):
            if checker := cash_forecast_type_id.approve_forecast_type(period_id):
                manual_cash_forecast_vals = {}
                is_previously_created = self.env['setu.cash.forecast'].search(
                    [('acc_forecast_period_id', '=', period_id.id),
                     ('forecast_type_id', '=', cash_forecast_type_id.id),
                     ('company_id', '=', cash_forecast_type_id.company_id.id),
                     ('forecast_type', '=', cash_forecast_type_id.type)], limit=1)

                if not is_previously_created or self.acc_period_id.date_start >= date.today().replace(day=1):
                    manual_cash_forecast_vals = self.prepare_create_manual_cash_forecast(cash_forecast_type_id,
                                                                                         period_id)
                if is_previously_created and self.acc_period_id.date_start >= date.today().replace(day=1):
                    is_previously_created.update(manual_cash_forecast_vals)
                if not is_previously_created:
                    cash_forecast_obj.create(manual_cash_forecast_vals)
        return True

    def create_cash_forecast(self):
        month_start_date = date.today().replace(day=1)
        if self.acc_period_id.date_end < month_start_date:
            raise ValidationError("please select future period")
        cash_forecast_type_ids = self.cash_forecast_type_ids or self.cash_forecast_type_ids.search([
                                                                    ('type', '=', 'opening'),
                                                                    ('company_id', '=', self.env.company.id)])

        cash_forecast = self.env['setu.cash.forecast'].search([('forecast_type_id', 'in', cash_forecast_type_ids.ids),
                                                               ('acc_forecast_period_id.date_start', '>=', month_start_date)
                                                               ])
        period_ids = cash_forecast.mapped('acc_forecast_period_id')

        period_ids |= self.env['sh.account.period'].search([('date_start', '>=', month_start_date),
                                                                     ('date_end', '<=', self.acc_period_id.date_end)])

        for period_id in period_ids:
            self.create_manual_cash_forecast(period_id)
        return True

    def calculate_value(self):
        if self.calculate == 'forecast':
            self.create_cash_forecast()
        else:
            month_start_date = date.today().replace(day=1)
            if self.acc_period_id.date_start <= month_start_date:
                self.env['setu.cash.forecast'].get_real_values(self.acc_period_id.id)
            else:
                raise ValidationError("please select current or past period")
        return {
            'name': _('Cash Forecast'),
            'view_mode': 'pivot,tree,form',
            'res_model': 'setu.cash.forecast',
            # 'view_id': self.env.ref('setu_cash_flow_forecasting.setu_cash_forecast_pivot_view').id,
            'type': 'ir.actions.act_window',
        }

    def update_cash_forecast(self):
        action = self.env.ref('setu_cash_flow_forecasting.actions_create_update_cash_forecast').sudo().read()[0]
        context = self._context.copy()
        wiz = self.create({'cash_forecast_type_ids': [(6, 0, context.get('cash_forecast_type_ids', []))],
                           'acc_period_id': context.get('acc_period_id', False)})
        action['res_id'] = wiz.id
        action['context'] = context
        return action
