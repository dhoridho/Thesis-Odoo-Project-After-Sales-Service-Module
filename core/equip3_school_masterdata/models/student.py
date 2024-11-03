from odoo import _, api, fields, models
from datetime import date, datetime
from odoo.exceptions import UserError, ValidationError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, \
    DEFAULT_SERVER_DATETIME_FORMAT
import time



class StudentsStudents(models.Model):
    _inherit = 'student.student'
    
    school_id = fields.Many2one(string="School")

    def admission_done(self):
        request = super(StudentsStudents, self).admission_done()
        school_standard_obj = self.env['school.standard']
        ir_sequence = self.env['ir.sequence']
        student_group = self.env.ref('school.group_school_student')
        emp_group = self.env.ref('base.group_user')
        for rec in self:
            if rec.student_type == 'new_student':
                if not rec.standard_id:
                    raise ValidationError(_("Please select class!"))
                if rec.standard_id.remaining_seats <= 0:
                    raise ValidationError(_('Seats of class %s are full'
                                            ) % rec.standard_id.standard_id.name)
                domain = [('school_id', '=', rec.school_id.id)]
                # Checks the standard if not defined raise error
                if not school_standard_obj.search(domain):
                    raise UserError(_(
                        "Warning! The standard is not defined in school!"))
                # Assign group to student
                number = 1
                for rec_std in rec.search(domain):
                    rec_std.roll_no = number
                    number += 1
                # Assign registration code to student
                reg_code = ir_sequence.next_by_code('student.registration')
                registation_code = (str('REG') + str('/') +
                                    str(time.strftime('%Y')[2:]) + str('/') +
                                    str(time.strftime('%m')) + str('/') +
                                    str(time.strftime('%d')) + str('/') +
                                    str(reg_code))
                stu_code = ir_sequence.next_by_code('student.code')
                student_code = (str(rec.school_id.code) + str('/') +
                                str(rec.year.code) + str('/') +
                                str(stu_code))
                rec.write({
                        'admission_date': time.strftime('%Y-%m-%d'),
                        'student_code': student_code,
                        'reg_code': registation_code})
        return request



