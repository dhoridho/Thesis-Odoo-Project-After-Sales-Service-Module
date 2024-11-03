from odoo import models, fields, api, _
from odoo.exceptions import UserError


class Equip3HrSalaryRule(models.Model):
    _inherit = "hr.salary.rule"

    salary_rule_tax_category = fields.Selection(
        selection=[("taxable", "Taxable"), ("non_taxable", "Non-Taxable")],
        string="Tax Category",
        required=True
    )