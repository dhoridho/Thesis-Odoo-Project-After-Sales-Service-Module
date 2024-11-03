# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta



class ShFiscalYear(models.Model):
    _inherit = 'sh.fiscal.year'

    def action_create_init(self, periode=False):
        data_financial_report = self.env['ctm.dynamic.balance.sheet.report']
        list_period = self.get_list_period(periode)
        vals = {'all_account': 'on'}
        reports = ["Balance Sheet", "Profit and Loss"]
        if list_period:
            for report in reports:
                for period_line in list_period:
                    check_period_line = self.check_period(report, period_line['period'], str(self.company_id.id))
                    if check_period_line:
                        self.delete_period(report, period_line['period'], str(self.company_id.id))
                        check_period_line_value = self.check_period(report, period_line['period'], str(self.company_id.id))
                        if not check_period_line_value:
                            create_periode = True
                        else:
                            create_periode = False
                    else:
                        create_periode = True
                    if create_periode:
                        vals.update({'date_from': period_line['date_start'], 'date_to': period_line['date_end']})
                        financial_report = data_financial_report.create(vals)
                        view_report = financial_report.view_report(financial_report.ids, report)
                        if "bs_lines" in view_report:
                            for view_report_line in view_report['bs_lines']:
                                tmp_line={}
                                if 'code' in view_report_line:
                                    company_id = self.company_id
                                    currency = company_id.currency_id
                                    symbol = currency.symbol
                                    position = currency.position
                                    amount_balance = view_report_line[view_report_line['code_anl']]
                                    if position == "before":
                                        debit_amount = 0.00
                                        credit_amount = 0.00
                                        balance_amount = float(amount_balance.replace(symbol + " ", "").replace(",", ""))
                                    else:
                                        debit_amount = 0.00
                                        credit_amount = 0.00
                                        balance_amount = float(amount_balance.replace(" " + symbol, "").replace(",", ""))

                                    tmp_line['name'] = view_report_line['name']
                                    tmp_line['report_name'] = report
                                    tmp_line['account_id'] = view_report_line['id']
                                    tmp_line['company_id'] = company_id.id
                                    tmp_line['currency_id'] = currency.id
                                    tmp_line['debit_amount'] = debit_amount
                                    tmp_line['credit_amount'] = credit_amount
                                    tmp_line['balance_amount'] = balance_amount
                                    tmp_line['period_id'] = period_line['period']
                                    tmp_line['valid_value'] = True
                                    create_line_init = self.env['initial.balance.line']
                                    create_line_init.create(tmp_line)
                                    period_lines = self.env['sh.account.period'].search([('id', '=', period_line['period'])])
                                    period_lines.write({'valid_value' : True})

    def get_list_period(self, periode=False):
        if periode:
            period = 'and sap.id = %s'
        else:
            period = ''
        sql = ('''SELECT 
                        sfy.id as fiscal_year_id, 
                        sfy.name as fiscal_year_name, 
                        sfy.code as fiscal_year_code,
                        sap.id as period,
                        sap.name as periode_name,
                        sap.code as period_code,
                        sap.date_start as date_start,
                        sap.date_end as date_end,
                        sap.valid_value as valid_value
                  FROM sh_fiscal_year sfy 
                  inner join sh_account_period sap on sfy.id=sap.fiscal_year_id
                  Where sfy.company_id = %s
                  ''' + period +
                  ''' order by date_start asc'''
              )
        if periode:
            params = [str(self.company_id.id), str(periode)]
        else:
            params = [str(self.company_id.id)]
        self.env.cr.execute(sql, params)
        period_lines = self.env.cr.dictfetchall()
        return period_lines

    def check_period(self, report_name, period, company):
        sql = ('''SELECT 
                        ibl.id as id, 
                        ibl.report_name as report_name, 
                        ibl.account_id as account_id, 
                        ibl.period_id as period_id, 
                        ibl.valid_value as valid_value 
                  FROM initial_balance_line ibl
                  WHERE report_name = %s AND period_id  = %s AND company_id = %s '''
              )
        params = [str(report_name), str(period), str(company)]
        self.env.cr.execute(sql, params)
        period_line = self.env.cr.dictfetchall()
        return period_line

    def delete_period(self, report_name, period, company):
        sql = ('''DELETE FROM initial_balance_line ibl
                  WHERE ibl.id in ( SELECT ibl2.id as id FROM initial_balance_line ibl2 
                                    WHERE valid_value = false AND report_name = %s AND period_id  = %s AND company_id = %s) '''
              )
        params = [str(report_name), str(period), str(company)]
        self.env.cr.execute(sql, params)

    def check_period_value(self, company, date_period):
        sql = ('''SELECT 
                        sfy.id as fiscal_year_id, 
                        sfy.name as fiscal_year_name, 
                        sfy.code as fiscal_year_code,
                        sap.id as period,
                        sap.name as periode_name,
                        sap.code as period_code,
                        sap.date_start as date_start,
                        sap.date_end as date_end,
                        sap.valid_value as valid_value
                    FROM sh_fiscal_year sfy 
                    inner join sh_account_period sap on sfy.id = sap.fiscal_year_id
                    Where sfy.company_id = %s and sap.valid_value = true and sap.date_start > %s
                    order by sap.date_start desc, sap.code desc 
                    '''
              )
        params = [str(company), str(date_period)]
        self.env.cr.execute(sql, params)
        period_line = self.env.cr.dictfetchall()
        return period_line

    def create_fs(self):
        for res_line in self:
            period_lines = self.env['sh.account.period'].search([('fiscal_year_id', '=', res_line.id)])
            if period_lines:
                for period_line in period_lines:
                    if period_line.state == 'done':
                        self.action_create_init(periode=period_line.id)
                    if period_line.state == 'draft':
                        initial_balances = self.env['initial.balance.line'].search([('period_id', '=', period_line.id)])
                        for initial_line in initial_balances:
                            initial_line.write({'valid_value' : False})
                        period_line.write({'valid_value' : False})
                        check_period_value_ids = self.check_period_value(self.company_id.id, period_line.date_end)
                        if check_period_value_ids:
                            for check_period_value_id in check_period_value_ids:
                                initial_balances1 = self.env['initial.balance.line'].search([('period_id', '=', check_period_value_id['period'])])
                                for initial_line1 in initial_balances1:
                                    initial_line1.write({'valid_value' : False})
                                line_periode = self.env['sh.account.period'].search([('id', '=', check_period_value_id['period'])])
                                line_periode.write({'valid_value' : False, 'state': 'draft'})

    def close_fiscal_year_approve(self):
        res = super(ShFiscalYear, self).close_fiscal_year_approve()
        for rec in self:
            if rec.state == 'done':
                rec.create_fs()
        return res

    def re_open_fiscal_year_approve(self):
        date_now = date.today()
        for rec in self:
            sql = ( """
                        SELECT 
                            sfy.id as fiscal_year_id, 
                            sap.id as period,
                            sap.date_start as date_start,
                            sap.date_end as date_end
                        FROM sh_fiscal_year sfy 
                        inner join sh_account_period sap on sfy.id = sap.fiscal_year_id
                        Where (sfy.company_id = %s and sap.date_end >= %s) and sap.date_start <= %s  
                    """
                   )
            params = [str(rec.company_id.id), date_now, date_now]
            self.env.cr.execute(sql, params)
            period_line_bydate = self.env.cr.dictfetchall()
            # if period_line_bydate:
            #     continue
            #     # if period_line_bydate[0]["fiscal_year_id"] != rec.fiscal_year_id.id:
            #     #     raise UserError(_("diferent fiscal years\ncan't re-open period"))
            # else:
            #     raise UserError(_("diferent fiscal years\ncan't re-open period"))

        super(ShFiscalYear, self).re_open_fiscal_year_approve()
        for rec in self:
            if rec.state == 'draft':
                rec.create_fs()

    def re_open_fiscal_year(self):
        date_now = date.today()
        for rec in self:
            sql = ( """
                        SELECT 
                            sfy.id as fiscal_year_id, 
                            sap.id as period,
                            sap.date_start as date_start,
                            sap.date_end as date_end
                        FROM sh_fiscal_year sfy 
                        inner join sh_account_period sap on sfy.id = sap.fiscal_year_id
                        Where (sfy.company_id = %s and sap.date_end >= %s) and sap.date_start <= %s  
                    """
                   )
            params = [str(rec.company_id.id), date_now, date_now]
            self.env.cr.execute(sql, params)
            period_line_bydate = self.env.cr.dictfetchall()
            # if period_line_bydate:
            #     continue
            #     # if period_line_bydate[0]["fiscal_year_id"] != rec.fiscal_year_id.id:
            #     #     raise UserError(_("diferent fiscal years\ncan't re-open period"))
            # else:
            #     raise UserError(_("diferent fiscal years\ncan't re-open period"))
        
        super(ShFiscalYear, self).re_open_fiscal_year()
        for rec in self:
            if rec.state == 'draft':
                rec.create_fs()

