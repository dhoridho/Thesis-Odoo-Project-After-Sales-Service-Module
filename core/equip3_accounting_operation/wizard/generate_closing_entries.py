# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class GenerateOpeningEntriesConfirmationWizard(models.TransientModel):
    _name = 'generate.closing.entries.confirmation.wizard'
    _description = "Generate Opening Entries Confirmation Wizard"
    
    @api.model
    def default_get(self, fields):
        context = self._context
        res = super(GenerateOpeningEntriesConfirmationWizard, self).default_get(fields)
        res.update(context.get('data'))
        return res
    
    name = fields.Text(default="Closing year entry has been created. Do you really want to make new closing entry?")
    fiscal_year_id = fields.Many2one('sh.fiscal.year', string="Fiscal Year to close", required=True)
    closing_entry_date = fields.Date(string='Closing Entry Date', required=True)
    journal_id = fields.Many2one('account.journal', string="Journal", required=True, domain=[('type', '=', 'opening')])
    description = fields.Text(string='Description', required=True)  
    summary_account_id = fields.Many2one('account.account', string='Profit and Loss Summary Account', 
                                            required=True)
    retained_earnings_account_id = fields.Many2one('account.account', string='Retained Earnings Account', 
                                            required=True)
                                            
    def action_continue(self):
        values = {
            'fiscal_year_id' : self.fiscal_year_id.id,
            'closing_entry_date' : self.closing_entry_date,
            'journal_id' : self.journal_id.id,
            'description' : self.description,
            'summary_account_id' : self.summary_account_id.id,
            'retained_earnings_account_id' : self.retained_earnings_account_id.id,
        }
        generate_closing_wizard = self.env['generate.closing.entries'].create(values)
        
        return generate_closing_wizard.data_save()
                                            
                                            

