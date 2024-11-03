from odoo import api, fields, models, _


class Equip3PhHrReportsInheritHrSalarypRule(models.Model):
    _inherit = "hr.salary.rule"

    nontaxable_options = [
        ("basic_salary", "Basic Salary (Including the exempt P250000 & Below)"),
        ("holiday_pay", "Holiday Pay (MWE)"),
        ("overtime_pay", "Overtime Pay (MWE)"),
        ("night_shift_differential", "Night Shift Differential (MWE)"),
        ("hazard_pay", "Hazard Pay (MWE)"),
        ("13th_month_pay_and_other_benefits", "13th Month Pay and Other Benefits"),
        ("de_minimis_benefits", "De Minimis Benefits"),
        ("sss_gsis_phic_pagibig_contributions", "SSS, GSIS, PHIC, & PAG-IBIG Contributions"),
        ("salaries_and_other_forms_of_compensation", "Salaries and Other Forms of Compensation"),
    ]
    taxable_options = [
        ("basic_salary", "Basic Salary"),
        ("representation", "Representation"),
        ("transportation", "Transportation"),
        ("cola", "Cost of Living Allowance"),
        ("fixed_housing_allowance", "Fixed Housing Allowance"),
        ("others_42a", "Others (Specify) 42A"),
        ("others_42b", "Others (Specify) 42B"),
        ("commission", "Commission"),
        ("profit_sharing", "Profit Sharing"),
        ("fees_including_director_fees", "Fees Including Director's Fees"),
        ("13th_month_benefits", "Taxable 13th Month Benefits"),
        ("hazard_pay", "Hazard Pay"),
        ("overtime_pay", "Overtime Pay"),
        ("others_49a", "Others (Specify) 49A"),
        ("others_49b", "Others (Specify) 49B")
    ]

    nontaxable_compensation_income = fields.Selection(selection=nontaxable_options, string='Compensation Income (Non-Taxable)')
    taxable_compensation_income = fields.Selection(selection=taxable_options, string='Compensation Income (Taxable)')