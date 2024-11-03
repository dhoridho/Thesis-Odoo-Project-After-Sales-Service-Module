from odoo import _, api, fields, models
from odoo.exceptions import ValidationError



class ResumeLine(models.Model):
    _inherit = 'hr.resume.line'

    position = fields.Char("Position")
    salary = fields.Float("Salary")
    companytelp_number = fields.Char("Company Telp Number")
    reason_for_leaving = fields.Text("Reason For Leaving")
    is_experience1 = fields.Boolean("Experience ?")

    @api.onchange('line_type_id')
    def _get_is_experience(self):
        for rl in self:
            is_experience1 = False
            if rl.line_type_id.name == 'Experience':
                is_experience1=True
            rl.is_experience1 = is_experience1


    @api.onchange('position')
    def _get_position(self):
        for rl in self:
            rl.description = rl.position



class Applicant(models.Model):
    _inherit = "hr.applicant"


    def create_employee_from_applicant(self):
        res = super(Applicant, self).create_employee_from_applicant()
        if self.is_blacklist:
            raise ValidationError("This applicant has been blacklisted. A blacklisted applicant cannot be converted into an employee. Remove the blacklist from this applicant before converting it to an employee")
        
        type_resume_obj = self.env['hr.resume.line.type']
        resume_line_ids = []
        exp_type = type_resume_obj.sudo().search([('name','=','Experience')],limit=1)
        for exp in self.past_experience_ids:
            resume_line_ids.append((0,0,{
                'name':exp.company_name,
                'line_type_id':exp_type.id,
                'position':exp.position,
                'description':exp.position,
                'salary':exp.salary,
                'companytelp_number':exp.company_telephone_number,
                'reason_for_leaving':exp.reason_for_leaving,
                'date_start':exp.start_date,
                'date_end':exp.end_date,
                'is_experience1':True,
            }))
        
        
        if res.get('context'):
            res['context']['default_resume_line_ids'] = resume_line_ids
            res['context']['default_identification_id'] = self.identification_no
            res['context']['default_mobile_phone'] = self.partner_mobile
            res['context']['default_work_phone'] = self.partner_phone
            res['context']['default_work_email'] = self.email_from
            res['context']['default_gender'] = self.gender
            res['context']['default_birthday'] = self.date_of_birth
            res['context']['default_religion_id'] = self.religion.id if self.religion else False
            res['context']['default_current_address'] = self.address
            res['context']['default_marital'] = self.marital_status.id if self.marital_status else False
        

        return  res