class GenerateOpeningEntries(models.TransientModel):
    _name = 'generate.closing.entries'
    _description = "Generate Opening Entries"
 
    def _get_domain_for_summary_account_id(self):
        result = []
        try:
            account_type_id = self.env['ir.model.data'].xmlid_to_res_id("account.data_unaffected_earnings")
            result = [('user_type_id','=',account_type_id),('company_id','=',self.env.company.id)]
        except:
            result = [('company_id','=',self.env.company.id)]
        return result
    

    def _get_domain_for_retained_earnings_account_id(self):
        result = []
        try:
            account_type_id = self.env['ir.model.data'].xmlid_to_res_id("account.data_account_type_equity")
            result = [('user_type_id','=',account_type_id),('company_id','=',self.env.company.id)]
        except:
            result = [('company_id','=',self.env.company.id)]
        return result

    fiscal_year_id = fields.Many2one('sh.fiscal.year', string="Fiscal Year to close", required=True)
    closing_entry_date = fields.Date(string='Closing Entry Date', required=True)
    journal_id = fields.Many2one('account.journal', string="Journal", required=True, domain=[('type', '=', 'opening')])
    description = fields.Text(string='Description', required=True)  
    summary_account_id = fields.Many2one('account.account', string='Profit and Loss Summary Account', 
                                            required=True, domain=_get_domain_for_summary_account_id)
    retained_earnings_account_id = fields.Many2one('account.account', string='Retained Earnings Account', 
                                            required=True, domain=_get_domain_for_retained_earnings_account_id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company.id)
                                            
                                            
                                            
    def action_generate(self):
        ctx = self.env.context
        if self.fiscal_year_id.move_id or self.fiscal_year_id.summary_move_id:
            action = self.env["ir.actions.actions"]._for_xml_id("equip3_accounting_operation.generate_closing_entries_confirmation_action")
            data = {
                'fiscal_year_id' : self.fiscal_year_id.id,
                'closing_entry_date' : self.closing_entry_date,
                'journal_id' : self.journal_id.id,
                'description' : self.description,
                'summary_account_id' : self.summary_account_id.id,
                'retained_earnings_account_id' : self.retained_earnings_account_id.id,
                }
            action.update({
                'context' : {'data' : data}
                })
            return action
        else:
            data_save = self.data_save()
            return data_save

    def data_save(self):
        """
        This function create closing entries
        """
        obj_acc_move = self.env['account.move']
        obj_acc_move_line = self.env['account.move.line']
        total_debit = total_credit = debit_calculation = credit_calculation = 0.0

        fyear = self.fiscal_year_id
        closing_entry_date = self.closing_entry_date
        journal = self.journal_id
        company_id = self.journal_id.company_id.id
        period = self.env['sh.account.period'].search([('date_start','<=',closing_entry_date),('date_end','>=',closing_entry_date),('company_id','=',company_id)])
        summary_account = self.summary_account_id
        retain_earning_account = self.retained_earnings_account_id
        
        
        #delete existing move and move lines if any
        list_move_ids = []
        if fyear.move_id:
            list_move_ids.append(fyear.move_id.id)
        if fyear.summary_move_id:
            list_move_ids.append(fyear.summary_move_id.id)
        move_ids = obj_acc_move.browse(list_move_ids)

        if move_ids:
            for move in move_ids:
                if move.state not in ('posted','cancel'):
                    move_line_ids = obj_acc_move_line.search(
                        [('move_id', 'in', move.ids)])
                    move_line_ids.unlink()
                    move.unlink()
                elif move.state == 'posted':
                    move.button_draft()
                    move.button_cancel()


        #create the first closing move
        vals = {
            'name': '/',
            'ref': fyear.name + ' Profit and Loss Summary',
            'date': closing_entry_date,
            'journal_id': journal.id,
        }
        move_id = obj_acc_move.create(vals)


        account_types = []
        #Find the account type id of Income and Expense
        try:
            account_types = [
            self.env['ir.model.data'].xmlid_to_res_id("account.data_account_type_revenue"),
            self.env['ir.model.data'].xmlid_to_res_id("account.data_account_type_other_income"),
            self.env['ir.model.data'].xmlid_to_res_id("account.data_account_type_expenses"),
            self.env['ir.model.data'].xmlid_to_res_id("account.data_account_type_direct_costs"),
            self.env['ir.model.data'].xmlid_to_res_id("account.data_account_type_depreciation")]
        except:
            account_types = []

        # Add centralized line to reconcile it
        query_part = """
                INSERT INTO account_move_line (
                     debit, credit, name, date, move_id, journal_id, period_id,
                     account_id, currency_id, company_currency_id, amount_currency, company_id,display_type) VALUES
                     (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,%s)
        """
        
        # The first line of the first move
        
        query_1st_Line_args = (total_debit,
                                  total_credit,
                                  'Profit and Loss Summary ' + fyear.name,
                                  closing_entry_date,
                                  move_id.id,
                                  journal.id,
                                  period.id,
                                  summary_account.id,
                                  move_id.currency_id and move_id.currency_id.id or None,
                                  move_id.currency_id and move_id.currency_id.id or None,
                                  total_credit,
                                  company_id,
                                  None)
        self._cr.execute(query_part, tuple(query_1st_Line_args))
        
        first_move_line = [x.id for x in obj_acc_move_line.sudo().search([('move_id', '=', move_id.id)])]

     
        #1. report of the income and expense accounts
        self._cr.execute('''
            SELECT a.id
            FROM account_account a
            LEFT JOIN account_account_type t ON (a.user_type_id = t.id)
            WHERE a.company_id = %s
              AND a.user_type_id IN %s''', (company_id, tuple(account_types), ))
        account_ids = [res[0] for res in self._cr.fetchall()]

        if account_ids:
            try:
                self._cr.execute('''
                    INSERT INTO account_move_line (
                         name, create_uid, create_date, write_uid, write_date,
                          journal_id, currency_id, company_currency_id, date_maturity,
                         partner_id, blocked,credit,  debit,
                         ref, account_id, period_id, date, move_id, amount_currency,
                         quantity, product_id, company_id)
                      (SELECT l.name, l.create_uid, l.create_date, l.write_uid, l.write_date,
                         %s, l.currency_id, l.company_currency_id, l.date_maturity, l.partner_id, l.blocked,
                         l.debit, l.credit, l.ref, l.account_id,
                         %s, (%s) AS date, %s, -l.amount_currency, l.quantity, l.product_id, l.company_id
                       FROM account_move_line AS l
                       LEFT JOIN account_move AS m ON l.move_id=m.id
                       LEFT JOIN account_journal AS j ON m.journal_id=j.id
                       WHERE account_id IN %s AND l.date BETWEEN %s AND %s AND m.state='posted' AND j.type<>'opening'
                        )''', (journal.id, period.id, closing_entry_date, move_id.id, tuple(account_ids), fyear.date_start, fyear.date_end, ))
            except:
                import traceback
                traceback.print_exc()
                return



        # find all lines with this move
        move_lines = obj_acc_move_line.sudo().search(
            [('move_id', '=', move_id.id)])
        for line in move_lines:
            if line.account_id.id not in (summary_account.id,retain_earning_account.id):
                total_credit += line.credit
                total_debit += line.debit
            line._compute_balance()

        if total_debit - total_credit  < 0.0:
            debit_calculation = total_credit - total_debit
            credit_calculation = 0
        else:
            debit_calculation = 0
            credit_calculation = total_debit - total_credit


        self._cr.execute("""UPDATE account_move_line SET debit=%s, credit=%s,  amount_currency=%s
                            WHERE id=%s""", (debit_calculation, credit_calculation, debit_calculation-credit_calculation, first_move_line[0]))

        
        #create the second closing move
        vals = {
            'name': '/',
            'ref': fyear.name + ' Move to Retained Earning',
            'date': closing_entry_date,
            'journal_id': journal.id,
        }
        move_id2 = obj_acc_move.create(vals)

        vals2 = {
            'debit' : credit_calculation, 
            'credit' : debit_calculation, 
            'name' : 'Profit and Loss Summary ' + fyear.name, 
            'date' : closing_entry_date, 
            'move_id' : move_id2.id, 
            'journal_id' : journal.id, 
            'period_id' : period.id,
            'account_id' : summary_account.id,
            'currency_id' : move_id2.currency_id and move_id2.currency_id.id or None,
            'company_currency_id' : move_id2.currency_id and move_id2.currency_id.id or None, 
            'amount_currency' : credit_calculation-debit_calculation,
            'company_id' : summary_account.company_id.id,
        }
        
        vals3 = {
            'debit' : debit_calculation, 
            'credit' : credit_calculation, 
            'name' : 'Retained Earning ' + fyear.name,
            'date' : closing_entry_date, 
            'move_id' : move_id2.id, 
            'journal_id' : journal.id, 
            'period_id' : period.id,
            'account_id' : retain_earning_account.id,
            'currency_id' : move_id2.currency_id and move_id2.currency_id.id or None,
            'company_currency_id' : move_id2.currency_id and move_id2.currency_id.id or None, 
            'amount_currency' : debit_calculation-credit_calculation,
            'company_id' : retain_earning_account.company_id.id,
        }
        
        # move_id2.write({'line_ids' : [(0,0, vals2),(0,0, vals3)]})
        move_line2 = obj_acc_move_line.sudo().with_context(check_move_validity=False).create(vals2)
        move_line3 = obj_acc_move_line.sudo().with_context(check_move_validity=False).create(vals3)
  
        last_move_lines = obj_acc_move_line.sudo().search(
            [('move_id', '=', move_id.id)], limit=1, order='id asc')
        for line in last_move_lines:
            line._compute_balance()
            
        
        last_move_lines2 = obj_acc_move_line.sudo().search(
            [('move_id', '=', move_id2.id)], order='id asc')
        for line in last_move_lines2:
            line._compute_balance()
        self.env.cr.commit()
        # move_id._compute_amount()
        move_id.sudo().action_post()
        move_id2.sudo().action_post()
        
        fyear.write({
                'move_id' : move_id2.id,
                'summary_move_id' : move_id.id
            })
        
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_move_journal_line")
        action.update({'domain' : [('id','in',[move_id.id,move_id2.id])]})
        return action
