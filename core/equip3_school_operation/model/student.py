import base64
from ast import If
import pytz
from odoo.modules import get_module_resource
from pytz import timezone, UTC
from odoo import api, fields, models, _, tools
from datetime import timedelta, datetime, date
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from odoo.exceptions import UserError, ValidationError


class StudentAssign(models.Model):
    _name = "student.student"
    _inherit = ["student.student", "mail.thread", "mail.activity.mixin"]
    _description = "Admission Register"
    _order = "create_date desc"

    @api.depends("student_type")
    def _compute_name(self):
        """Method to compute student name"""
        for rec in self:
            if rec.student_type:
                if rec.student_type == "existing_student":
                    student = rec.student_id.student_id
                rec.student_name = student

    @api.model
    def _default_image(self):
        '''Method to get default Image'''
        image_path = get_module_resource('equip3_school_operation', 'static/src/img',
                                         'student1.png')
        return base64.b64encode(open(image_path, 'rb').read())

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [('school_branch_ids','in',allowed_branch_ids)]

    school_id = fields.Many2one(string="School", domain=_domainSchool)
    student_type = fields.Selection([('new_student', 'New Student'), ('existing_student', 'Existing Student')],
                                    string="Student Type", default="new_student")
    student_id = fields.Many2one("student.student", "Student Name", help="Select related student")
    student_name = fields.Char("Name", compute="_compute_name", store=True, help="Enter Student name",
                               track_visibility='onchange')
    fees_ids = fields.Many2one('student.fees.structure', related="program_id.fees_ids", string='Fees Structure',
                               store=True)
    middle = fields.Char(required=False, track_visibility='onchange')
    last = fields.Char(required=False, track_visibility='onchange')
    full_name = fields.Char(compute='_compute_full_name')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")
    is_pdpa_constent = fields.Boolean(string="PDPA Constent")
    name_presented = fields.Char(string='Name Presented on Certificate', required=True, track_visibility='onchange')
    nric = fields.Char(string='Identification No.', required=True)
    year = fields.Many2one(readonly=False, domain="[('current', '=', True)]")
    state = fields.Selection([('draft', 'Draft'),
                              ('applied', 'Applied'),
                              ('confirmed', 'Pending Payment'),
                              ('done', 'Done'),
                              ('rejected', 'Rejected'),
                              ('terminate', 'Terminate'),
                              ('cancel', 'Cancel'),
                              ('alumni', 'Alumni')],
                             'Status', readonly=True, default="draft",
                             help='State of the student registration form', track_visibility='onchange', tracking=True)
    term_id = fields.Many2one('academic.month', string="Term", compute='_compute_term_id', store=True)
    approved_matrix_id = fields.Many2one('school.approval.matrix', compute="_compute_approved_matrix",
                                         string="Approving Matrix", store=True, required=False)
    approved_matrix_ids = fields.One2many('school.approval.matrix.line', 'stu_id', compute="_approving_matrix_lines",
                                          store=True, string="Approved Matrix")
    is_approve_button = fields.Boolean(string='Is Approve Button', compute='_get_approve_button', store=False)
    approval_matrix_line_id = fields.Many2one('school.approval.matrix.line', string='Approval Matrix Line',
                                              compute='_get_approve_button', store=False)
    program_id = fields.Many2one('standard.standard', string="Program", required=True)
    academic_code = fields.Char(related='year.code', string='Code', store=True)
    standard_id = fields.Many2one('school.standard',
                                  domain="[('standard_id', '=', program_id), ('start_year', '=', academic_code)]",
                                  string='Intake')
    program_ids = fields.One2many('standard.standard', related="school_id.school_program_ids", string="Program",
                                  store=False)
    portal_user_id = fields.Many2one('res.users', string='Portal User')
    phone = fields.Char(string='Phone', track_visibility='onchange')
    email = fields.Char(string='Email', track_visibility='onchange')
    mobile = fields.Char(string='Mobile', track_visibility='onchange')
    website = fields.Char(string="Website", track_visibility="onchange")
    photo = fields.Binary('Photo', default=_default_image,
                          help='Attach student photo')
    message_ids = fields.One2many(
        "mail.message",
        "res_id",
        "Messages",
        domain=lambda self: [("model", "=", self._name)],
        auto_join=True,
        help="Messages can entered",
    )
    message_follower_ids = fields.One2many(
        "mail.followers",
        "res_id",
        "Followers",
        domain=lambda self: [("res_model", "=", self._name)],
        help="Select message followers",
    )
    activity_ids = fields.One2many(
        'mail.activity', 'res_id', 'Activities',
        auto_join=True,
        groups="base.group_user", )
    academic_tracking_ids = fields.One2many('academic.tracking', 'student_id')
    subject_ids = fields.Many2many('subject.subject', compute='_compute_subject_ids', store=True)
    branch_id = fields.Many2one(comodel_name='res.branch', related='school_id.branch_id', store=True, string='Branch', )
    user_id = fields.Many2one(
        'res.users', 'User ID',
        ondelete="cascade",
        required=False, delegate=False,
        help='Select related user of the student'
    )
    name = fields.Char("Name")
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="State",
        ondelete="restrict",
        domain="[('country_id', '=?', country_id)]",
    )
    country_id = fields.Many2one("res.country", string="Country", ondelete="restrict")
    comment = fields.Text("Notes")
    color = fields.Integer("Color Index")
    company_ids = fields.Many2many('res.company', string="Companies")
    type = fields.Selection([('local_student', 'Local Student'),
                             ('international_student', 'International Student')
                            ], string='Type', default="local_student")
    personal_document = fields.Binary(string='Personal Document')
    transfer_student = fields.Selection(selection=[
                            ('yes', 'Yes'),
                            ('no', 'No')
                        ], string='Transfer Student')
    previous_school = fields.Char(string='Previous School')
    student_pass_registry = fields.Char(string='Student Pass Registry (SOLAR Application Number)')
    student_pass_status = fields.Char(string='Student Pass Status')
    student_pass_digital = fields.Binary(string='Student Pass Digital')
    appeal_from = fields.Binary(string='Appeal From (If Needed)')
    med_checkup_form = fields.Binary(string='Medical Check Up Form')
    med_checkup_result = fields.Binary(string='Medical Check Up Result')
    med_checkup_date = fields.Date(string='Medical Check Up Date')
    fees_register_id = fields.Many2one('student.fees.register', string='Fees Register')
    teacher_assignment_id = fields.Many2one('school.teacher.assignment', string='Teacher Assignment')
    exam_id = fields.Many2one('exam.exam', string='Exam')
    additional_exam_id = fields.Many2one('additional.exam', string='Additional Exam')

    @api.onchange('gender')
    def _onchange_default_image(self):
        if self.gender == 'male':
            image_path = get_module_resource('equip3_school_operation', 'static/src/img', 'student1.png')
        else:
            image_path = get_module_resource('equip3_school_operation', 'static/src/img', 'student2.png')
        self.photo = base64.b64encode(open(image_path, 'rb').read())

    @api.depends('academic_tracking_ids', 'academic_tracking_ids.all_score_subject_ids')
    def _compute_subject_ids(self):
        for rec in self:
            rec.subject_ids = [(5, 0, 0)]
            subject_ids = []
            for tracking in rec.academic_tracking_ids:
                subject_ids += tracking.all_score_subject_ids.mapped('subject_id').ids
            rec.subject_ids = [(6, 0, subject_ids)]

    def attendance_action_btn(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Attendance Line',
            'res_model': 'daily.attendance.line',
            'domain': [('student_id', '=', self.id)],
            'view_mode': 'tree',
        }
        return action

    def attendance_action_btn(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Attendance Line',
            'res_model': 'daily.attendance.line',
            'domain': [('student_id', '=', self.id)],
            'view_mode': 'tree',
        }
        return action

    @api.model
    def default_get(self, fields):
        res = super(StudentAssign, self).default_get(fields)
        year_id = self.env['academic.year'].search([('current', '=', True)], limit=1, order="id")
        res['year'] = year_id and year_id.id or False
        return res

    @api.onchange('name', 'middle', 'last')
    def _onchange_first_middle_last_name(self):
        name_presented = self.name
        if self.middle:
            name_presented += ' ' + self.middle
        if self.last:
            name_presented += ' ' + self.last
        self.name_presented = name_presented

    @api.depends('name', 'middle', 'last')
    def _compute_full_name(self):
        for rec in self:
            full_name = rec.name
            if rec.middle:
                full_name += ' ' + rec.middle
            if rec.last:
                full_name += ' ' + rec.last
            rec.full_name = full_name

    @api.onchange('school_id', 'program_id')
    def _onchange_standard_id(self):
        school_standard_id = self.env['school.standard'].search([
            ('standard_id', '=', self.program_id.id),
            ('start_year', '=', self.year.code),
        ], limit=1)
        if school_standard_id:
            self.standard_id = school_standard_id
        else:
            self.standard_id = False

        if self.school_id :
            branch_id = self.school_id.branch_id
            if not branch_id :
                branch_id = self.env["res.branch"].sudo().search([('company_id','=',self.school_id.company_id.id)], limit=1, order="id desc")
            self.branch_id = branch_id

    @api.depends('year')
    def _compute_term_id(self):
        for record in self:
            today_date = date.today()
            term_id = record.year.month_ids.filtered(lambda r: r.enrollment_date_start and r.enrollment_date_stop
                                                               and r.enrollment_date_start <= today_date and r.enrollment_date_stop >= today_date)
            record.term_id = False
            if term_id:
                record.term_id = term_id and term_id[0].id or False

    def _get_approve_button(self):
        for record in self:
            record.is_approve_button = False
            record.approval_matrix_line_id = False
            if record.state == "applied":
                matrix_lines = sorted(
                    record.approved_matrix_ids.filtered(lambda r: not r.approved and r.state == "confirmed"))
                if len(matrix_lines) > 0 :
                    matrix_line_id = matrix_lines[0]
                    if self.env.user.id in matrix_line_id.user_id.ids and self.env.user.id != matrix_line_id.last_approved.id:
                        record.is_approve_button = True
                        record.approval_matrix_line_id = matrix_line_id.id
            elif record.state == "confirmed":
                matrix_lines = sorted(
                    record.approved_matrix_ids.filtered(lambda r: not r.approved and r.state == "done"))
                if len(matrix_lines) > 0:
                    matrix_line_id = matrix_lines[0]
                    if self.env.user.id in matrix_line_id.user_id.ids and self.env.user.id != matrix_line_id.last_approved.id:
                        record.is_approve_button = True
                        record.approval_matrix_line_id = matrix_line_id.id
            elif record.state == "rejected":
                matrix_lines = sorted(
                    record.approved_matrix_ids.filtered(lambda r: not r.approved and r.state == "draft"))
                if len(matrix_lines) > 0:
                    matrix_line_id = matrix_lines[0]
                    if self.env.user.id in matrix_line_id.user_id.ids and self.env.user.id != matrix_line_id.last_approved.id:
                        record.is_approve_button = True
                        record.approval_matrix_line_id = matrix_line_id.id

    @api.depends('approved_matrix_id')
    def _approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            record.approved_matrix_ids = []
            for line in record.approved_matrix_id.approval_matrix_ids:
                data.append((0, 0, {
                    'state': line.state,
                    'user_id': [(6, 0, line.user_id.ids)],
                    'minimum_approver': line.minimum_approver,
                }))
            record.approved_matrix_ids = data

    @api.depends('school_id', 'program_id')
    def _compute_approved_matrix(self):
        for record in self:
            record.approved_matrix_id = False
            if record.school_id and record.program_id:
                approval_matrix_id = self.env['school.approval.matrix'].search([
                    ('school_id', '=', record.school_id.id),
                    ('program_id', '=', record.program_id.id)
                ], limit=1)
                record.approved_matrix_id = approval_matrix_id and approval_matrix_id.id or False

    def action_apply(self):
        for record in self:
            record.state = 'applied'
            record.message_post(body="%s applied admission register" % (self.env.user.name))

    def action_reject(self):
        for record in self:
            name = record.approval_matrix_line_id.approved_status or ''
            if name != '':
                name += "\n • %s: Rejected" % (self.env.user.name)
            else:
                name += "• %s: Rejected" % (self.env.user.name)
            date = record.approval_matrix_line_id.approval_time or ''
            if date != '':
                date += "•" + self.env.user.name + ":" +datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT) 
            else:
                date += "•" + self.env.user.name + ":" +datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record.approval_matrix_line_id.write({
                'last_approved': self.env.user.id,
                'approved_users': [(4, self.env.user.id)],
                'approval_time': date,
                'approved_status': name
            })
            if record.approval_matrix_line_id.approved:
                record.state = 'rejected'

    def action_confirm(self):
        for record in self:
            name = record.approval_matrix_line_id.approved_status or ''
            if name != '':
                name += "\n • %s: Approved" % (self.env.user.name)
            else:
                name += "• %s: Approved" % (self.env.user.name) 
            date = record.approval_matrix_line_id.approval_time or ''
            if date != '':
                date += "•" + self.env.user.name + ":" +datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT) 
            else:
                date += "•" + self.env.user.name + ":" +datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record.approval_matrix_line_id.write({
                'last_approved': self.env.user.id,
                'approved_users': [(4, self.env.user.id)],
                'approval_time': date,
                'approved_status': name
            })
            if record.approval_matrix_line_id.approved:
                record.state = 'confirmed'
                return record.sudo()._action_create_student_invoice()
            record.message_post(body="%s confirmed admission register" % (self.env.user.name))

    def action_set_to_draft(self):
        for record in self:
            name = record.approval_matrix_line_id.approved_status or ''
            if name != '':
                name += "\n • %s: Approved" % (self.env.user.name)
            else:
                name += "• %s: Approved" % (self.env.user.name)
            date = record.approval_matrix_line_id.approval_time or ''
            if date != '':
                date += "•" + self.env.user.name + ":" +datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT) 
            else:
                date += "•" + self.env.user.name + ":" +datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record.approval_matrix_line_id.write({
                'last_approved': self.env.user.id,
                'approved_users': [(4, self.env.user.id)],
                'approval_time': date,
                'approved_status': name
            })
            if record.approval_matrix_line_id.approved:
                record.state = 'draft'

    @api.model
    def academic_year_term(self):
        today_date = date.today()
        start_date = date.today().replace(day=1)
        next_date = start_date.replace(day=28) + timedelta(days=4)
        next_month_date = (next_date - timedelta(days=next_date.day)) + timedelta(days=1)
        student_records = self.search(
            [('state', '=', 'done'), ('student_type', '=', 'new_student'), ('fees_ids', '!=', False),
             ('year', '!=', False)])
        for student in student_records:
            if student.fees_ids.line_ids.filtered(lambda r: r.type == 'term'):
                date_filter = student.year.month_ids.filtered(lambda r: r.date_start.month == next_month_date.month)
                final_date = date_filter.billing_date
                journal = self.env['account.journal'].search(
                    [('type', '=', 'sale'), ('company_id', '=', self.env.company.id)])
                if final_date == today_date:
                    vals = {
                        "student_id": student.id,
                        "fees_structure_id": student.fees_ids.id,
                        "standard_id": student.standard_id.id,
                        "medium_id": student.medium_id.id,
                        "journal_id": journal.company_id.id,
                    }
                    slip_obj = self.env["student.payslip"].create(vals)
                    slip_obj.onchange_student_id()
                    slip_obj.monthly_payslip_confirm()
                    invoice_vals = slip_obj.student_pay_fees()
                    ctx = {
                        'email_from': self.env.company.email,
                    }
                    template_id = self.env.ref('equip3_school_operation.generate_student_invoice_email_templates')
                    template_id.with_context(ctx).send_mail(invoice_vals['res_id'], force_send=True)

    # @api.model
    # def academic_year_term_history_status(self):
    #     today_date = date.today()
    #     student_history = self.env['student.history'].search([('term_id.date_stop', '<', today_date)])
    #     student_history.write({'status': 'unactive'})

    def student_admission_done(self):
        for record in self:
            name = record.approval_matrix_line_id.approved_status or ''
            if name != '':
                name += "\n • %s: Approved" % (self.env.user.name)
            else:
                name += "• %s: Approved" % (self.env.user.name)
            date = record.approval_matrix_line_id.approval_time or ''
            if date != '':
                date += "•" + self.env.user.name + ":" +datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT) 
            else:
                date += "•" + self.env.user.name + ":" +datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
            record.approval_matrix_line_id.write({
                'last_approved': self.env.user.id,
                'approved_users': [(4, self.env.user.id)],
                'approval_time': date,
                'approved_status': name
            })
            if record.approval_matrix_line_id.approved:
                record.write({'state': 'done'})
                record.admission_done()
    
    def admission_done(self):
        res = super(StudentAssign, self).admission_done()
        school_standard_obj = self.env['school.standard']
        ir_sequence = self.env['ir.sequence']
        student_group = self.env.ref('school.group_school_student')
        emp_group = self.env.ref('base.group_user')
        for rec in self:
            new_grp_list = [student_group.id, emp_group.id]
            if rec.portal_user_id:
                rec.portal_user_id.write({
                    'groups_id': [(6, 0, new_grp_list)],
                    'related_student_id': rec.id
                })
            academic_tracking_vals = {
                'student_id': rec.id if rec.student_type == 'new_student' else rec.student_id.id,
                'program_id': rec.program_id.id,
                'school_id': rec.school_id.id,
                'intake_ids': [(0, 0, {
                    'intake_id': rec.standard_id.id,
                    'status': "active"
                })],
            }
            academic_tracking_id = self.env['academic.tracking'].create(academic_tracking_vals)
            if rec.student_type == 'new_student':
                if not rec.standard_id:
                    raise ValidationError(_("Please select class!"))
                if rec.standard_id.remaining_seats <= 0:
                    raise ValidationError(_('Seats of class %s are full'
                                            ) % rec.standard_id.standard_id.name)
                domain = [('school_id', '=', rec.school_id.id)]
                if not school_standard_obj.search(domain):
                    raise UserError(_(
                        "Warning! The standard is not defined in school!"))
                number = 1
                for rec_std in rec.search(domain):
                    rec_std.roll_no = number
                    number += 1
                reg_code = ir_sequence.next_by_code('student.registration')
                registation_code = (str(rec.school_id.state_id.name) + str('/') +
                                    str(rec.school_id.city) + str('/') +
                                    str(rec.school_id.name) + str('/') +
                                    str(reg_code))
                stu_code = ir_sequence.next_by_code('student.code')
                student_code = (str(rec.school_id.code) + str('/') +
                                str(rec.year.code) + str('/') +
                                str(stu_code))
                rec.write({
                    'student_id': rec.student_id.id,
                    'admission_date': fields.Date.today(),
                    'student_code': student_code,
                    'reg_code': registation_code
                })

                rec.history_ids = [(0, 0, {
                    'academice_year_id': rec.year.id,
                    'division_id': rec.standard_id.division_id.id,
                    'standard_id': rec.standard_id.id,
                    'status': 'active',
                    'medium_id': rec.medium_id.id,
                    'school_id': rec.school_id.id or False,
                    'term_id': rec.term_id.id or False,
                    'program_id': rec.program_id.id or False,
                })]
            elif rec.student_type == 'existing_student':
                rec.student_id.write({
                    'name': rec.name,
                    'last': rec.last,
                    'middle': rec.middle,
                    'year': rec.year.id or False,
                    'email': rec.email,
                    'fees_ids': rec.fees_ids.id or False,
                    'name_presented': rec.name_presented,
                    'nric': rec.nric,
                    'school_id': rec.school_id.id or False,
                    'street': rec.street,
                    'street2': rec.street2,
                    'city': rec.city,
                    'state_id': rec.state_id.id or False,
                    'zip': rec.zip,
                    'country_id': rec.country_id.id or False,
                    'gender': rec.gender,
                    'date_of_birth': rec.date_of_birth,
                    'admission_date': fields.Date.today(),
                    'history_ids': [(0, 0, {
                        'academice_year_id': rec.year.id,
                        'division_id': rec.standard_id.division_id.id,
                        'standard_id': rec.standard_id.id,
                        'status': 'active',
                        'medium_id': rec.medium_id.id,
                        'school_id': rec.school_id.id or False,
                        'term_id': rec.term_id.id or False,
                        'program_id': rec.program_id.id or False,
                    })]
                })
                rec.standard_id.write(
                    {
                        "intake_student_line_ids": [
                            (0, 0, {"student_id": rec.student_id.id})
                        ]
                    }
                )
        
        return res

    def _action_create_student_invoice(self):
        for rec in self:
            if rec.student_type == 'new_student':
                rec.write({'state': 'confirmed'})

                student_journal = self.env['account.journal'].search([('type', '=', 'sale')], limit=1)
                vals = {
                    "student_id": self.id,
                    "fees_structure_id": self.fees_ids.id,
                    "standard_id": self.standard_id.id,
                    "medium_id": self.medium_id.id,
                    "journal_id": student_journal.id,
                    "first_student_payslip": True
                }
                slip_obj = self.env["student.payslip"].create(vals)
                slip_obj.onchange_student_id()
                slip_obj.payslip_confirm()
                slip_obj.student_pay_fees()
                '''Email to Student'''
                template_id = self.env.ref('equip3_school_operation.student_confirmation_email_template').id
                template = self.env['mail.template'].browse(template_id)
                template.send_mail(self.id, force_send=True)
                '''Email to Parents'''
                if self.parent_id:
                    template_id = self.env.ref('equip3_school_operation.parents_confirmation_email_template').id
                    template = self.env['mail.template'].browse(template_id)
                    template.send_mail(self.id, force_send=True)
                '''Student Invoice Redirect'''
                return {
                    'name': _('Student Payslip'),
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'student.payslip',
                    'res_id': slip_obj.id,
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                }
            elif rec.student_type == 'existing_student':
                rec.write({
                    'user_id': rec.student_id.user_id.id,
                    'state': 'confirmed'
                })
                student_journal = self.env["account.journal"].search(
                    [("type", "=", "sale")], limit=1
                )
                vals = {
                    "student_id": self.student_id.id,
                    "fees_structure_id": self.fees_ids.id,
                    "standard_id": self.standard_id.id,
                    "medium_id": self.medium_id.id,
                    "journal_id": student_journal.id,
                    "first_student_payslip": False,
                    "admission_ref": self.id
                }
                slip_obj = self.env["student.payslip"].create(vals)
                slip_obj.onchange_student_id()
                slip_obj.payslip_confirm()
                slip_obj.student_pay_fees()
                """Email to Student"""
                template_id = self.env.ref(
                    "equip3_school_operation.student_confirmation_email_template"
                ).id
                template = self.env["mail.template"].browse(template_id)
                template.send_mail(self.student_id.id, force_send=True)
                """Email to Parents"""
                if self.parent_id:
                    template_id = self.env.ref(
                        "equip3_school_operation.parents_confirmation_email_template"
                    ).id
                    template = self.env["mail.template"].browse(template_id)
                    template.send_mail(self.student_id.id, force_send=True)
                """Student Invoice Redirect"""
                return {
                    "name": _("Student Payslip"),
                    "view_type": "form",
                    "view_mode": "form",
                    "res_model": "student.payslip",
                    "res_id": slip_obj.id,
                    "type": "ir.actions.act_window",
                    "target": "current",
                }

    def set_terminate(self):
        res = super(StudentAssign, self).set_terminate()
        for rec in self:
            rec.history_ids.write({'status': 'unactive'})
        return res

    @api.model
    def create(self, values):
        res = super(StudentAssign, self).create(values)
        admission_group = self.env.ref('school.group_school_student')
        res.user_id.write({'groups_id': [(4, admission_group.id)]})

        return res

    def _get_street(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.street:
            address = "%s" % (partner.street)
        if partner.street2:
            address += ", %s" % (partner.street2)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    def _get_address_details(self, partner):
        self.ensure_one()
        res = {}
        address = ''
        if partner.city:
            address = "%s" % (partner.city)
        if partner.state_id.name:
            address += ", %s" % (partner.state_id.name)
        if partner.zip:
            address += ", %s" % (partner.zip)
        if partner.country_id.name:
            address += ", %s" % (partner.country_id.name)
        # reload(sys)
        html_text = str(tools.plaintext2html(address, container_tag=True))
        data = html_text.split('p>')
        if data:
            return data[1][:-2]
        return False

    @api.onchange('student_id')
    def onchange_student_id(self):
        if self.student_type == 'existing_student' and self.student_id:
            self.name = self.student_id.name or False
            self.middle = self.student_id.middle or False
            self.last = self.student_id.last or False
            self.year = self.student_id.year.id or False
            self.email = self.student_id.email or False
            self.fees_ids = self.student_id.fees_ids.id or False
            self.name_presented = self.student_id.name_presented or False
            self.nric = self.student_id.nric or False
            self.school_id = self.student_id.school_id.id or False
            self.street = self.student_id.street or False
            self.street2 = self.student_id.street2 or False
            self.city = self.student_id.city or False
            self.state_id = self.student_id.state_id.id or False
            self.zip = self.student_id.zip or False
            self.country_id = self.student_id.country_id.id or False
            self.gender = self.student_id.gender or False
            self.date_of_birth = self.student_id.date_of_birth or False
            self.term_id = self.student_id.term_id.id or False
        else:
            self.name = False
            self.middle = False
            self.last = False
            self.email = False
            self.fees_ids = False
            self.name_presented = False
            self.nric = False
            self.school_id = False
            self.street = False
            self.street2 = False
            self.city = False
            self.state_id = False
            self.zip = False
            self.country_id = False
            self.gender = False
            self.date_of_birth = False

    def _update_student_vals(self, vals):
        student_rec = self.env["student.student"].browse(
            vals.get("student_id")
        )
        partner_id = self.env['res.partner'].browse(vals.get('partner_id'))
        vals.update(
            {
                "name": student_rec.name,
                "middle": student_rec.middle,
                "last": student_rec.last,
                "gender": student_rec.gender,
                "date_of_birth": student_rec.date_of_birth,
            }
        )

    def button_admission_invoice(self):
        action = self.env.ref('school_fees.action_student_payslip_form').read()[0]
        payslips = self.env['student.payslip'].search([('student_id', '=', self.id)])
        if len(payslips) > 1:
            action['domain'] = [('id', 'in', payslips.ids)]
        elif len(payslips) == 1:
            action['views'] = [(self.env.ref('school_fees.view_student_payslip_form').id, 'form')]
            action['res_id'] = payslips.ids[0]
        else:
            action['domain'] = [('id', 'in', [])]
        return action

    @api.model
    def create(self, vals):
        """Inherited create method to assign values from student model"""
        if vals.get("student_id"):
            self._update_student_vals(vals)

        if 'student_type' in vals and vals['student_type'] == 'existing_student':
            if self.env['student.history'].search(
                    [('student_id', '=', vals['student_id']), ('program_id', '=', vals['program_id']),
                     ('status', '=', 'active')]):
                raise ValidationError("Student can't admission with the same active program")
        else:
            student_group = self.env.ref('school.group_school_student')
            emp_group = self.env.ref('base.group_user')
            new_grp_list = [student_group.id, emp_group.id]
            registered_user = self.env['res.users'].search([('login', '=', vals.get('email'))])
            if not registered_user:
                create_user = self.env['res.users'].create({
                    'name': vals.get('name'),
                    'login': vals.get('email'),
                    'password': vals.get('email'),
                    'groups_id': [(6, 0, new_grp_list)],
                })
                vals['user_id'] = create_user.id

        res = super(StudentAssign, self).create(vals)

        return res

    def write(self, vals):
        """Inherited write method to update values from student model"""
        if vals.get("student_id"):
            self._update_student_vals(vals)
        if 'email' in vals:
            self.user_id.write({
                'login': vals['email']
            })
            self.user_id.partner_id.write({
                'email': vals['email']
            })
        return super(StudentAssign, self).write(vals)


class StudentReference(models.Model):
    _inherit = "student.reference"

    email = fields.Char('Email', required=True, help='Enter Email')
    admission_id = fields.Many2one(
        comodel_name='student.admission.register',
        string='Student Admission',
        help='Student admission'
    )
    middle = fields.Char('Middle Name', required=False)
    last = fields.Char('Surname', required=False)

class ResourceResource(models.Model):
    _inherit = "resource.resource"

    name = fields.Char('Name', required=False, help='Enter Name')


class StudentleaveRequest(models.Model):
    _inherit = "studentleave.request"
    _description = "Student Leave Request"
    _order = "create_date desc"

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [('school_branch_ids', 'in', allowed_branch_ids)]

    school_id = fields.Many2one('school.school', string='School', required=True, domain=_domainSchool)
    program_id = fields.Many2one('standard.standard', string='Program', required=True, domain="[('school_id', '=', school_id)]")
    group_class = fields.Many2one('group.class', string='Group Class', required=False)
    pic_class = fields.Many2one('school.teacher', string='PIC Class')
    pic_intake = fields.Many2one('school.teacher', string='Intake PIC')
    branch_id = fields.Many2one(comodel_name='res.branch', readonly=True, compute='_compute_branch_id', store=True)
    name = fields.Char('Name', required=False, help='Enter Name', compute='_compute_request_name', store=True)
    state = fields.Selection(selection_add=[('waiting', 'Waiting for Approval')])
    approval_matrix_id = fields.Many2one(
        comodel_name='school.approval.matrix',
        string='Approval Matrix',
        domain=[('approval_for', '=', 'student_leave')],
        compute='_compute_approval_matrix',
        store=True
    )
    approval_matrix_line_ids = fields.One2many(
        comodel_name="student.leave.approval.matrix",
        inverse_name="student_leave_id",
        string="Approval Matrix Line"
    )
    is_need_approval = fields.Boolean(string='Need Approval', compute='_compute_is_need_approval')
    is_leave_approval_matrix = fields.Boolean(string='Is Leave Approval Approval')
    is_created = fields.Boolean('Is Created')
    subject_id = fields.Many2one('subject.subject', string='Subject')
    is_student_leave_request_per_subject = fields.Boolean(
        string="Student Leave Request per Subject"
    )

    @api.model
    def create(self, vals):
        if "is_created" in vals:
            vals["is_created"] = True

        res = super(StudentleaveRequest, self).create(vals)

        return res

    @api.model
    def default_get(self, fields):
        res = super(StudentleaveRequest, self).default_get(fields)
        school_setting_id = self.env.ref("equip3_school_setting.school_config_settings_data").id
        school_config = self.env["school.config.settings"].browse([school_setting_id])
        if school_config.leave_approval_matrix:
            res.update({"is_leave_approval_matrix": True})
        
        if school_config.student_leave_request_per_subject:
            res.update({"is_student_leave_request_per_subject": True})

        return res
    
    @api.onchange("group_class")
    def get_subject_domain_by_group_class(self):
        if not self.group_class:
            return {}
        
        subject_ids = self.group_class.subject_ids.mapped('subject_id').ids

        return {
            "domain": {
                "subject_id": [("id", "in", subject_ids)]
            }
        }

    @api.depends('student_id', 'start_date')
    def _compute_request_name(self):
        for request in self:
            name = False
            leave_date = request.get_leave_date()
            student_name = request.student_id.name
            if request.student_id and request.start_date:
                name = _("%s (%s)" % (student_name, leave_date))
            
            request.name = name
    
    def get_leave_date(self):
        for request in self:
            start_date = request.start_date
            end_date = request.end_date

            if start_date == end_date:
                return str(start_date)
            leave_date = _("%s - %s" % (str(start_date), str(end_date)))

            return leave_date
    
    @api.depends("approval_matrix_id")
    def _compute_is_need_approval(self):
        for request in self:
            approval_matrix = request.approval_matrix_id
            approver_user_ids, approved_user_ids = (
                request.get_approver_and_approved_user_ids()
            )
            current_user = self.env.uid
            if (
                approval_matrix
                and current_user in approver_user_ids
                and current_user not in approved_user_ids
                and request.state == "waiting"
            ):
                request.is_need_approval = True
            else:
                request.is_need_approval = False

    def get_approver_and_approved_user_ids(self):
        approver_user_ids = []
        approved_user_ids = []
        for request in self:
            next_approval_line = request.approval_matrix_line_ids.filtered(
                lambda line: len(line.approved_user_ids) < len(line.user_ids)
            ).sorted(key=lambda line: line.sequence)
            if next_approval_line:
                for line in next_approval_line[0]:
                    for approver_id in line.user_ids.ids:
                        approver_user_ids.append(approver_id)

                    for approved_id in line.approved_user_ids.ids:
                        approved_user_ids.append(approved_id)

        return approver_user_ids, approved_user_ids

    @api.depends('school_id', 'program_id')
    def _compute_approval_matrix(self):
        for request in self:
            request.approval_matrix_id = False
            if request.school_id and request.program_id and request.is_leave_approval_matrix:
                approval_matrix = self.env['school.approval.matrix'].search(
                    [
                        ('approval_for', '=', 'student_leave'),
                        ('school_id', '=', request.school_id.id),
                        ('program_id', '=', request.program_id.id)
                    ], limit=1
                )
                
                request.approval_matrix_id = approval_matrix.id
                request.get_approval_matrix(request.approval_matrix_id)
    
    def get_approval_matrix(self, matrix):
        for request in self:
            if matrix:
                data_approvers = []
                for line in matrix.approval_matrix_ids:
                    data_approvers.append(
                        (
                            0,
                            0,
                            {
                                "sequence": line.sequence,
                                "minimum_approver": line.minimum_approver,
                                "user_ids": [(6, 0, line.user_id.ids)],
                            },
                        )
                    )
                request.approval_matrix_line_ids = [(5, 0, 0)] + data_approvers
            else:
                request.approval_matrix_line_ids = [(5, 0, 0)]
    
    def _reset_sequence(self):
        for request in self:
            current_sequence = 1
            for line in request.approval_matrix_line_ids:
                line.sequence = current_sequence
                current_sequence += 1

    def copy(self, default=None):
        res = super(
            StudentleaveRequest, self.with_context(keep_line_sequence=True)
        ).copy(default)

        return res
    
    def request_approval(self):
        for request in self:
            request.write({"state": "waiting"})

    def action_approve(self):
        for request in self:
            user = self.env.user
            for line in request.approval_matrix_line_ids:
                if user.id in line.user_ids.ids:
                    approved_time = line.approved_time or ""
                    if approved_time != "":
                        approved_time += "\n• %s: Approved - %s" % (
                            user.name,
                            datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        )
                    else:
                        approved_time += "• %s: Approved - %s" % (
                            user.name,
                            datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                        )
                    line.write({"approved_user_ids": [(4, user.id)]})
                    if len(line.approved_user_ids) < line.minimum_approver:
                        line.write(
                            {
                                "state": "waiting",
                                "approval_status": "Waiting for Approval",
                                "approved_time": approved_time
                            }
                        )
                    else:
                        line.write(
                            {
                                "state": "confirmed",
                                "approval_status": "Confirmed Request",
                                "approved_time": approved_time
                            }
                        )

            confrimed_approvals = request.approval_matrix_line_ids.filtered(
                lambda line: line.state == "confirmed"
                and len(line.user_ids.ids) == len(line.approved_user_ids.ids)
            )
            if len(confrimed_approvals.ids) == len(
                request.approval_matrix_id.approval_matrix_ids.ids
            ):
                request.approve_state()
    
    def action_reject(self, reason):
        for request in self:
            user = self.env.user
            for line in request.approval_matrix_line_ids:
                feedback = line.feedback or ""
                if feedback != "":
                    feedback += "\n• %s:  %s" % (user.name, reason)
                else:
                    feedback += "• %s: %s" % (user.name, reason)

                if user.id in line.user_ids.ids:
                    line.write(
                        {
                            "approved_user_ids": [(4, user.id)],
                            "total_reject_users": line.total_reject_users + 1,
                        }
                    )
                    if (
                        line.total_reject_users == line.minimum_approver
                        and line.total_reject_users != len(line.user_ids.ids)
                    ):
                        line.write(
                            {
                                "approval_status": "Waiting for Approval",
                                "feedback": feedback,
                            }
                        )
                    else:
                        line.write(
                            {
                                "approval_status": "Rejected",
                                "state": "rejected",
                                "feedback": feedback,
                            }
                        )
            confrimed_approvals = request.approval_matrix_line_ids.filtered(
                lambda line: line.state == "confirmed"
            )
            rejected_approvals = request.approval_matrix_line_ids.filtered(
                lambda line: line.state == "rejected"
            )
            if len(confrimed_approvals.ids) == len(
                request.approval_matrix_id.approval_matrix_ids.ids
            ):
                request.approve_state()
            elif rejected_approvals:
                request.reject_state()

    def action_open_fedback_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'student.leave.feedback.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Reject Reason",
            'target': 'new',
            'context':{'default_student_leave_request_id': self.id},
        }

    def action_approve_request(self):
        self.approve_state()

    
    @api.depends('school_id')
    def _compute_branch_id(self):
        for rec in self:
            rec.branch_id = rec.school_id.branch_id.id

    @api.onchange('standard_id')
    def _onchange_intake_pic(self):
        pic_name = self.standard_id.user_id
        self.pic_intake = pic_name

    @api.onchange('group_class')
    def _onchange_class_pic(self):
        pic_name = self.group_class.pic
        self.pic_class = pic_name

    @api.onchange("student_id")
    def onchange_student(self):
        group_class = self.env['group.class'].search([('student_ids', '=', self.student_id.id)])
        """Method to get standard and roll no of student selected"""
        if self.student_id:
            self.standard_id = self.student_id.standard_id.id
            self.roll_no = self.student_id.roll_no
            self.school_id = self.student_id.school_id.id
            self.program_id = self.student_id.program_id.id
            self.group_class = group_class.id
            self.teacher_id = self.student_id.standard_id.user_id.id or False

    def _update_student_vals(self, vals):
        student_rec = self.env["student.student"].browse(
            vals.get("student_id")
        )
        vals.update(
            {
                "roll_no": student_rec.roll_no,
                "standard_id": student_rec.standard_id.id,
                "school_id": student_rec.school_id.id,
                "program_id": student_rec.program_id.id,
                "teacher_id": student_rec.standard_id.user_id.id,
            }
        )
        return vals

    def approve_state(self):
        res = super(StudentleaveRequest, self).approve_state()
        domain = [
            ('class_date', '>=', self.start_date),
            ('class_date', '<=', self.end_date),
        ]

        if self.subject_id:
            domain.append(('subject_id', '=', self.subject_id.id))
        
        class_id = self.env['ems.classes'].search(domain)
        student_id = class_id.ems_classes_line.filtered(lambda x: x.student_id.id == self.student_id.id)

        if student_id:
            student_id.write({
                'is_absent': True,
                'remark': self.reason,
            })
        return res
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("company_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("branch_id", "in", context.get("allowed_branch_ids")),
                ("branch_id", "=", False),
            ]

        result = super(StudentleaveRequest, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain.extend([("company_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("branch_id", "in", context.get("allowed_branch_ids")),
                    ("branch_id", "=", False),
                ]
            )
        return super(StudentleaveRequest, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )


class StudentPassTracker(models.Model):
    _name = "student.pass.tracker"
    _description = "Student Pass Tracker"
    _rec_name = "student_name"

    @api.model
    def _domain_school_id(self):
        allowed_branch_ids = self.env.branches.ids
        return [("school_branch_ids", "in", allowed_branch_ids)]

    student_name = fields.Many2one('student.student', string='Student Name')
    source_document = fields.Char(string='Source Document')
    student_pass_form = fields.Binary(string='Student Pass Form')
    sola_id = fields.Char(string='Sola ID')
    sp_request_status = fields.Char(string='Student Pass Request Status')
    appeal_form = fields.Binary(string='Appeal Form (If needed)')
    fin_number = fields.Char(string='FIN Number')
    stp_expiry_date = fields.Date(string='STP Expiry Date', default=fields.Date.context_today)
    sp_digital = fields.Binary(string='Student Pass Digital')
    sp_eForm = fields.Binary(string='Student Pass e-Form')
    ipa = fields.Binary(string='In-Principle Approval (IPA)')
    transfer_student = fields.Selection(selection=[
                            ('yes', 'Yes'),
                            ('no', 'No')
                        ], string='Transfer Student', default='no')
    school = fields.Many2one('school.school', string='School', domain=_domain_school_id)
    appointment_date = fields.Date(string='e-Appointment Date', default=fields.Date.context_today)
    med_checkup_form = fields.Binary(string='Medical Check Up Form')
    med_checkup_result = fields.Binary(string='Medical Check Up Result')
    med_checkup_date = fields.Date(string='Medical Check Up Date', default=fields.Date.context_today)

    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("school.company_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("school.school_branch_ids", "in", context.get("allowed_branch_ids")),
                ("school.school_branch_ids", "=", False),
            ]

        result = super(StudentPassTracker, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain.extend([("school.company_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("school.school_branch_ids", "in", context.get("allowed_branch_ids")),
                    ("school.school_branch_ids", "=", False),
                ]
            )
        return super(StudentPassTracker, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )