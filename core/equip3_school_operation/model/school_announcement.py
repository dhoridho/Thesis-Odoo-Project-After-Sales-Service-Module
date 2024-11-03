from datetime import datetime, time, date
from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from lxml import etree
from odoo.addons.base.models.res_partner import _tz_get

MAX_RECURRENT_EVENT = 720

RRULE_TYPE_SELECTION = [
    ('daily', 'Days'),
    ('weekly', 'Weeks'),
    ('monthly', 'Months'),
    ('yearly', 'Years'),
]

class SchoolAnnouncementTable(models.Model):
    _name = 'school.announcement'
    _description = 'Announcement'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Code No:', help="Sequence Number of the Announcement")
    is_announcement = fields.Boolean(string='Is general Announcement?', help="To set Announcement as general announcement")
    announcement_reason = fields.Text(string='Title', states={'draft': [('readonly', False)]}, required=True, readonly=True, help="Announcement Subject")
    state = fields.Selection([('draft', 'Draft'), ('submitted', 'Submitted'), ('expired', 'Expired')], string='Status', default='draft', track_visibility='always')
    date_start = fields.Datetime(string='Start Date', default=datetime.now().strftime('%Y-%m-%d'), required=True, help="Start date of announcement want to see")
    date_end = fields.Datetime(string='End Date', default=datetime.now().strftime('%Y-%m-%d'), required=True, help="End date of announcement want too see")
    announcement_type = fields.Selection([('employee', 'By Employee'), 
                                          ('teacher', 'By Teacher'), 
                                          ('program', 'By Program'),
                                          ('intake', 'By Intake'), 
                                          ('group_class', 'By Group Class')])
    requested_date = fields.Date(string='Requested Date', default=datetime.now().strftime('%Y-%m-%d'),help="Create Date of Record")
    attachment_id = fields.Many2many('ir.attachment', 'doc_school_announcement_rel', 'doc_id', 'attach_id4', string="Attachment", help='You can attach the copy of your Letter')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, readonly=True, help="Login user Company")
    is_select_all = fields.Boolean(string='Select All')
    email_employee_ids = fields.Many2many('hr.employee', 'school_email_employee_list', string='Get Employees Email Details')
    email_teacher_ids = fields.Many2many('school.teacher', 'school_email_teacher_list', string='Get Teachers Email Details')
    email_student_ids = fields.Many2many('student.student', 'school_email_student_list', string='Get Students Email Details')

    announcement = fields.Html(string='Letter', states={'draft': [('readonly', False)]}, readonly=True, help="Announcement Content")
    recurrency = fields.Boolean('Recurrent', help="Recurrent Announcement")
    interval = fields.Integer(string='Repeat Every', readonly=False, help="Repeat every (Days/Week/Month/Year)", default=1)
    rrule_type = fields.Selection(RRULE_TYPE_SELECTION, string='Recurrence', help="Let the event automatically repeat at that interval", readonly=False, default='weekly')
    event_tz = fields.Selection(_tz_get, string='Timezone', readonly=False)
    count = fields.Integer(string='Repeat', help="Repeat x times", readonly=False, default=1)
    parent_id = fields.Many2one('school.announcement', string="Parent")
    child_ids = fields.One2many('school.announcement', 'parent_id', 'Child Announcement')

    employee_ids = fields.Many2many('hr.employee', 'school_employee_announcement', 'announcement', 'employee', string='Employees', 
                                     help="Employee's which want to see this announcement")
    teacher_ids = fields.Many2many('school.teacher', 'school_teacher_announcement', 'announcement', 'teacher', string='Teachers', 
                                    help="Teacher's which want to see this announcement")
    program_ids = fields.Many2many('standard.standard', 'school_program_announcement', 'announcement', 'program', string='Program', 
                                    help="Program's which want to see this announcement")
    program_id = fields.Many2one('standard.standard', string='Program')
    intake_ids = fields.Many2many('school.standard', 'school_intake_announcement', 'announcement', 'intake', string='Intake', 
                                  domain="[('standard_id', 'in', program_ids)]", help="Intake's which want to see this announcement")
    intake_id = fields.Many2one('school.standard', string='Intake', domain="[('standard_id', '=', program_id)]")
    group_class_ids = fields.Many2many('group.class', 'school_group_class_announcement', 'announcement', 'group_class', string='Group Class', 
                                        domain="[('intake', 'in', intake_ids)]", help="Group Class's which want to see this announcement")
    student_ids = fields.Many2many('student.student', 'school_student_announcement', 'announcement', 'student',
                                    string='Students', help="Student's which want to see this announcement")

    @api.onchange('announcement_type')
    def _onchange_announcement_type(self):
        self.clear_users_tab()
        if self.announcement_type == 'employee':
            employees = self.env['hr.employee'].search([])
            self.employee_ids = [(6, 0, employees.ids)]

    @api.onchange('is_select_all')
    def _onchange_select_all(self):
        if self.is_select_all == True:
            program = self.env['standard.standard'].search([])
            self.program_ids = [(6, 0, program.ids)]
    
    @api.onchange('program_ids')
    def _onchange_program_ids(self):
        all_program = self.program_ids.search([]).ids
        if self.program_ids.ids != all_program:
            self.is_select_all = False
        if self.announcement_type == 'teacher':
            teacher = self.env['school.teacher'].search([('program_id', 'in', self.program_ids.ids)])
            self.teacher_ids = [(6, 0, teacher.ids)]
        elif self.announcement_type == 'program':
            intake_ids = []
            for program in self.program_ids:
                intake_ids += program.intake_ids.ids
            standard = self.env['school.standard'].search([('id', 'in', intake_ids)])
            student_ids = []
            for intake in standard:
                for student in intake.intake_student_line_ids:
                    student_ids.append(student.student_id.id)
            self.student_ids = [(6, 0, student_ids)]

    @api.onchange('program_id')
    def _onchange_program_id(self):
        if self.announcement_type == 'intake':
            self.intake_ids = [(5, 0, 0)]
        elif self.announcement_type == 'group_class':
            self.intake_id = False

    @api.onchange('intake_ids')
    def _onchange_intake_ids(self):
        if self.announcement_type == 'intake':
            student_ids = []
            for intake in self.intake_ids:
                for student in intake.intake_student_line_ids:
                    student_ids.append(student.student_id.id)
            self.student_ids = [(6, 0, student_ids)]

    @api.onchange('intake_id')
    def _onchange_intake_id(self):
        self.group_class_ids = [(5, 0, 0)]

    @api.onchange('group_class_ids')
    def _onchange_group_class_ids(self):
        student_ids = []
        for group_class in self.group_class_ids:
            student_ids += group_class.student_ids.ids
        self.student_ids = [(6, 0, student_ids)]
    
    def clear_users_tab(self):
        self.employee_ids = [(5, 0, 0)]
        self.teacher_ids = [(5, 0, 0)]
        self.program_ids = [(5, 0, 0)]
        self.program_id = False
        self.intake_ids = [(5, 0, 0)]
        self.intake_id = False
        self.group_class_ids = [(5, 0, 0)]
        self.student_ids = [(5, 0, 0)]
        self.is_select_all = False

    def get_user_email_list(self):
        for rec in self:
            if rec.is_announcement:
                rec.email_employee_ids = self.env['hr.employee'].search([])
                rec.email_teacher_ids = self.env['school.teacher'].search([])
                rec.email_student_ids = self.env['student.student'].search([])
                rec.announcement_type = False
            elif rec.announcement_type == 'employee':
                rec.email_employee_ids = rec.employee_ids
                rec.email_teacher_ids = False
                rec.email_student_ids = False
            elif rec.announcement_type == 'teacher':
                rec.email_employee_ids = False
                rec.email_teacher_ids = rec.teacher_ids
                rec.email_student_ids = False
            elif rec.announcement_type in ('program', 'intake', 'group_class'):
                rec.email_employee_ids = False
                rec.email_teacher_ids = False
                rec.email_student_ids = rec.student_ids
            else:
                rec.email_employee_ids = False
                rec.email_teacher_ids = False
                rec.email_student_ids = False

    def get_user_email(self, email_employee_ids, email_teacher_ids, email_student_ids):
        email_list = [emp.work_email for emp in email_employee_ids] + [teacher.work_email for teacher in email_teacher_ids] + [student.email for student in email_student_ids]
        return str(email_list).replace('[', '').replace(']', '').replace("'", '')

    def get_emp_name(self, email_employee_ids):
        return str([emp_name.name for emp_name in email_employee_ids]).replace('[', '').replace(']', '').replace("'", '')

    def get_teacher_name(self, email_teacher_ids):
        return str([teacher.name for teacher in email_teacher_ids]).replace('[', '').replace(']', '').replace("'", '')

    def get_student_name(self, email_student_ids):
        return str([student.name for student in email_student_ids]).replace('[', '').replace(']', '').replace("'", '')

    def get_expiry_state(self):
        """
        Function is used for Expiring Announcement based on expiry date
        it activate from the crone job.

        """
        now = datetime.now()
        ann_obj = self.search([('state', '!=', 'draft')])
        for recd in ann_obj:
            if recd.date_end < now:
                recd.write({'state': 'expired'})

    def action_cron_running(self):
        announce = self.search([('state', '=', 'draft')])
        now_date = datetime.now()
        for res in announce:
            if now_date >= res.date_start and now_date <= res.date_end:
                res.write({'state': 'submitted'})

    @api.constrains('date_start', 'date_end')
    def validation(self):
        if self.date_start > self.date_end:
            raise ValidationError("Start date must be less than End Date")

    @api.model
    def create(self, vals):
        if vals.get('is_announcement'):
            vals['name'] = self.env['ir.sequence'].next_by_code('school.announcement.general')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code('school.announcement')
        return super(SchoolAnnouncementTable, self).create(vals)

    @api.constrains('recurrency','count')
    def onchange_recurrence_count(self):
        if self.recurrency:
            if self.count > MAX_RECURRENT_EVENT:
                raise ValidationError("Max Number of repetitions is 720!")

    def submit(self):
        self.get_user_email_list()
        template_id = self.env.ref('equip3_school_operation.email_template_announcement')
        if self.attachment_id:
            template_id.attachment_ids = [(6, 0, self.attachment_id.ids)]
        if self.is_announcement:
            template_id.sudo().send_mail(self.id, force_send=True)
        else:
            if self.announcement_type == 'employee':
                for employee in self.employee_ids:
                    recipient = {'name': employee.name, 'email': employee.work_email}
                    template_id.sudo().with_context(recipient=recipient).send_mail(self.id, force_send=True)
            elif self.announcement_type == 'teacher':
                for teacher in self.teacher_ids:
                    recipient = {'name': teacher.name, 'email': teacher.work_email}
                    template_id.sudo().with_context(recipient=recipient).send_mail(self.id, force_send=True)
            elif self.announcement_type in ('program', 'intake', 'group_class'):
                for student in self.student_ids:
                    recipient = {'name': student.name, 'email': student.email}
                    template_id.sudo().with_context(recipient=recipient).send_mail(self.id, force_send=True)
        self.state = 'submitted'

    def compute_next_date(self, date, period, interval):
        if period == 'daily':
            date += relativedelta(days=interval)
        elif period == 'weekly':
            date += relativedelta(weeks=interval)
        elif period == 'monthly':
            date += relativedelta(months=interval)
        elif period == 'yearly':
            date += relativedelta(years=interval)
        return date

    def action_create_recurrence(self):
        recurrence_ids = self.env['school.announcement']
        announce = self.search([('state', '=', 'expired'),('parent_id', '=', False)])
        for rec in announce:
            if rec.recurrency:
                count = min(rec.count, MAX_RECURRENT_EVENT)
                count_child = len(rec.child_ids)
                child_ids = rec.child_ids.filtered(lambda l: l.state == "expired").sorted(key="id")[-1:]
                if count_child > 0 and not child_ids:
                    continue
                elif count_child > 0 and child_ids:
                    date_begin = child_ids.date_start
                    date_begin_time = child_ids.date_start.time()
                    date_end = child_ids.date_end
                else:
                    date_begin = rec.date_start
                    date_begin_time = rec.date_start.time()
                    date_end = rec.date_end
                if count_child < count:
                    start_date = date_begin
                    end_date = date_end
                    diff = (end_date.date() - start_date.date()).days
                    date_begin = self.compute_next_date(end_date, rec.rrule_type, rec.interval)
                    ends_date = date_begin + relativedelta(days=diff)
                    date_end = ends_date
                    date_begin = datetime.combine(date_begin, date_begin_time)
                    vals = {
                        'parent_id': rec.id,
                        'attachment_id': rec.attachment_id.ids or [],
                        'is_announcement': rec.is_announcement,
                        'announcement_reason': rec.announcement_reason,
                        'announcement_type': rec.announcement_type,
                        'employee_ids': rec.employee_ids.ids or [],
                        'teacher_ids': rec.teacher_ids.ids or [],
                        'student_ids': rec.student_ids.ids or [],
                        'announcement': rec.announcement,
                        'date_start': date_begin,
                        'date_end': date_end,
                        'email_employee_ids': rec.email_employee_ids.ids or False,
                        'email_teacher_ids': rec.email_teacher_ids.ids or False,
                        'email_student_ids': rec.email_student_ids.ids or False,
                    }
                    recurrence_ids.create(vals)
