import base64

from odoo import _, api, fields, models
from odoo.modules import get_module_resource


class SchoolTeacher(models.Model):
    _inherit = 'school.teacher'
    _order = "create_date desc"

    @api.model
    def _default_image(self):
        '''Method to get default Image'''
        image_path = get_module_resource('equip3_school_operation', 'static/src/img',
                                         'teacher1.png')
        return base64.b64encode(open(image_path, 'rb').read())

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [('school_branch_ids', 'in', allowed_branch_ids)]

    employee_type = fields.Selection([('employee_wages_based_on_classes', 'Employee’s Wages based on Classes'), ('employee_wages_based_on_hours', 'Employee’s Wages based on Hours')], string='Employee Type')
    school_id = fields.Many2one('school.school', string="School", domain=_domainSchool, compute="_compute_school_id", store=True)
    id_teacher = fields.Char(string='ID Teacher')
    ems_classes_ids = fields.One2many('ems.classes', 'teacher_id', string="Class Schedule")
    partner_id = fields.Many2one('res.partner', string='Related Partner', ondelete='restrict',
                                 help="Partner-related data of the teacher")
    class_date_start = fields.Datetime(string='Date Start')
    class_date_end = fields.Datetime(string='End Date')
    program_id = fields.Many2one('standard.standard', string='Program')
    group_class_ids = fields.One2many('group.class', 'pic', string="Group Class")
    photo = fields.Binary('Photo', default=_default_image,
                          help='Attach student photo')
    teacher_group_class_ids = fields.One2many('teacher.group.class', 'teacher_id', string='Group Class')
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string='State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict')
    branch_id = fields.Many2one(comodel_name='res.branch', readonly=False)
    

    @api.depends('standard_id')
    def _compute_school_id(self):
        for teacher in self:
            teacher.school_id = False
            if teacher.standard_id:
                teacher.school_id = teacher.standard_id.school_id.id

    @api.onchange('gender')
    def _onchange_default_image(self):
        if self.gender == 'male':
            image_path = get_module_resource('equip3_school_operation', 'static/src/img', 'teacher1.png')
        elif self.gender == 'female':
            image_path = get_module_resource('equip3_school_operation', 'static/src/img', 'teacher2.png')
        else:
            image_path = get_module_resource('equip3_school_operation', 'static/src/img', 'teacher1.png')
        self.photo = base64.b64encode(open(image_path, 'rb').read())

    @api.model
    def create(self, values):
        res = super(SchoolTeacher, self).create(values)
        res.employee_id.user_id.write({'groups_id': [(4, self.env.ref('school.group_school_teacher').id)]})
        return res

    def action_print_class_schedule(self):
        context = dict(self.env.context) or {}
        context.update({'default_teacher_id': self.id})
        return {
            'type': 'ir.actions.act_window',
            'name': 'Class Schedule',
            'res_model': 'class.schedule',
            'view_mode': 'form',
            'view_id': self.env.ref('equip3_school_operation.view_form_class_schedule').id,
            'target': 'new',
            'context': context
        }

    @api.onchange('program_id')
    def _onchange_program_id(self):
        if self.program_id:
            self.school_id = self.program_id.school_id

    def write(self, vals):
        if 'name' in vals:
            self._cr.execute("""
                SELECT subject_id FROM subject_teacher_rel teacher
                WHERE teacher_id in %s
            """, [tuple(self.ids)])
            result = [r[0] for r in self._cr.fetchall()]
            for fee in self.env['subject.subject'].browse(result):
                message_body = "Name changed from %s to %s" % (self.name, vals.get('name') or self.name)
                fee.message_post(body=message_body)

        if 'phone_numbers' in vals:
            self._cr.execute("""
                SELECT subject_id FROM subject_teacher_rel teacher
                WHERE teacher_id in %s
            """, [tuple(self.ids)])
            result = [r[0] for r in self._cr.fetchall()]
            for fee in self.env['subject.subject'].browse(result):
                message_body = "Phone Number changed from %s to %s" % (
                    self.phone_numbers, vals.get('phone_numbers') or self.phone_numbers)
                fee.message_post(body=message_body)

        if 'work_email' in vals:
            self._cr.execute("""
                SELECT subject_id FROM subject_teacher_rel teacher
                WHERE teacher_id in %s
            """, [tuple(self.ids)])
            result = [r[0] for r in self._cr.fetchall()]
            for fee in self.env['subject.subject'].browse(result):
                message_body = "Work Email changed from %s to %s" % (
                    self.work_email, vals.get('work_email') or self.work_email)
                fee.message_post(body=message_body)

        if 'company_id' in vals:
            self._cr.execute("""
                SELECT subject_id FROM subject_teacher_rel teacher
                WHERE teacher_id in %s
            """, [tuple(self.ids)])
            result = [r[0] for r in self._cr.fetchall()]
            for data in self.env['res.company'].browse(vals.get('company_id')):
                message_body = "Company changed from %s to %s" % (self.company_id.name, data.name)
                for fee in self.env['subject.subject'].browse(result):
                    fee.message_post(body=message_body)

        if 'department_id' in vals:
            self._cr.execute("""
                SELECT subject_id FROM subject_teacher_rel teacher
                WHERE teacher_id in %s
            """, [tuple(self.ids)])
            result = [r[0] for r in self._cr.fetchall()]
            for data in self.env['hr.department'].browse(vals.get('department_id')):
                message_body = "Department changed from %s to %s" % (self.department_id.name, data.name)
                for fee in self.env['subject.subject'].browse(result):
                    fee.message_post(body=message_body)

        if 'parent_id' in vals:
            self._cr.execute("""
                SELECT subject_id FROM subject_teacher_rel teacher
                WHERE teacher_id in %s
            """, [tuple(self.ids)])
            result = [r[0] for r in self._cr.fetchall()]
            for data in self.env['hr.employee'].browse(vals.get('parent_id')):
                message_body = "Manager changed from %s to %s" % (self.parent_id.name, data.name)
                for fee in self.env['subject.subject'].browse(result):
                    fee.message_post(body=message_body)

        return super(SchoolTeacher, self).write(vals)


class TeacherGroupClass(models.Model):
    _name = 'teacher.group.class'

    teacher_id = fields.Many2one('school.teacher', string='Teacher')
    intake_id = fields.Many2one('school.standard', string='Intake')
    group_class_id = fields.Many2one('group.class', string='Group Class')
    subject_id = fields.Many2one('subject.subject', string='Subject')
