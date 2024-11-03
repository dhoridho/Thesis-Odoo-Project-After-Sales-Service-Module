from odoo import _, api, fields, models
from datetime import datetime
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    spouse_name = fields.Char("Spouse Name")
    spouse_dob = fields.Date("Date of Birth")
    spouse_ident_no = fields.Char("Identification number")
    marriage_date = fields.Date("Date of Marriage")
    spouse_nationality = fields.Many2one('res.country', "Nationality")

    @api.constrains('spouse_dob')
    def _check_spouse_dob(self):
        for rec in self:
            today = datetime.today().date()
            if rec.spouse_dob:
                if rec.spouse_dob > today:
                    raise ValidationError(_(
                        "Please enter valid Date of Birth for spouse"))
            return True

    @api.constrains('marriage_date')
    def _check_marriage_date(self):
        for rec in self:
            today = datetime.today().date()
            if rec.marriage_date:
                if rec.marriage_date > today:
                    raise ValidationError(_(
                        "Please enter valid Date of Marriage for spouse"))
                if rec.spouse_dob and rec.marriage_date < rec.spouse_dob:
                    raise ValidationError(_(
                        "Please enter valid Date of Marriage for spouse."
                        " \nYou must enter Date of Marriage greater than "
                        "Date of Birth for spouse."))
        return True

    @api.onchange('marital', 'spouse_complete_name', 'spouse_birthdate')
    def onchange_spouse_complete_name(self):
        if self.marital in ['married', 'cohabitant']:
            if self.spouse_complete_name:
                self.spouse_name = self.spouse_complete_name
            if self.spouse_birthdate:
                self.spouse_dob = self.spouse_birthdate
        else:
            self.spouse_name = self.spouse_birthdate = ''
            self.spouse_complete_name = self.spouse_dob =  ''


class Dependents(models.Model):
    _inherit = "dependents"

    gender = fields.Selection([('male', 'Male'),
                               ('female', 'Female')],
                              "Gender")
