from odoo import api, models, _
from odoo.exceptions import ValidationError


class HrContract(models.Model):

    _inherit = 'hr.contract'

    @api.constrains('date_end', 'date_start')
    def _check_date(self):
        res = super(HrContract, self)._check_dates()
        for contract in self:
            domain = [('date_start', '<=', contract.date_end),
                      ('date_end', '>=', contract.date_start),
                      ('employee_id', '=', contract.employee_id.id),
                      ('id', '!=', contract.id)]
            contract_ids = self.search(domain, count=True)
            if contract_ids:
                raise ValidationError(_(
                    'You can not have 2 contract that overlaps on same date!'))
        return res

    @api.constrains('hr_contract_income_tax_ids')
    def _check_incomtax_year(self):
        for contract in self:
            if contract.hr_contract_income_tax_ids:
                for incmtax in contract.hr_contract_income_tax_ids:
                    domain = [
                        ('start_date', '<=', incmtax.end_date),
                        ('end_date', '>=', incmtax.start_date),
                        ('contract_id', '=', contract.id)]
                    contract_count = self.env['hr.contract.income.tax'].search_count(domain)
                    if contract_count > 1:
                        raise ValidationError(_(
                            'You can not configure multiple income tax '
                            'that overlap on same date!'))


class HrContractIncomeTax(models.Model):

    _inherit = 'hr.contract.income.tax'

    @api.constrains('director_fee_approval_date')
    def _check_director_fee_approval_date(self):
        for rec in self:
            if rec.director_fee_approval_date and rec.end_date:
                dir_year = rec.director_fee_approval_date.year
                year_id = rec.end_date.year
                if dir_year >= year_id:
                    raise ValidationError(_(
                        "Wrong IR8A Configuration: (50).Date of approval of "
                        "directors fees is accepted up to previous income "
                        "years!"))
