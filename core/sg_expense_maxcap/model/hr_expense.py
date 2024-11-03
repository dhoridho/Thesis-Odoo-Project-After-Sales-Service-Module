from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError


class HrExpense(models.Model):
    _inherit = "hr.expense"

    contract_id = fields.Many2one('hr.contract', 'Contract')

    @api.onchange('employee_id', 'date')
    def _check_expense_contract(self):
        contract_obj = self.env['hr.contract']
        for exp in self:
            if exp.employee_id and exp.employee_id.id and exp.date:
                contract_id = contract_obj.search([
                    ('employee_id', '=', exp.employee_id.id),
                    ('date_start', '<=', exp.date), '|',
                    ('date_end', '>=', exp.date),
                    ('date_end', '=', False)], limit=1)
                exp.contract_id = contract_id and contract_id.id or False

    @api.constrains('state', 'product_id', 'unit_amount', 'total_amount',
                    'employee_id', 'date', 'contract_id')
    def _check_expense_line_prod(self):
        for expense in self:
            contract = expense.contract_id or False
            if contract and (contract.date_end and
                    expense.date >= contract.date_start and
                    expense.date <= contract.date_end):
                for con_line in contract.hr_cont_prod_ids:
                    if (con_line.product_id and
                        con_line.product_id.id == expense.product_id.id and
                        (con_line.start_date <= expense.date and
                         con_line.end_date >= expense.date)):
                        if con_line.pro_rate:
                            cont_st_date = con_line.start_date
                            cont_ed_date = con_line.end_date
                            expense_date = expense.date

                            remain_mnt = 1
                            remain_month = relativedelta(expense_date,
                                                         cont_st_date)
                            if remain_month:
                                if remain_month.years:
                                    remain_mnt += (remain_month.years) * 12
                                if remain_month.months:
                                    remain_mnt += remain_month.months

                            cont_months = relativedelta(cont_ed_date,
                                                        cont_st_date)
                            contract_mnt = 1
                            if cont_months:
                                if cont_months.years:
                                    contract_mnt += \
                                        (cont_months.years) * 12
                                if cont_months.months:
                                    contract_mnt += cont_months.months

                            max_prod_cap = round((
                                con_line.max_prod_cap / contract_mnt
                            ) * remain_mnt)
                            total_amt = (con_line.max_exp_cap_draft +
                                         con_line.max_exp_cap)
                            if (max_prod_cap < total_amt and
                                    con_line.override is False):
                                raise ValidationError(_(
                                    'You can not apply expense more than pro'
                                    ' ration amount of %s ' % (max_prod_cap)))
                        else:
                            total_amnt = (con_line.max_exp_cap_draft +
                                          con_line.max_exp_cap)
                            if (con_line.max_prod_cap < total_amnt and
                                    con_line.override is False):
                                raise ValidationError(_(
                                    'You can not create expense over your'
                                    ' expense limit.\nYour expense limit'
                                    ' for product "%s" is : %s .\nAnd'
                                    ' you have already approved expenses'
                                    ' for same product is : %s.\n'
                                    % (
                                        con_line.product_id.name,
                                        con_line.max_prod_cap,
                                        con_line.max_exp_cap)))
