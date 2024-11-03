from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import json


class SetuCashForecastGroup(models.Model):
    _name = 'setu.cash.forecast.categories'
    _description = "Cash Forecast Category"
    _order = 'sequence'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    is_group_for_opening = fields.Boolean("Is Group For Opening Balance", default=False)
    type = fields.Selection([('income', 'Cash In'), ('expense', 'Cash Out'),
                             ('opening', 'Opening Forecast'), ('net_forecast', 'Net Forecasting'),
                             ('closing', 'Closing Forecast')],
                            string="Group")
    # [Dipesh] create field for store kanban_dashboard_graph data
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            name=_("%s (copy)") % (self.name or ''))
        return super(SetuCashForecastGroup, self).copy(default)

    # [Dipesh] getting cash forecast categories and generate json data for chart
    def _kanban_dashboard_graph(self):
        for data in self:
            data.kanban_dashboard_graph = json.dumps(data.get_bar_graph_datas())

    # [Dipesh] method for generate json chart data
    def get_bar_graph_datas(self):

        types = self.env['setu.cash.forecast.type'].search([('cash_forecast_category_id.id', '=', self.id)])
        list_data = []
        for type_record in types:
            data = {}
            data_case = self.env['setu.cash.forecast'].search([('forecast_type_id', '=', type_record.id)])
            if data_case:
                data['label'] = type_record.name
                data['value'] = sum(data_case.mapped('forecast_value'))
                data['type'] = 'future'
                list_data.append(data)
        result_data = list_data

        # record = self.env['setu.cash.forecast.type'].search([('cash_forecast_category_id.id', '=', self.id)])
        # result_data = []
        # if record:
        #     for data in record:
        #         result = self.env['setu.cash.forecast'].search([('forecast_type', '=', data.type), ('name', '=', data.name)])
        #         if result:
        #             for value in result:
        #                 result_data.append({'label': value.display_name, 'value': value.forecast_value, 'type': 'future'})
        if result_data.__len__():
            return [{'values': result_data, 'title': "graph_title"}]
        else:
            return [{'values': [{'label': 'No Data Found', 'value': 0, 'type': ''}], 'title': "dummy"}]

    # [Dipesh] Create action for open setu.cash.forecast.categories form view when click on kanban view title
    def open_action(self):
        return {
            'name': _('Refund Orders'),
            'view_mode': 'form',
            'res_model': 'setu.cash.forecast.categories',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
        }

    @api.constrains('name')
    def _check_forecast_categories(self):
        duplicate_records = self.search([('id', '!=', self.id),
                                         ('name', '=', self.name)])
        if duplicate_records:
            raise ValidationError(_('Forecast Category you want to create is duplicate'))


class CashForcastTag(models.Model):
    _name = "cash.forecast.tag"

    def _set_account_company(self):
        return self._context.get('company_id', False) or self.env.company.id

    name = fields.Char("Name")
    company_id = fields.Many2one('res.company', string='Company', default=_set_account_company)
    account_ids = fields.One2many('account.account', 'cash_forecast_tag', string='Accounts')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        default = dict(default or {})
        default.update(
            name=_("%s (copy)") % (self.name or ''))
        return super(CashForcastTag, self).copy(default)
    
    @api.constrains('name', 'company_id')
    def _check_forecast_tag(self):
        duplicate_records = self.search([('id', '!=', self.id),
                                         ('name', '=', self.name),
                                         ('company_id', '=', self.company_id.id)])
        if duplicate_records:
            raise ValidationError(_('Forecast Category you want to create is duplicate'))
