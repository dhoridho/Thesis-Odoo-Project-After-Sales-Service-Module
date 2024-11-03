from odoo import _, api, models, fields
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DSDF
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _inherit = "hr.contract"

    hr_cont_prod_ids = fields.One2many('hr.cont.prod', 'contract_id',
                                       'contract Products',
                                       help="Configure Product and it's \
                                       Maximum limits for Expenses")
    hr_expense_ids = fields.One2many('hr.expense', 'contract_id', 'Expense')

    @api.constrains('date_end', 'date_start')
    def _check_contr_start_end_date(self):
        """
        This constraint Method is used to restrict system
        that does not take start date and end date of expense
        product out of contract date limit.
        """
        for exp in self:
            if exp.hr_cont_prod_ids and exp.date_start and exp.date_end:
                for exp_prod in exp.hr_cont_prod_ids:
                    if exp_prod.start_date < exp.date_start and \
                            exp.date_end < exp_prod.end_date:
                        raise ValidationError(_(
                            'Contract Date Error !\n'
                            'Expense Product start date and end date must'
                            ' be in between contract start and end date !'))
                    elif exp_prod.start_date < exp.date_start and \
                            exp_prod.end_date < exp.date_end:
                        raise ValidationError(_(
                            'Contract Date Error !\n'
                            'Expense Product start date and end date must'
                            ' be in between contract start and end date !'))
                    elif exp.date_start < exp_prod.start_date and \
                            exp.date_end < exp_prod.end_date:
                        raise ValidationError(_(
                            'Contract Date Error !\n'
                            'Expense Product start date and end date must'
                            ' be in between contract start and end date !'))


