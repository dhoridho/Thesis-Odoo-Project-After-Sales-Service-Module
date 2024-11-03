# -*- coding: utf-8 -*-
from odoo import api, models, _


class InsReportBalanceSheet(models.AbstractModel):
    _name = 'report.equip3_accounting_reports.balance_sheet'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.context.get('bs_report'):
            if data.get('report_data'):
                col = 1 + len(data.get('report_data')['years_preview'])
                
                if data.get('report_data')['filters']['debit_credit'] == 'on':
                    col = 1 + (len(data.get('report_data')['years_preview']) * 3)
                
                if data.get('report_data')['filters']['budget'] == 'on':
                    col = 1 + (len(data.get('report_data')['years_preview']) * 2)

                comp_list = data.get('report_data')['comps_list']
                col_total = col * len(comp_list)

                data.update({
                    'Filters': data.get('report_data')['filters'],
                    'report_lines': data.get('report_data')['bs_lines'],
                    'report_name': data.get('report_name'),
                    'title': data.get('report_data')['name'],
                    'company': self.env.company,
                    'bs_lines': data.get('report_data')['bs_lines'],
                    'years_preview': data.get('report_data')['years_preview'],
                    'filter_budget': data.get('report_data')['filters']['filter_budget'],
                    'budget': data.get('report_data')['filters']['budget'],
                    'debit_credit': data.get('report_data')['filters']['debit_credit'],
                    'col' : len(data.get('report_data')['years_preview']),
                    'tot_column' : col - 1,
                    'comps_list' : data.get('report_data')['comps_list'],
                    'comp_names' : data.get('report_data')['comp_names'],
                    'tot_comp_list' : len(data.get('report_data')['comps_list']),
                    'col_total' : col_total,
                    'entities_comparison' : data.get('report_data')['filters']['entities_comparison'],
                    'curr_list' : data.get('report_data')['curr_list'],
                })
        return data
