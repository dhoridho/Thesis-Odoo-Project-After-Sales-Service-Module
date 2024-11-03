# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from datetime import datetime, date
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

class TenancyReport(models.AbstractModel):
    _name = 'report.equip3_property_report.template_report'
    _description = "In Depth Tenancy Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        get_to = data['form']['to_date']
        get_from = data['form']['from_date']
        get_rental_ids = data['form']['rental_ids']
        docs = [] 
        to_date = datetime.strptime(get_to, '%Y-%m-%d').date()
        from_date = datetime.strptime(get_from, '%Y-%m-%d').date()
        renter_ids  = self.env['renter.history'].search([])
        rental_ids = self.env['res.partner'].search([('id','in', get_rental_ids)])
        invoice_ids = self.env['account.move'].search([('partner_id', 'in', get_rental_ids)])
        # if not contract_obj:
        #     raise UserError(_("Expired 1 Contract is not available in this Date Range."))

        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'report_date':fields.Date.today(),
            'from_date':from_date,
            'to_date':to_date,
            'rental_ids': rental_ids,
            'invoice_ids': invoice_ids,
            'renter_ids': renter_ids,
}
        
class RevenueForecast(models.AbstractModel):
    _name = 'report.equip3_property_report.revenue_forecast_template_report'
    _description = "Revenue Forecast Report"
    
    @api.model
    def _get_report_values(self, docids, data=None):
        get_from = data['form']['start_date']
        get_to = data['form']['end_date']
        get_invoice_ids = data['form']['invoice_ids']
        get_user = data['form']['user_id']
        docs = [] 
        to_date = datetime.strptime(get_to, '%Y-%m-%d').date()
        from_date = datetime.strptime(get_from, '%Y-%m-%d').date()
        invoice_ids_paid = self.env['account.move'].search([('id','in', get_invoice_ids), ('payment_state','=','paid')])
        invoice_ids_not_paid = self.env['account.move'].search([('id','in', get_invoice_ids), ('payment_state','=','not_paid')])
        sum_invoice_paid = sum(invoice_ids_paid.mapped('amount_total'))
        sum_invoice_not_paid = sum(invoice_ids_not_paid.mapped('amount_total'))
        user_ids = self.env['res.users'].search([('id','in',[get_user])])
        
        realizable_revenue = []
        expected_revenue_total = 0
        start_date = datetime.strftime(from_date, '%m/%d/%Y')
        start_date = datetime.strptime(start_date, '%m/%d/%Y').date()
        end_date = datetime.strftime(to_date, '%m/%d/%Y')
        end_date = datetime.strptime(end_date, '%m/%d/%Y').date()
        
        agree = self.env['agreement'].search([('property_id','!=',False), ('invoice_type', '=', 'recurring'), ('is_template', '=', False)])
        if agree:
            for agr in agree:
                if agr.stage_id.name == 'Active':
                    recurring = self.env['agreement.recurring.invoice'].search([('id','=',agr.recurring_invoice_id.id)])
                    if recurring.recurring_type == 'monthly':
                        if agr.next_invoice >= start_date:
                            next_invoice = agr.next_invoice
                        else:
                            next = agr.next_invoice
                            while next <= end_date:
                                next = agr.next_invoice + relativedelta(months=+recurring.month)
                                if next >= start_date:
                                    next_invoice = next
                                    break
                        while next_invoice <= end_date:
                            if next_invoice >= agr.end_date:
                                break
                            vals = {
                                'property': agr.property_id.name,
                                'contract': agr.name,
                                'invoice_date': next_invoice,
                                'invoice_amount': agr.amount_total,
                            }
                            realizable_revenue.append(vals)
                            expected_revenue_total += agr.amount_total
                            next_invoice = next_invoice + relativedelta(months=+recurring.month)
                    
                    elif recurring.recurring_type == 'yearly':
                        if agr.next_invoice >= start_date:
                            next_invoice = agr.next_invoice
                        else:
                            next = agr.next_invoice
                            while next <= end_date:
                                next = agr.next_invoice + relativedelta(years=+recurring.year)
                                if next >= start_date:
                                    next_invoice = next
                                    break
                        while next_invoice <= end_date:
                            if next_invoice >= agr.end_date:
                                break
                            vals = {
                                'property': agr.property_id.name,
                                'contract': agr.name,
                                'invoice_date': next_invoice,
                                'invoice_amount': agr.amount_total,
                            }
                            realizable_revenue.append(vals)
                            expected_revenue_total += agr.amount_total
                            next_invoice = next_invoice + relativedelta(years=+recurring.year)
                            
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'report_date':fields.Date.today(),
            'from_date':from_date,
            'to_date':to_date,
            'realizable_revenue': realizable_revenue,
            'expected_revenue_total': expected_revenue_total,
            'invoice_ids_paid': invoice_ids_paid,
            'invoice_ids_not_paid': invoice_ids_not_paid,
            'sum_invoice_paid': sum_invoice_paid,
            'sum_invoice_not_paid': sum_invoice_not_paid,
            'user_ids': user_ids,
        }

