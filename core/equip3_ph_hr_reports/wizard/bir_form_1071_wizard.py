from odoo import _, api, fields, models
from odoo.exceptions import UserError


class BirForm1901Wizard(models.TransientModel):
    _name = "bir.form.1701.wizard"
    _description = "BIR Form 1701 Wizard"

    employee_ids = fields.Many2many(comodel_name="hr.employee", string="Employee")

    def action_print_report(self):
        report_id = self.env.ref('equip3_ph_hr_reports.bir_form_1701_report')
        data = {}
        employee_informations = []

        if not self.employee_ids:
            raise UserError(_("Please add at least one employee to generate report."))

        for employee in self.employee_ids:
            contact = employee.mobile_phone
            tin = employee.tin

            if not tin:
                raise UserError(_("Tax Identification Number (TIN) for employee %s must be filled." % (employee.name)))

            if not employee.address_home_id:
                raise UserError(_("Home address for employee %s must be filled." % (employee.name)))

            if not employee.address_home_id.zip:
                raise UserError(_("Zip code for employee %s must be filled." % (employee.name)))
            
            if not employee.birthday:
                raise UserError(_("Date of Birth for employee %s must be filled." % (employee.name)))
            
            if not employee.work_email:
                raise UserError(_("Email for employee %s must be filled." % (employee.name)))

            if not employee.country_id:
                raise UserError(_("Citizenship (Country) for employee %s must be filled." % (employee.name)))

            if not contact:
                raise UserError(_("Contact (Mobile Phone) for employee %s must be filled." % (employee.name)))
            
            if not employee.marital:
                raise UserError(_("Civil Status (Marital Status) for employee %s must be filled." % (employee.name)))
            
            if "+63" in contact:
                contact = contact.replace(contact[:3], "0")
            elif "63" in contact:
                contact = contact.replace(contact[:2], "0")

            if "-" in tin:
                tin = tin.replace("-", "")

            employee_informations.append(
                {
                    'tax_payer_name': employee.name,
                    'tin': tin,
                    'zip_code': employee.address_home_id.zip,
                    'date_of_birth': employee.birthday,
                    'email': employee.work_email,
                    'citizenship': employee.country_id.name,
                    'contact': contact,
                    'civil_status': employee.marital
                }
            )
        data['name'] = ('BIR Form 1701')
        data['employee_ids'] = employee_informations
        print_report_name = ('BIR Form 1701')
        report_id.write({'name': print_report_name})

        return report_id.report_action(self, data=data)
