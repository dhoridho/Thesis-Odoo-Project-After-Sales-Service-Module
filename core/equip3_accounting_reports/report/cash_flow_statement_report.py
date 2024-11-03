from odoo import api, models, _


class GeneralLedger(models.AbstractModel):
    _name = 'report.equip3_accounting_reports.cash_flow_statement'

    @api.model
    def _get_report_values(self, docids, data=None):
        if self.env.context.get('trial_pdf_report'):
            if data.get('report_data'):
                account_data = data.get('report_data')['report_lines']
                type_report = data.get('report_data')['type_report']

                received_customer = []
                cash_received = []
                payment_supplier = []
                cash_paid = []

                cf_operating_addition = []
                cf_operating_deduction = []
                cf_operating_cashin_indirect = []
                cf_operating_cashout_indirect = []
                net_income = []

                if type_report == 'indirect':
                    cf_operating_addition = self._sum_list(account_data['cf_operating_addition'], 'Addition')
                    cf_operating_deduction = self._sum_list(account_data['cf_operating_deduction'], 'Deduction')
                    cf_operating_cashin_indirect = self._sum_list(account_data['cf_operating_cashin_indirect'], 'Cash in')
                    cf_operating_cashout_indirect = self._sum_list(account_data['cf_operating_cashout_indirect'], 'Cash out')
                    net_income = self._sum_list(account_data['net_income'], 'Net Income')
                    sum_cf_statement = self._sum_list(cf_operating_addition + cf_operating_deduction + cf_operating_cashin_indirect + cf_operating_cashout_indirect + net_income, 'Total cash flow from operating activities')
                else:
                    received_customer = self._sum_list(account_data['received_customer'],'Advance payments received from customers')
                    cash_received = self._sum_list(account_data['cash_received'],'Cash received from')
                    payment_supplier = self._sum_list(account_data['payment_supplier'],'Advance payments made to suppliers')
                    cash_paid = self._sum_list(account_data['cash_paid'],'Cash paid for')
                    sum_cf_statement = self._sum_list(received_customer + cash_received + payment_supplier + cash_paid,'Total cash flow from operating activities')

                cf_investing = self._sum_list(account_data['cf_investing'], "cf_investing")
                cf_finance = self._sum_list(account_data['cf_finance'], "cf_finance")
                cf_unclass = self._check_list(self._sum_list(account_data['cf_unclass'], "cf_unclass"))
                sum_all_cf_statement = self._sum_list(sum_cf_statement + cf_investing + cf_finance + cf_unclass,'Net increase in cash and cash equivalents')
                cf_beginning_period = self._sum_list(account_data['cf_beginning_period'], "Cash and cash equivalents, beginning of period")
                cf_closing_period = self._sum_list(sum_all_cf_statement + cf_beginning_period,'Cash and cash equivalents, closing of period')

                list_previews = []
                list_received_customer = {}
                list_cash_received = {}
                list_payment_supplier = {}
                list_cash_paid = {}
                list_cf_operating_addition = {}
                list_cf_operating_deduction = {}
                list_cf_operating_cashin_indirect = {}
                list_cf_operating_cashout_indirect = {}
                list_net_income = {}
                list_sum_cf_statement = {}
                list_cf_investing = {}
                list_cf_finance = {}
                list_cf_unclass = {}
                list_sum_all_cf_statement = {}
                list_cf_beginning_period = {}
                list_cf_closing_period = {}

                list_report_lines = data.get('report_data')['list_report_lines']
                
                for tmp_report_lines in list_report_lines:
                    list_previews += [tmp_report_lines['name_filter_date']]

                    if type_report == 'indirect':
                        tmp_cf_operating_addition = self._sum_list(tmp_report_lines['cf_operating_addition'], "cf_operating_addition")
                        list_cf_operating_addition.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_operating_addition}})
                        
                        tmp_cf_operating_deduction = self._sum_list(tmp_report_lines['cf_operating_deduction'], "cf_operating_deduction")
                        list_cf_operating_deduction.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_operating_deduction}})
                        
                        tmp_cf_operating_cashin_indirect = self._sum_list(tmp_report_lines['cf_operating_cashin_indirect'], "cf_operating_cashin_indirect")
                        list_cf_operating_cashin_indirect.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_operating_cashin_indirect}})

                        tmp_cf_operating_cashout_indirect = self._sum_list(tmp_report_lines['cf_operating_cashout_indirect'], "cf_operating_cashout_indirect")
                        list_cf_operating_cashout_indirect.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_operating_cashout_indirect}})
                        
                        tmp_net_income = self._sum_list(tmp_report_lines['net_income'], "net_income")
                        list_net_income.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_net_income}})

                        tmp_sum_cf_statement = self._sum_list(tmp_cf_operating_addition + tmp_cf_operating_deduction + tmp_cf_operating_cashin_indirect + tmp_cf_operating_cashout_indirect + tmp_net_income, 'Total cash flow from operating activities')
                    else:
                        tmp_received_customer = self._sum_list(tmp_report_lines['received_customer'],'Advance payments received from customers')
                        list_received_customer.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_received_customer}})

                        tmp_cash_received = self._sum_list(tmp_report_lines['cash_received'],'Cash received from')
                        list_cash_received.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cash_received}})

                        tmp_payment_supplier = self._sum_list(tmp_report_lines['payment_supplier'],'Advance payments made to suppliers')
                        list_payment_supplier.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_payment_supplier}})

                        tmp_cash_paid = self._sum_list(tmp_report_lines['cash_paid'],'Cash paid for')
                        list_cash_paid.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cash_paid}})

                        tmp_sum_cf_statement = self._sum_list(tmp_received_customer + tmp_cash_received + tmp_payment_supplier + tmp_cash_paid,'Total cash flow from operating activities')
                    
                    list_sum_cf_statement.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_sum_cf_statement}})

                    tmp_cf_investing = self._sum_list(tmp_report_lines['cf_investing'], "cf_investing")
                    list_cf_investing.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_investing}})

                    tmp_cf_finance = self._sum_list(tmp_report_lines['cf_finance'], "cf_finance")
                    list_cf_finance.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_finance}})

                    tmp_cf_unclass = self._check_list(self._sum_list(tmp_report_lines['cf_unclass'], "cf_unclass"))
                    list_cf_unclass.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_unclass}})

                    tmp_sum_all_cf_statement = self._sum_list(tmp_sum_cf_statement + tmp_cf_investing + tmp_cf_finance + tmp_cf_unclass,'Net increase in cash and cash equivalents')
                    list_sum_all_cf_statement.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_sum_all_cf_statement}})

                    tmp_cf_beginning_period = self._sum_list(tmp_report_lines['cf_beginning_period'], "Cash and cash equivalents, beginning of period")
                    list_cf_beginning_period.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_beginning_period}})

                    tmp_cf_closing_period = self._sum_list(tmp_sum_all_cf_statement + tmp_cf_beginning_period,'Cash and cash equivalents, closing of period')
                    list_cf_closing_period.update({tmp_report_lines['name_filter_date'] : {"report_name" : tmp_report_lines['name_filter_date'], 'report_lines' : tmp_cf_closing_period}})

                data.update({'account_data': account_data,
                             'type_report': type_report,
                             'received_customer': received_customer,
                             'cash_received': cash_received,
                             'payment_supplier': payment_supplier,
                             'cash_paid': cash_paid,
                             'cf_operating_addition': cf_operating_addition,
                             'cf_operating_deduction': cf_operating_deduction,
                             'cf_operating_cashin_indirect': cf_operating_cashin_indirect,
                             'cf_operating_cashout_indirect': cf_operating_cashout_indirect,
                             'net_income': net_income,
                             'sum_cf_statement': sum_cf_statement,
                             'cf_investing': cf_investing,
                             'cf_finance': cf_finance,
                             'cf_unclass': cf_unclass,
                             'sum_all_cf_statement': sum_all_cf_statement,
                             'cf_beginning_period': cf_beginning_period,
                             'cf_closing_period': cf_closing_period,
                             'Filters': data.get('report_data')['filters'],
                             'company': self.env.company,
                             'list_previews': list_previews,
                             'list_report_lines':list_report_lines,
                             'list_received_customer' : list_received_customer,
                             'list_cash_received' : list_cash_received,
                             'list_payment_supplier' : list_payment_supplier,
                             'list_cash_paid' : list_cash_paid,
                             'list_cf_operating_addition' : list_cf_operating_addition,
                             'list_cf_operating_deduction' : list_cf_operating_deduction,
                             'list_cf_operating_cashin_indirect' : list_cf_operating_cashin_indirect,
                             'list_cf_operating_cashout_indirect' : list_cf_operating_cashout_indirect,
                             'list_net_income' : list_net_income,
                             'list_sum_cf_statement' : list_sum_cf_statement,
                             'list_cf_investing' : list_cf_investing,
                             'list_cf_finance' : list_cf_finance,
                             'list_cf_unclass' : list_cf_unclass,
                             'list_sum_all_cf_statement' : list_sum_all_cf_statement,
                             'list_cf_beginning_period' : list_cf_beginning_period,
                             'list_cf_closing_period' : list_cf_closing_period,
                             })
        return data

    def _check_list(self,list_value):
        values=[]
        check = False
        for rec in list_value:
            if rec['total_debit'] > 0 or rec['total_credit'] > 0 or rec['total_balance'] > 0:
                check = True
        if check == True:
            values = list_value
        return values

    def _sum_list(self,list_value, value_name):
        values=[]
        value =  {'month_part': value_name, 
                  'year_part': 2022, 
                  'total_debit': 0.0, 
                  'total_credit': 0.0, 
                  'total_balance': 0.0}
        for rec in list_value:
            value['total_debit'] += rec['total_debit']
            value['total_credit'] += rec['total_credit']
            value['total_balance'] += rec['total_balance']
        values.append(value)
        return values

    def _sum_list_minus(self,list_value, value_name):
        values=[]
        value =  {'month_part': value_name, 
                  'year_part': 2022, 
                  'total_debit': 0.0, 
                  'total_credit': 0.0, 
                  'total_balance': 0.0}
        i = 0
        max_len = len(list_value)
        while i < max_len:
            if i == 0:
                value['total_debit'] = list_value[i]['total_debit']
                value['total_credit'] = list_value[i]['total_credit']
                value['total_balance'] = list_value[i]['total_balance']
                i += 1
            else:
                value['total_debit'] -= list_value[i]['total_debit']
                value['total_credit'] -= list_value[i]['total_credit']
                value['total_balance'] -= list_value[i]['total_balance']
                i += 1
        values.append(value)
        return values