class ExpenseForecast(models.AbstractModel):
    _name = 'report.equip3_property_report.expense_forecast_template_report'
    _description = "Revenue Forecast Report"
    
    @api.model
    def _get_report_values(self, docids, data=None):
        get_from = data['form']['start_date']
        get_to = data['form']['end_date']
        get_user = data['form']['user_id']
        mwo_ids = data['form']['mwo']
        mro_ids = data['form']['mro']
        expense_ids = data['form']['expense']
        bill_ids = data['form']['bills']
        docs = [] 
        to_date = datetime.strptime(get_to, '%Y-%m-%d').date()
        from_date = datetime.strptime(get_from, '%Y-%m-%d').date()
        user_ids = self.env['res.users'].search([('id','in',[get_user])])
        mwo_done = self.env['maintenance.work.order'].search([('id','in',mwo_ids), ('state_id','=','done')])
        mro_done = self.env['maintenance.repair.order'].search([('id','in',mro_ids), ('state_id','=','done')])
        mwo_progress = self.env['maintenance.work.order'].search([('id','in',mwo_ids), ('state_id','in',['in_progress','pending'])])
        mro_progress = self.env['maintenance.repair.order'].search([('id','in',mro_ids), ('state_id','in',['in_progress','pending'])])
        sum_mwo_done = sum(mwo_done.mapped('amount_total'))
        sum_mro_done = sum(mro_done.mapped('amount_total'))
        sum_mwo_progress = sum(mwo_progress.mapped('amount_total'))
        sum_mro_progress = sum(mro_progress.mapped('amount_total'))
        bill_paid = self.env['account.move'].search([('id','in', bill_ids), ('payment_state','=','paid')])
        bill_unpaid = self.env['account.move'].search([('id','in', bill_ids), ('payment_state','=','not_paid')])
        sum_bill_paid = sum(bill_paid.mapped('amount_total'))
        sum_bill_unpaid = sum(bill_unpaid.mapped('amount_total'))
        
        realiziable_expense = []
        realiziable_expense_total = 0
        start_date = datetime.strftime(from_date, '%m/%d/%Y')
        start_date = datetime.strptime(start_date, '%m/%d/%Y').date()
        end_date = datetime.strftime(to_date, '%m/%d/%Y')
        end_date = datetime.strptime(end_date, '%m/%d/%Y').date()
        expense = self.env['agreement.expense.plan'].search([('id','in',expense_ids), ('state','not in',['cancelled'])])
        if not expense:
            raise UserError(_('No Expense Plan Selected'))
        for exp in expense:
            if exp.expense_type == 'recurring':
                recurring = self.env['agreement.recurring.expenses'].search([('id','=',exp.recurring_type_id.id)])
                if recurring.recurring_type == 'day':
                    if exp.next_date == False:
                        start = exp.start_date
                    else:
                        start = exp.next_date
                    if start >= start_date:
                        next_date = start
                    else:
                        next = next_date
                        while next <= end_date:
                            next = next_date + relativedelta(days=+recurring.day)
                            if next >= start_date:
                                next_date = next
                                break
                    while next_date <= end_date:
                        if next_date >= exp.end_date:
                            break
                        vals = {
                            'property': exp.agreement_id.property_id.name,
                            'contract': exp.agreement_id.name,
                            'expense_date': next_date,
                            'expense_amount': exp.amount_total,
                        }
                        realiziable_expense.append(vals)
                        realiziable_expense_total += exp.amount_total
                        next_date = next_date + relativedelta(days=+recurring.day)
                
                if recurring.recurring_type == 'week':
                    if exp.next_date == False:
                        start = exp.start_date
                    else:
                        start = exp.next_date
                    if start >= start_date:
                        next_date = start
                    else:
                        next = next_date
                        while next <= end_date:
                            next = next_date + relativedelta(days=+recurring.week*7)
                            if next >= start_date:
                                next_date = next
                                break
                    while next_date <= end_date:
                        if next_date >= exp.end_date:
                            break
                        vals = {
                            'property': exp.agreement_id.property_id.name,
                            'contract': exp.agreement_id.name,
                            'expense_date': next_date,
                            'expense_amount': exp.amount_total,
                        }
                        realiziable_expense.append(vals)
                        realiziable_expense_total += exp.amount_total
                        next_date = next_date + relativedelta(days=+recurring.week*7)
                        
                if recurring.recurring_type == 'month':
                    if exp.next_date == False:
                        start = exp.start_date
                    else:
                        start = exp.next_date
                    if start >= start_date:
                        next_date = start
                    else:
                        next = next_date
                        while next <= end_date:
                            next = next_date + relativedelta(months=+recurring.month)
                            if next >= start_date:
                                next_date = next
                                break
                    while next_date <= end_date:
                        if next_date >= exp.end_date:
                            break
                        vals = {
                            'property': exp.agreement_id.property_id.name,
                            'contract': exp.agreement_id.name,
                            'expense_date': next_date,
                            'expense_amount': exp.amount_total,
                        }
                        realiziable_expense.append(vals)
                        realiziable_expense_total += exp.amount_total
                        next_date = next_date + relativedelta(months=+recurring.month)
                        
                if recurring.recurring_type == 'year':
                    if exp.next_date == False:
                        start = exp.start_date
                    else:
                        start = exp.next_date
                    if start >= start_date:
                        next_date = start
                    else:
                        next = next_date
                        while next <= end_date:
                            next = next_date + relativedelta(years=+recurring.year)
                            if next >= start_date:
                                next_date = next
                                break
                    while next_date <= end_date:
                        if next_date >= exp.end_date:
                            break
                        vals = {
                            'property': exp.agreement_id.property_id.name,
                            'contract': exp.agreement_id.name,
                            'expense_date': next_date,
                            'expense_amount': exp.amount_total,
                        }
                        realiziable_expense.append(vals)
                        realiziable_expense_total += exp.amount_total
                        next_date = next_date + relativedelta(years=+recurring.year)
                            
        return {
            'doc_ids': data['ids'],
            'doc_model': data['model'],
            'report_date':fields.Date.today(),
            'from_date':from_date,
            'to_date':to_date,
            'mwo_done': mwo_done,
            'mro_done': mro_done,
            'mwo_progress': mwo_progress,
            'mro_progress': mro_progress,
            'sum_mwo_done': sum_mwo_done,
            'sum_mro_done': sum_mro_done,
            'sum_mwo_progress': sum_mwo_progress,
            'sum_mro_progress': sum_mro_progress,
            'bill_paid': bill_paid,
            'bill_unpaid': bill_unpaid,
            'sum_bill_paid': sum_bill_paid,
            'sum_bill_unpaid': sum_bill_unpaid,
            'realiziable_expense': realiziable_expense,
            'realiziable_expense_total': realiziable_expense_total,
            'user_ids': user_ids,
        }