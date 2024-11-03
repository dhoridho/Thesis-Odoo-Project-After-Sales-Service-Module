from builtins import str
from datetime import date, datetime, timedelta
from odoo import fields, models, api


class SetuCashFlowForecastingDashboard(models.Model):
    _name = 'setu.cash.flow.forecasting.dashboard'
    _description = 'Cash Forecast Dashboard'

    @api.model
    def get_dashboard_data(self, kwargs=False):
        final_result = []
        filter = kwargs
        filter_today_date = date.today()
        filter_date = date.today()
        if filter is not False:
            if filter[0].get('filter') == 'Current Fiscal Period':

                filter_today_date = self.env['sh.account.period'].search(
                    [('date_start', '<=', date.today()), ('date_end', '>=', date.today())]).date_start
                filter_date = self.env['sh.account.period'].search(
                    [('date_start', '<=', date.today()), ('date_end', '>=', date.today())]).date_end
            elif filter[0].get('filter') == 'Current Fiscal Year':
                filter_today_date = self.env['sh.fiscal.year'].search(
                    [('date_start', '<=', date.today()), ('date_end', '>=', date.today())]).date_start
                filter_date = self.env['sh.fiscal.year'].search(
                    [('date_start', '<=', date.today()), ('date_end', '>=', date.today())]).date_end
            elif filter[0].get('filter') == 'time_period':
                filter_date = datetime.strptime(filter[2].get('date_end'), '%Y-%m-%d').date()
                filter_today_date = datetime.strptime(filter[1].get('date_start'), '%Y-%m-%d').date()
        else:
            filter_today_date = self.env['sh.fiscal.year'].search(
                [('date_start', '<=', date.today()), ('date_end', '>=', date.today())]).date_start
            filter_date = self.env['sh.fiscal.year'].search(
                [('date_start', '<=', date.today()), ('date_end', '>=', date.today())]).date_end

        if not filter_today_date:
            filter_today_date = date.today()
        if not filter_date:
            filter_date = date.today()

        # ORM METHOD START

        data = self.env['setu.cash.forecast'].search([
            ('forecast_type', 'not in', ('opening', 'closing')),
            ('company_id', 'in' if len(self.env.company.ids) > 1 else '=',
             tuple(self.env.company.ids) if len(self.env.company.ids) > 1 else self.env.company.id)
        ]).filtered(lambda f: f.acc_forecast_period_id.date_start and f.acc_forecast_period_id.date_end)

        data = data.filtered(lambda f: f.acc_forecast_period_id.date_start >= filter_today_date and f.acc_forecast_period_id.date_end <= filter_date)

        # Prepare Expense Line Card Chart Data
        expense_line_cart_chart = self.get_card_line_chart_data(search_domain="expense", start_date=filter_today_date,
                                                                end_date=filter_date)

        # Prepare Income Line Card Chart Data
        income_line_cart_chart = self.get_card_line_chart_data(search_domain="income", start_date=filter_today_date,
                                                               end_date=filter_date)

        # Prepare income vs expanse ratio bar chart data
        income_vs_expanse_ratio_chart = self.get_income_vs_expanse_ratio_bar_chart_data(start_date=filter_today_date,
                                                                                        end_date=filter_date)

        # Prepare income vs expanse Value bar chart data
        income_vs_expanse_value_chart = self.get_income_vs_expanse_value_bar_chart_data(start_date=filter_today_date,
                                                                                        end_date=filter_date)

        # Prepare expense doughnut chart
        expense_dougnut_data = data.search([('forecast_type', '=', "expense")]).filtered(lambda f: f.acc_forecast_period_id.date_start and f.acc_forecast_period_id.date_end)
        expense_dougnut_data = expense_dougnut_data.filtered(lambda f: f.acc_forecast_period_id.date_start >= filter_today_date and f.acc_forecast_period_id.date_end <= filter_date).mapped('forecast_value')
        expense_dougnut_forecast_value = sum(x for x in expense_dougnut_data)
        expense_dougnut_real_value = sum(
            x for x in data.search([('forecast_type', '=', "expense")]).mapped('real_value'))

        forecast_expanse_data = [round(expense_dougnut_forecast_value, 2), expense_dougnut_real_value]
        forecast_expanse_label = ["Forecast Expense", "Real Expense"]

        # Prepare income doughnut chart
        income_dougnut_data = data.search([('forecast_type', '=', "income")]).filtered(lambda f: f.acc_forecast_period_id.date_start and f.acc_forecast_period_id.date_end)
        
        income_dougnut_data = income_dougnut_data.filtered(lambda f: f.acc_forecast_period_id.date_start >= filter_today_date and f.acc_forecast_period_id.date_end <= filter_date).mapped('forecast_value')
        income_dougnut_forecast_value = sum(x for x in income_dougnut_data)
        income_dougnut_real_value = sum(x for x in data.search([('forecast_type', '=', "income")]).mapped('real_value'))

        forecast_income_data = [round(income_dougnut_forecast_value, 2), income_dougnut_real_value]
        forecast_income_label = ["Forecast Income", "Real Income"]

        # Add Currency symbol in income and expense chart value
        if self.env.company.currency_id.position == "before":
            forecast_expanse_display_data = [
                self.env.company.currency_id.symbol + " " + str(round(expense_dougnut_forecast_value, 2)),
                self.env.company.currency_id.symbol + " " + str(expense_dougnut_real_value)]
            forecast_income_display_data = [
                self.env.company.currency_id.symbol + " " + str(round(income_dougnut_forecast_value, 2)),
                self.env.company.currency_id.symbol + " " + str(income_dougnut_real_value)]
        else:
            forecast_expanse_display_data = [
                str(round(expense_dougnut_forecast_value, 2)) + " " + self.env.company.currency_id.symbol,
                str(expense_dougnut_real_value) + " " + self.env.company.currency_id.symbol]
            forecast_income_display_data = [
                str(round(income_dougnut_forecast_value, 2)) + " " + self.env.company.currency_id.symbol,
                str(income_dougnut_real_value) + " " + self.env.company.currency_id.symbol]

        final_expense_doughnut_chart_data = {
            'final_expense_doughnut_chart_data': [forecast_expanse_label, forecast_expanse_data,
                                                  forecast_expanse_display_data]}
        final_income_doughnut_chart_data = {
            'final_income_doughnut_chart_data': [forecast_income_label, forecast_income_data,
                                                  forecast_income_display_data]}

        # Prepare expanse Bar Chart Data
        expanse_bar_chart_result = self.get_bar_chart_date(search_domain='expense', start_date=filter_today_date,
                                                           end_date=filter_date)

        # Prepare income Bar Chart Data
        income_bar_chart_result = self.get_bar_chart_date(search_domain='income', start_date=filter_today_date,
                                                          end_date=filter_date)

        # Prepare expanse Line Chart Data
        expanse_line_chart_result = self.get_line_chart_data(search_domain='expense', start_date=filter_today_date,
                                                             end_date=filter_date)

        # Prepare income Line Chart Data
        income_line_chart_result = self.get_line_chart_data(search_domain='income', start_date=filter_today_date,
                                                             end_date=filter_date)

        # ORM METHOD END


        table_data = {'table_data': 'dashboard_data'}
        final_result.append(table_data)

        chart_data = []
        chart_data = {'chart_data': chart_data}
        final_result.append(chart_data)

        expense_chart_data = {'expense_chart_data': expanse_bar_chart_result}
        final_result.append(expense_chart_data)

        final_expense_chart_data = []
        final_expense_chart_data.append(expanse_line_chart_result)

        income_chart_data = {'income_chart_data': income_bar_chart_result}
        final_result.append(income_chart_data)


        final_income_chart_data = []
        final_income_chart_data.append(income_line_chart_result)
        final_result.append(final_expense_chart_data)
        final_result.append(final_income_chart_data)

        # Prepare Expanse Vs Income Ratio Chart
        try:
            forecast_expanse_list = forecast_expanse_data[0] / forecast_income_data[0]
        except ZeroDivisionError:
            forecast_expanse_list = 0.0

        try:
            forecast_expanse_list2 = forecast_expanse_data[1] / forecast_income_data[1]
        except ZeroDivisionError:
            forecast_expanse_list2 = 0.0

        total_Forecast_ratio = [round(forecast_expanse_list, 2), round(forecast_expanse_list2, 2)]
        if self.env.company.currency_id.position == "before":
            total_Forecast_ratio_data = [
                self.env.company.currency_id.symbol + " " + str(round(forecast_expanse_list, 2)),
                self.env.company.currency_id.symbol + " " + str(round(forecast_expanse_list2, 2))]
        else:
            total_Forecast_ratio_data = [
                str(round(forecast_expanse_list, 2)) + " " + self.env.company.currency_id.symbol,
                str(round(forecast_expanse_list2, 2)) + " " + self.env.company.currency_id.symbol]
        total_Forecast_ratio_label = ["Forecast Income Vs Expenses ratio", "Real Income Vs Expenses ratio"]
        final_income_vs_income_doughnut_chart_data = {
            'final_income_vs_income_doughnut_chart_data': [total_Forecast_ratio_label, total_Forecast_ratio,
                                                           total_Forecast_ratio_data]}

        final_result.append(final_expense_doughnut_chart_data)
        final_result.append(final_income_doughnut_chart_data)
        final_result.append(final_income_vs_income_doughnut_chart_data)

        # Prepare Fiscal Period Data
        fiscal_data = self.env['sh.account.period'].search([])
        fiscal_period = []
        for data in fiscal_data:
            fiscal_period.append([data.code, data.date_start, data.date_end])
        final_result.append(fiscal_period)

        final_result.append(expense_line_cart_chart)
        final_result.append(income_line_cart_chart)
        final_result.append(self.env.company.currency_id.symbol)

        final_result.append(income_vs_expanse_value_chart)
        final_result.append(income_vs_expanse_ratio_chart)

        return final_result

    def get_bar_chart_date(self, search_domain, start_date, end_date):
        income_types = self.env['setu.cash.forecast.type'].search([('type', '=', search_domain)])
        income_list_data = []
        for type_record in income_types:
            data = {}
            data_case = self.env['setu.cash.forecast'].search([('forecast_type_id', '=', type_record.id)]).filtered(lambda f: f.acc_forecast_period_id.date_start and f.acc_forecast_period_id.date_end)
            data_case = data_case.filtered(lambda f: f.acc_forecast_period_id.date_start >= start_date and f.acc_forecast_period_id.date_end <= end_date)
            if data_case:
                data['name'] = type_record.name
                data['forecast_value'] = sum(data_case.mapped('forecast_value'))
                data['real_value'] = sum(data_case.mapped('real_value'))
                income_list_data.append(data)
        return income_list_data

    def get_line_chart_data(self, search_domain, start_date, end_date):
        types = self.env['setu.cash.forecast.type'].search([('type', '=', search_domain)])
        test = self.env['setu.cash.forecast'].search([('forecast_type_id', 'in', types.ids)], order='acc_forecast_period_id').filtered(lambda f: f.acc_forecast_period_id.date_start and f.acc_forecast_period_id.date_end)
        test = test.filtered(lambda f: f.acc_forecast_period_id.date_start >= start_date and f.acc_forecast_period_id.date_end <= end_date).mapped('acc_forecast_period_id')
        list_data = []

        for type_record in types:
            data = {}
            forecast_value_list = []
            data_case = self.env['setu.cash.forecast'].search([('forecast_type_id', '=', type_record.id)])
            if data_case:
                data['name'] = type_record.name
                data['forecast_period'] = test.mapped('code')
                temp_list = [data_case.filtered(lambda xx: x.code == xx.acc_forecast_period_id.code) for x in test]
                for x in temp_list:
                    if x:
                        forecast_value_list.append(x.forecast_value)
                    else:
                        forecast_value_list.append(0)
                data['forecast_value'] = forecast_value_list
                list_data.append(data)
        return list_data

    def get_card_line_chart_data(self,search_domain,start_date,end_date):
        periods = self.env['sh.account.period'].search([])
        list_data = []
        month = []
        total = []
        data = {}
        for period in periods:
            data = {}
            data_case = self.env['setu.cash.forecast'].search([('acc_forecast_period_id', '=', period.id), ('forecast_type', '=', search_domain)]).filtered(lambda f: f.acc_forecast_period_id.date_start and f.acc_forecast_period_id.date_end)
            data_case = data_case.filtered(lambda f: f.acc_forecast_period_id.date_start >= start_date and f.acc_forecast_period_id.date_end <= end_date)
            if data_case:
                data['month'] = month.append(period.code)
                data['total'] = total.append(sum(data_case.mapped('forecast_value')))
        data['month'] = month
        if self.env.company.currency_id.position == "before":
            data['currency'] = [self.env.company.currency_id.symbol + "" + str(suit) for suit in total]
        else:
            data['currency'] = [str(suit) + "" + self.env.company.currency_id.symbol for suit in total]
        data['total'] = total
        return data

    def get_income_vs_expanse_ratio_bar_chart_data(self, start_date, end_date):
        start_date = self.env['sh.fiscal.year'].search(
            [('date_start', '<=', date.today()), ('date_end', '>=', date.today())]).date_start
        end_date = self.env['sh.fiscal.year'].search(
            [('date_start', '<=', date.today()), ('date_end', '>=', date.today())]).date_end
        data = self.env['sh.fiscal.year'].search(
            [('date_start', '>=', start_date), ('date_end', '<=', end_date)])
        result = []
        dict = {}
        for fiscal_period in data.period_ids:
            total_income = self.env['setu.cash.forecast'].search(
                [('acc_forecast_period_id', '=', fiscal_period.id), ('forecast_type', '=', 'income')]).mapped(
                'forecast_value')
            total_expanse = self.env['setu.cash.forecast'].search(
                [('acc_forecast_period_id', '=', fiscal_period.id), ('forecast_type', '=', 'expense')]).mapped(
                'forecast_value')
            result.append({fiscal_period.code: round((sum(total_income) or 0) / (sum(total_expanse) or 1), 2)})
        return result

    def get_income_vs_expanse_value_bar_chart_data(self, start_date, end_date):
        start_date = self.env['sh.fiscal.year'].search(
            [('date_start', '<=', date.today()), ('date_end', '>=', date.today())]).date_start
        end_date = self.env['sh.fiscal.year'].search(
            [('date_start', '<=', date.today()), ('date_end', '>=', date.today())]).date_end
        data = self.env['sh.fiscal.year'].search(
            [('date_start', '>=', start_date), ('date_end', '<=', end_date)])
        result = []
        dict = {}
        for fiscal_period in data.period_ids:
            total_income = self.env['setu.cash.forecast'].search(
                [('acc_forecast_period_id', '=', fiscal_period.id), ('forecast_type', '=', 'income')]).mapped(
                'forecast_value')
            total_expanse = self.env['setu.cash.forecast'].search(
                [('acc_forecast_period_id', '=', fiscal_period.id), ('forecast_type', '=', 'expense')]).mapped(
                'forecast_value')
            result.append({fiscal_period.code: [sum(total_income) or 0, sum(total_expanse) or 0]})
        return result
