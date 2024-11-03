import base64
from odoo.tools import human_size
from odoo import api, fields, models, _
from datetime import datetime, date , timedelta
from odoo.exceptions import ValidationError
from lxml import etree
import json


class ProgressHistoryWiz(models.Model):
    _inherit = "progress.history.wiz"

    def create_task_bill(self):
        for record in self:
            total_time_usage = sum(record.labour_usage_ids.mapped('time_usage'))
            if total_time_usage > 0:
                # create journal entry on account.move
                account_journal_entry = self.env['account.move'].create({
                    'analytic_group_ids': record.project_id.analytic_idz.ids,
                    'ref': 'Bill - ' + self.name,
                    'date': datetime.now(),
                    'move_type': 'in_invoice',
                    'project_task_id': record.work_order
                })
                journal_items = []
                credit_amount = 0
                credit_currency_id = False
                for labour in record.labour_usage_ids:
                    # Debit
                    if labour.time_usage > 0:
                        amount = labour.time_usage * labour.contractors * labour.unit_price
                        if len(labour.project_task_id.project_id.cip_account_id) > 0:
                            account_id = labour.project_task_id.project_id.cip_account_id.id
                        else:
                            if labour.product_id.categ_id.stock_type == "service":
                                account_id = labour.product_id.categ_id.property_service_account_id.id
                            else:
                                account_id = labour.product_id.categ_id.property_account_expense_categ_id.id

                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'name': 'Labour Bill - ' + self.name,
                            'account_id': account_id,
                            'analytic_tag_ids': labour.analytic_group_ids.ids,
                            'amount_currency': amount,
                            'currency_id': labour.cs_labour_id.currency_id.id,
                            'debit': amount,
                            'credit': 0.0,
                            'labour_usage_line_id': labour.labour_usage_line_id.id,
                            'exclude_from_invoice_tab': False,
                            'product_id': labour.product_id.id,
                            'quantity': labour.time_usage * labour.contractors,
                            'product_uom_id': labour.uom_id.id,
                        }))
                        credit_amount += amount
                        credit_currency_id = labour.cs_labour_id.currency_id.id

                # credit
                if credit_amount > 0:
                    credit_account = record.company_id.partner_id.property_account_payable_id.id
                    journal_items.append((0, 0, {
                        'move_id': account_journal_entry.id,
                        'name': 'Labour Bill - ' + self.name,
                        'account_id': credit_account,
                        'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
                        'amount_currency': credit_amount,
                        'currency_id': credit_currency_id,
                        'debit': 0,
                        'credit': credit_amount,
                        'exclude_from_invoice_tab': True,
                    }))

                account_journal_entry.line_ids = journal_items
                self.account_move_id = account_journal_entry

    def add_progress(self):
        res = super(ProgressHistoryWiz, self).add_progress()
        for record in self:
            if record.custom_project_progress == "manual_estimation" and not record.is_progress_history_approval_matrix:
                record.create_task_bill()
        return res


class ProgressHistory(models.Model):
    _inherit = "progress.history"

    def create_task_bill(self):
        for record in self:
            total_time_usage = sum(record.labour_usage_ids.mapped('time_usage'))
            if total_time_usage > 0:
                # create journal entry on account.move
                account_journal_entry = self.env['account.move'].create({
                    'analytic_group_ids': record.project_id.analytic_idz.ids,
                    'ref': 'Bill - ' + self.name,
                    'date': datetime.now(),
                    'move_type': 'in_invoice',
                    'project_task_id': record.work_order
                })
                journal_items = []
                credit_amount = 0
                credit_currency_id = False
                for labour in record.labour_usage_ids:
                    if labour.time_usage > 0:
                    # Debit
                        amount = labour.time_usage * labour.contractors * labour.unit_price
                        if len(labour.project_task_id.project_id.cip_account_id) > 0:
                            account_id = labour.project_task_id.project_id.cip_account_id.id
                        else:
                            if labour.product_id.categ_id.stock_type == "service":
                                account_id = labour.product_id.categ_id.property_service_account_id.id
                            else:
                                account_id = labour.product_id.categ_id.property_account_expense_categ_id.id
                        journal_items.append((0, 0, {
                            'move_id': account_journal_entry.id,
                            'name': 'Labour Bill - ' + self.name,
                            'account_id': account_id,
                            'analytic_tag_ids': labour.analytic_group_ids.ids,
                            'amount_currency': amount,
                            'currency_id': labour.cs_labour_id.currency_id.id,
                            'debit': amount,
                            'credit': 0.0,
                            'labour_usage_line_id': labour.labour_usage_line_id.id,
                            'exclude_from_invoice_tab': False,
                            'product_id': labour.product_id.id,
                            'quantity': labour.time_usage * labour.contractors,
                            'product_uom_id': labour.uom_id.id,
                            'price_subtotal': amount,
                            'price_total': amount,
                        }))
                        credit_amount += amount
                        credit_currency_id = labour.cs_labour_id.currency_id.id

                # credit
                if credit_amount > 0:
                    credit_account = record.company_id.partner_id.property_account_payable_id.id
                    journal_items.append((0, 0, {
                        'move_id': account_journal_entry.id,
                        'name': 'Labour Bill - ' + self.name,
                        'account_id': credit_account,
                        'analytic_tag_ids': account_journal_entry.analytic_group_ids.ids,
                        'amount_currency': credit_amount,
                        'currency_id': credit_currency_id,
                        'debit': 0,
                        'credit': credit_amount,
                        'exclude_from_invoice_tab': True,
                    }))

                account_journal_entry.line_ids = journal_items
                account_journal_entry._compute_amount()
                self.progress_wiz.account_move_id = account_journal_entry

    def action_confirm_approving_matrix(self):
        res = super(ProgressHistory, self).action_confirm_approving_matrix()

        for record in self:
            if record.state == 'approved' and record.custom_project_progress == "manual_estimation":
                record.create_task_bill()
        return res

