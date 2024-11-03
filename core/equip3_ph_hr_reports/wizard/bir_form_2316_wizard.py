from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime
from datetime import timedelta
from dateutil.relativedelta import relativedelta


class BirForm2316Wizard(models.TransientModel):
    _name = "bir.form.2316.wizard"
    _description = "BIR Form 2316 Wizard"

    employee_ids = fields.Many2many(comodel_name="hr.employee", string="Employee")
    start_period = fields.Date(
        string="Start Period",
        required=True,
        default=lambda self: fields.Date.to_string(datetime.now().replace(month=1, day=1)),
    )
    end_period = fields.Date(
        string="End Period",
        required=True,
        default=lambda self: fields.Date.to_string(
            datetime.now().replace(month=12, day=1) + relativedelta(day=31)
        ),
    )
    payslip_period_id = fields.Many2one('hr.payslip.period', string='Payslip Period', domain="[('state','=','open')]")
    month = fields.Many2one('hr.payslip.period.line', string="Month", domain="[('period_id','=',payslip_period_id)]")
    month_name = fields.Char('Month Name', readonly=True)
    year = fields.Char('Year', readonly=True)
    
    @api.onchange('month')
    def _onchange_month(self):
        for res in self:
            if res.payslip_period_id:
                if res.month:
                    period_line_obj = self.env['hr.payslip.period.line'].search(
                        [('id', '=', res.month.id)], limit=1)
                    if period_line_obj:
                        for rec in period_line_obj:
                            res.start_period = rec.start_date
                            res.end_period = rec.end_date
                            res.month_name = res.month.month
                            res.year = res.month.year
                        
                    else:
                        res.start_period = False
                        res.end_period = False
                        res.month_name = False
                        res.year = False
    
    def _calculate_total(self, payslip, tax_category, compensation_type=None):
        """
        Helper function to calculate the total for a specific tax category and compensation type.
        """
        if tax_category == "non_taxable":
            lines = payslip.line_ids.filtered(
                lambda line: line.salary_rule_id.salary_rule_tax_category == tax_category
                and (compensation_type is None or line.salary_rule_id.nontaxable_compensation_income == compensation_type)
            ).mapped("total")
        else:
            lines = payslip.line_ids.filtered(
                lambda line: line.salary_rule_id.salary_rule_tax_category == tax_category
                and (compensation_type is None or line.salary_rule_id.taxable_compensation_income == compensation_type)
            ).mapped("total")
        
        if isinstance(lines, (int, float)):
            return lines
        return sum(lines) if lines else 0

    def get_non_taxable_compensation(self, payslip):
        if not payslip:
            return {}
        
        compensation_types = [
            "basic_salary", "holiday_pay", "overtime_pay", "night_shift_differential",
            "hazard_pay", "13th_month_pay_and_other_benefits", "de_minimis_benefits",
            "sss_gsis_phic_pagibig_contributions", "salaries_and_other_forms_of_compensation"
        ]
        
        totals = {
            f"total_non_taxable_{compensation_type}": self._calculate_total(
                payslip, "non_taxable", compensation_type
            )
            for compensation_type in compensation_types
        }
        totals["total_non_taxable"] = self._calculate_total(payslip, "non_taxable")
        
        return totals

    def get_taxable_compensation(self, payslip):
        if not payslip:
            return {}
        
        compensation_types = [
            "basic_salary", "representation", "transportation", "cola",
            "fixed_housing_allowance", "others_42a", "others_42b", 
            "commission", "profit_sharing", "fees_including_director_fees",
            "13th_month_benefits", "hazard_pay", "overtime_pay", "others_49a",
            "others_49b"
        ]
        
        totals = {
            f"total_taxable_{compensation_type}": self._calculate_total(
                payslip, "taxable", compensation_type
            ) for compensation_type in compensation_types
        }
        totals["total_taxable"] = self._calculate_total(payslip, "taxable")
        
        return totals


    def action_print_report(self):
        report_id = self.env.ref("equip3_ph_hr_reports.bir_form_2316_report")
        data = {}
        employee_informations = []
        paylip = self.env["hr.payslip"]

        if not self.employee_ids:
            raise ValidationError(_("Please add at least one employee to generate report."))

        for employee in self.employee_ids:
            company_id = employee.company_id
            contract_id = employee.contract_id
            address_home_id = employee.address_home_id
            tin = employee.tin

            # Get payslip data for selected employee and period
            employee_payslip = paylip.search(
                [
                    ("employee_id", "=", employee.id),
                    ("date_from", "<=", self.end_period),
                    ("date_to", ">=", self.start_period),
                    ("state", "=", "done"),
                    ("line_ids", "!=", False)
                ], limit=1
            )

            if not employee_payslip:
                raise ValidationError(_("There's no payslip for employee %s!" % (employee.name)))

            # Get non-taxable compensations
            nontaxable_compensation_income = self.get_non_taxable_compensation(employee_payslip)

            # Get taxable compensations
            taxable_compensation_income = self.get_taxable_compensation(employee_payslip)

            if not tin:
                raise UserError(
                    _(
                        "Tax Identification Number (TIN) for employee %s must be filled."
                        % (employee.name)
                    )
                )

            if not address_home_id:
                raise UserError(
                    _("Home address for employee %s must be filled." % (employee.name))
                )
            
            if not address_home_id.zip:
                raise UserError(
                    _("Zip for employee %s must be filled." % (employee.name))
                )
            
            if not address_home_id.city:
                raise UserError(
                    _("City for employee %s must be filled." % (employee.name))
                )

            if not employee.birthday:
                raise UserError(
                    _("Date of Birth for employee %s must be filled." % (employee.name))
                )

            if not employee.mobile_phone:
                raise UserError(
                    _(
                        "Contact (Mobile Phone) for employee %s must be filled."
                        % (employee.name)
                    )
                )
        
            if not contract_id:
                raise UserError(
                    _("There is no contract for employee %s" % (employee.name))
                )

            if not contract_id.wage:
                raise UserError(
                    _("Wage for employee %s must be filled." % (employee.name))
                )
            
            if not contract_id.over_day:
                raise UserError(
                    _("Day Wage for employee %s must be filled." % (employee.name))
                )

            if not company_id:
                raise UserError(
                    _("Company for employee %s must be filled." % (employee.name))
                )
            
            contact = employee.mobile_phone
            if "+63" in contact:
                contact = contact.replace(contact[:3], "0")
            elif "63" in contact:
                contact = contact.replace(contact[:2], "0")
            
            # Phone numner in Philippines contains 11 digit, add warning if it's invalid
            if len(contact) > 11:
                raise UserError(
                    _("Contact for employee %s seems to be invalid, it must contains 11 digit." % (employee.name))
                )
            
            if "-" in tin:
                tin = tin.replace("-", "")

            basic_informations = {
                "start_period": self.start_period,
                "end_period": self.end_period,
                "employee_name": employee.name,
                "tin": tin,
                "city": address_home_id.city,
                "zip_code": address_home_id.zip,
                "date_of_birth": employee.birthday,
                "contact": contact,
                "wage_per_day": employee.contract_id.over_day,
                "wage": employee.contract_id.wage,
                "currency_symbol": employee.contract_id.currency_id.symbol,
                "company_name": company_id.name,
                "company_city": company_id.city_id.name,
                "company_zip_code": company_id.zip,
                "taxable_compensation_income_from_previous_employer": 0
            }

            # merge dictonaries
            tax_information = {**basic_informations, **nontaxable_compensation_income, **taxable_compensation_income}
            employee_informations.append(tax_information)

        data["name"] = "BIR Form 2316"
        data["employee_ids"] = employee_informations
        print_report_name = "BIR Form 2316"
        report_id.write({"name": print_report_name})

        return report_id.report_action(self, data=data)