class BSAccountLine(models.Model):
    _name = 'initial.balance.line'
    _description = "initial Balance Sheet"

    
    name = fields.Char("Account Name", related='account_id.name')
    report_name = fields.Char("Report Name")
    account_id = fields.Many2one('account.account', string="Account")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Account Currency')
    debit_amount = fields.Monetary("Debit amount")
    credit_amount = fields.Monetary("Credit Amount")
    balance_amount = fields.Monetary("Balance Amount")
    period_id = fields.Many2one('sh.account.period', string="Peroid")
    valid_value = fields.Boolean("Valid Value")

    @api.model_create_multi
    def create(self, vals_list):
        rslt = super(BSAccountLine, self).create(vals_list)
        return rslt

class ShAccountPeriod(models.Model):
    _inherit = 'sh.account.period'
    
    valid_value = fields.Boolean("Valid Value")
    company_id = fields.Many2one('res.company', string='Company', related='fiscal_year_id.company_id')

    @api.model
    def _create_init_balance(self):
        for rec in self:
            if rec.state == 'done':
                rec.fiscal_year_id.action_create_init(periode=rec.id)
            if rec.state == 'draft':
                initial_balances = self.env['initial.balance.line'].search([('period_id', '=', rec.id)])
                for initial_line in initial_balances:
                    initial_line.write({'valid_value' : False})
                rec.write({'valid_value' : False})
                check_period_value_ids = rec.fiscal_year_id.check_period_value(rec.company_id.id, rec.date_end)
                if check_period_value_ids:
                    for check_period_value_id in check_period_value_ids:
                        initial_balances1 = self.env['initial.balance.line'].search([('period_id', '=', check_period_value_id['period'])])
                        for initial_line1 in initial_balances1:
                            initial_line1.write({'valid_value' : False})
                        line_periode = self.env['sh.account.period'].search([('id', '=', check_period_value_id['period'])])
                        line_periode.write({'valid_value' : False, 'state': 'draft'})

    def close_period(self):
        super(ShAccountPeriod, self).close_period()
        for rec in self:
            if rec.state == 'done':
                rec._create_init_balance()

    def reopen_period(self):
        for rec in self:
            date_now = date.today()
            sql = ( """
                        SELECT 
                            sfy.id as fiscal_year_id, 
                            sap.id as period,
                            sap.date_start as date_start,
                            sap.date_end as date_end
                        FROM sh_fiscal_year sfy 
                        inner join sh_account_period sap on sfy.id = sap.fiscal_year_id
                        Where (sfy.company_id = %s and sap.date_end >= %s) and sap.date_start <= %s  
                    """
                   )
            params = [str(rec.company_id.id), date_now, date_now]
            self.env.cr.execute(sql, params)
            period_line_bydate = self.env.cr.dictfetchall()
            # if period_line_bydate:
            #     if period_line_bydate[0]["fiscal_year_id"] != rec.fiscal_year_id.id:
            #     # if period_line_bydate[0]["fiscal_year_id"] != rec.id:
            #         raise UserError(_("diferent fiscal years\ncan't re-open period"))
            # else:
            #     raise UserError(_("diferent fiscal years\ncan't re-open period"))
        super(ShAccountPeriod, self).reopen_period()
        for rec in self:
            if rec.state == 'draft':
                rec._create_init_balance()
            
    def close_period_approve(self):
        super(ShAccountPeriod, self).close_period_approve()
        for rec in self:
            if rec.state == 'done':
                rec._create_init_balance()

    def reopen_period_approve(self):
        super(ShAccountPeriod, self).reopen_period_approve()
        for rec in self:
            if rec.state == 'draft':
                rec._create_init_balance()

