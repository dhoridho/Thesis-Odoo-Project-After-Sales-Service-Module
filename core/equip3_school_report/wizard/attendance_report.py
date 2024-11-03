from dataclasses import asdict
from odoo import _, models, fields, api, tools

class AttendanceReport(models.TransientModel):
    _name = 'attendance.report'
    
    intake_id = fields.Many2one('school.standard', string="Intake")
    year_id = fields.Many2one("academic.year", string="Academic Year")
    term_id = fields.Many2one('academic.month', string="Term", domain="[('year_id', '=', year_id)]")
    ems_subject_id = fields.Many2one("subject.weightage", string="Subject", domain="[('program_id', '=', intake_id),('year_id', '=', year_id),('term_id', '=', term_id)]")
    group_class = fields.Many2one('group.class', string='Group Class')
    subject_total_class = fields.Integer(string='Total Attendance', compute='_compute_subject_total_class')
    attendance_report_line = fields.One2many('attendance.report.line', 'attendance_report_id', string='Student Attendance Report Line')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    partner_id = fields.Many2one(comodel_name='res.partner', string="Partner")
    subject_id = fields.Many2one('subject.subject', string='Subject')
    related_subject_ids = fields.Many2many('subject.subject', compute='_compute_related_subject_ids')
    related_group_class_ids = fields.Many2many('group.class', compute='_compute_related_group_class_ids')

    @api.depends('group_class')
    def _compute_related_subject_ids(self):
        for rec in self:
            rec.related_subject_ids = False
            if rec.group_class:
                subject_ids = rec.group_class.subject_ids.mapped('subject_id')
                rec.related_subject_ids = subject_ids
                if self.env.user.has_group('school.group_school_teacher'):
                    teacher = self.env['school.teacher'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
                    if teacher:
                        group_classes = teacher.teacher_group_class_ids.filtered(lambda x: x.group_class_id == rec.group_class)
                        rec.related_subject_ids = group_classes.mapped('subject_id')

    @api.depends('intake_id')
    def _compute_related_group_class_ids(self):
        for rec in self:
            rec.related_group_class_ids = False
            if rec.intake_id:
                group_classes = self.env['group.class'].search([('intake', '=', rec.intake_id.id), ('state', '=', 'validated')])
                rec.related_group_class_ids = group_classes
                if self.env.user.has_group('school.group_school_teacher'):
                    teacher = self.env['school.teacher'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
                    if teacher:
                        rec.related_group_class_ids = group_classes.filtered(lambda x: x in teacher.teacher_group_class_ids.mapped('group_class_id'))

    def action_print_attendance_report(self):
        return self.env.ref('equip3_school_report.attendance_report').report_action(self)

    @api.onchange('ems_subject_id')
    def _onchange_ems_subject_id(self):
        self.attendance_report_line = [(5, 0, 0)] + [(0, 0, {'attendance_report_id': self.id, 'subject_id': self.ems_subject_id.subject_id.id, 'student_id': id}) for id in self.group_class.student_ids.ids]

    @api.depends('ems_subject_id', 'ems_subject_id.subject_id')
    def _compute_subject_total_class(self):
        for record in self:
            subject_total_class = self.env["daily.attendance"].search_count([('subject_id', '=', record.ems_subject_id.subject_id.id)])
            record.subject_total_class = subject_total_class

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

class AttendanceReportLine(models.TransientModel):
    _name = 'attendance.report.line'
    
    attendance_report_id = fields.Many2one('attendance.report', string='Student Attendance Report')
    student_id = fields.Many2one('student.student', string="Student")
    subject_id = fields.Many2one('subject.subject', string="Subject")
    total_attendance = fields.Integer(string='Total Attendance', compute='_compute_total_attendance')
    total_present = fields.Integer(string='Total Present', compute='_compute_total_present')
    total_absent = fields.Integer(string='Total Absent', compute='_compute_total_absent')
    presence_value = fields.Float(string='Presence Value', digits=(16, 2), compute='_compute_presence_value')
    presence_persentage = fields.Integer(string='Presence Percentage', compute='_compute_presence_persentage')

    @api.depends('student_id', 'subject_id')
    def _compute_total_attendance(self):
        for record in self:
            total_attendance = self.env["daily.attendance.line"].search_count([('subject_id', '=', record.subject_id.id),('student_id', '=', record.student_id.id)])
            record.total_attendance = total_attendance
    
    @api.depends('student_id', 'subject_id')
    def _compute_total_present(self):
        for record in self:
            total_present = self.env["daily.attendance.line"].search_count([('subject_id', '=', record.subject_id.id),('student_id', '=', record.student_id.id),('is_present', '=', True)])
            record.total_present = total_present

    @api.depends('student_id', 'subject_id')
    def _compute_total_absent(self):
        for record in self:
            total_absent = self.env["daily.attendance.line"].search_count([('subject_id', '=', record.subject_id.id),('student_id', '=', record.student_id.id),('is_absent', '=', True)])
            record.total_absent = total_absent

    @api.depends('total_attendance', 'total_present')
    def _compute_presence_value(self):
        for record in self:
            if record.total_attendance != 0:
                record.presence_value = record.total_present / record.total_attendance
            else:
                record.presence_value = 0

    @api.depends('presence_value')
    def _compute_presence_persentage(self):
        for record in self:
            if record.presence_value:
                record.presence_persentage = record.presence_value * 100
            else:
                record.presence_persentage = 0