class HrContractProd(models.Model):
    _name = "hr.cont.prod"
    _description = "Hr Contract Product"

    @api.depends('start_date', 'end_date', 'product_id',
                 'contract_id.employee_id', 'contract_id.hr_expense_ids',
                 'contract_id.hr_expense_ids.total_amount')
    def _get_max_exp_cap(self):
        """
        This Function is used to get all accepted expense amount
        for a current employee contract.
        """
        for contract in self:
            contract.max_exp_cap = total_exp = 0.0
            emp_id = contract.contract_id.employee_id.id
            today = datetime.now()
            contract_start_date = contract.start_date or today
            contract_end_date = contract.end_date or today
            start_date = datetime.strftime(contract_start_date, DSDF)
            end_date = datetime.strftime(contract_end_date, DSDF)
            expense_ids = self.env['hr.expense'].search([
                ('product_id', '=', contract.product_id.id),
                ('employee_id', '=', emp_id),
                ('state', '=', 'done'),
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('contract_id', '!=', False)])
            for exp in expense_ids:
                total_exp += exp.total_amount
            contract.max_exp_cap = total_exp

    @api.depends('start_date', 'end_date', 'product_id',
                 'contract_id.employee_id', 'contract_id.hr_expense_ids',
                 'contract_id.hr_expense_ids.total_amount')
    def _get_max_exp_cap_draft(self):
        """
        This Function is used to get all Draft expense amount
        for a current employee contract.
        """
        for contract in self:
            contract.max_exp_cap_draft = total = 0.0
            emp_id = contract.contract_id.employee_id.id
            today = datetime.now()
            contract_start_date = contract.start_date or today
            contract_end_date = contract.end_date or today
            start_date = datetime.strftime(contract_start_date, DSDF)
            end_date = datetime.strftime(contract_end_date, DSDF)
            expense_ids = self.env['hr.expense'].search([
                ('product_id', '=', contract.product_id.id),
                ('employee_id', '=', emp_id),
                ('state', 'in', ['draft', 'reported']),
                ('date', '>=', start_date),
                ('date', '<=', end_date),
                ('contract_id', '!=', False)])
            for exp in expense_ids:
                total += exp.total_amount
            contract.max_exp_cap_draft = total

    contract_id = fields.Many2one('hr.contract', 'Contract')
    product_id = fields.Many2one('product.product', 'Product',
                                 help="Expense products.",
                                 domain=[('can_be_expensed', '=', True)])
    max_prod_cap = fields.Float('Maximum Amount',
                                help="Maximum Amount for Expense products.")
    max_exp_cap = fields.Float(compute='_get_max_exp_cap',
                               string='Approved Expense',
                               help="Approved Expense amount.")
    max_exp_cap_draft = fields.Float(compute='_get_max_exp_cap_draft',
                                     string='Draft Expense',
                                     help="Draft Expense amount.")
    start_date = fields.Date('Start Date', required=True,
                             default=fields.Date.context_today)
    end_date = fields.Date('End Date', required=True,
                           default=fields.Date.context_today)
    override = fields.Boolean('Override',
                              help="If selected, Expense will override \
                              this Rule.")
    pro_rate = fields.Boolean("Pro-rate",
                              help="If selected, Pro ration Rule will be \
                              applied on expense.")

    @api.constrains('product_id', 'end_date', 'start_date')
    def _check_contr_prod_start_end(self):
        """
           This constraint Method is used to restrict system
           than does not take multiple products configuration on
           same date duration.
        """
        for exp_prod in self:
            prod_ids_in_count = self.search_count([
                ('contract_id', '=', exp_prod.contract_id.id),
                ('start_date', '<=', exp_prod.end_date),
                ('end_date', '>=', exp_prod.start_date),
                ('id', '!=', exp_prod.id),
                ('product_id', '=', exp_prod.product_id.id)])
            if prod_ids_in_count > 0:
                raise ValidationError(_(
                'Expense Product Error !\nYou can not create multiple '
                'configuration for same product on date duration!'))

    @api.constrains('end_date', 'start_date')
    def _check_contr_prod_start_end_date(self):
        """
           This constraint Method is used to restrict system
           that does not take start date and end date of expense
           product out of contract date limit.
        """
        for exp_prod in self:
            if (exp_prod.contract_id.date_start and
                    exp_prod.contract_id.date_end):
                if exp_prod.start_date < exp_prod.contract_id.date_start and \
                        exp_prod.contract_id.date_end < exp_prod.end_date:
                    raise ValidationError(_(
                        'Expense Product Date Error !\n'
                        'Expense Product start date and end date must be in'
                        ' between contract start and end date !'))
                elif exp_prod.start_date < exp_prod.contract_id.date_start and\
                        exp_prod.end_date < exp_prod.contract_id.date_end:
                    raise ValidationError(_(
                        'Expense Product Date Error !\n'
                        'Expense Product start date and end date must be in'
                        ' between contract start and end date !'))
                elif exp_prod.contract_id.date_start < exp_prod.start_date and\
                        exp_prod.contract_id.date_end < exp_prod.end_date:
                    raise ValidationError(_(
                        'Expense Product Date Error !\n'
                        'Expense Product start date and end date must be in'
                        ' between contract start and end date !'))

    @api.constrains('start_date', 'end_date')
    def _check_start_end_date(self):
        """
           This constraint Method is used to restrict system
           that does not take start date greater than end date.
        """
        for exp_prod in self:
            if ((exp_prod.start_date and exp_prod.end_date) and
                    (exp_prod.start_date > exp_prod.end_date)):
                raise ValidationError(_('Warning! \nThe start date must be'
                                        ' anterior to the end date.'))

    @api.constrains('max_prod_cap')
    def _check_max_prod_cap(self):
        """
       This constraint Method is used to restrict system
       that does not take approved and draft expense amounts
       greater than Maximum amount.
        """
        for exp_prod in self:
            if exp_prod.max_prod_cap < (exp_prod.max_exp_cap +
                                        exp_prod.max_exp_cap_draft):
                raise ValidationError(_(
                    'Warning! \nMaximum amount must be greater than '
                    'approved and draft expense amounts.'))

    @api.onchange('start_date', 'end_date')
    def onchange_date_start_end(self):
        if self.start_date and self.end_date and\
                self.start_date > self.end_date:
            raise ValidationError(_(
                'The start date must be anterior to the end date.'))
