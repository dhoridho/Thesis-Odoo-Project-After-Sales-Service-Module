from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError, Warning

class SchoolStandard(models.Model):
    _name = 'school.standard'
    _inherit = ["school.standard", "mail.thread", "mail.activity.mixin"]
    _description = "Intake"
    _order = "create_date desc"

    @api.model
    def _domainSchool(self):
        allowed_branch_ids = self.env.branches.ids
        return [("school_branch_ids", "in", allowed_branch_ids)]

    school_id = fields.Many2one('school.school', string="School", domain=_domainSchool)
    name = fields.Char(track_visibility='onchange')
    user_id = fields.Many2one(string="PIC", track_visibility='onchange')
    syllabus_ids = fields.One2many(compute="_compute_syllabus_ids", store=True)
    year = fields.Many2one('academic.year', string='Academic Year', domain="[('month_ids', '=', term_id)]")
    related_term_ids = fields.Many2many(related='standard_id.academic_month_ids')
    term_id = fields.Many2one('academic.month', string="Term")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End date", related="term_id.date_stop")
    division_id = fields.Many2one(required=False)
    medium_id = fields.Many2one(required=False)
    course_id = fields.Many2one('subject.subject', string="Course", domain="[('program_id', '=', standard_id)]", required=False)
    classroom_id = fields.Many2one('class.room', string="ClassRoom", related="course_id.classroom_id")
    related_program_ids = fields.One2many('standard.standard', string='Program', related='school_id.school_program_ids')
    start_year = fields.Char(string="Start Year")
    fees_ids = fields.Many2one('student.fees.structure', string='Fees Structure', related='standard_id.fees_ids')
    status = fields.Selection([('active', 'Active'), ('unactive', 'Unactive'), ('fail', 'Fail'), ('pass', 'Pass')],'Status')
    intake_id = fields.Many2one('school.standard', string="Intake", required=False)
    program_id = fields.Many2one('standard.standard', string="Program", required=False)
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
    done_student_ids = fields.Many2many('student.student', compute='_compute_done_student')
    intake_student_line_ids = fields.One2many('intake.student.line', 'intake_id', string='Intake Student Line')
    intake_subject_line_ids = fields.One2many('intake.subject.line', 'intake_id', string='Intake Subject Line')
    branch_id = fields.Many2one(comodel_name='res.branch', readonly=False, store=True, compute='_compute_branch_id')
    branch_ids = fields.One2many(
        comodel_name="res.branch",
        related="school_id.school_branch_ids",
        string="Branch"
    )
    active = fields.Boolean(default=True, help="Activate/Deactivate Intake")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("cmp_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("branch_ids", "in", context.get("allowed_branch_ids")),
                ("branch_ids", "=", False),
            ]

        result = super(SchoolStandard, self).search_read(
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
            domain.extend([("cmp_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("branch_ids", "in", context.get("allowed_branch_ids")),
                    ("branch_ids", "=", False),
                ]
            )
        return super(SchoolStandard, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )

    @api.depends('school_id')
    def _compute_branch_id(self):
        for rec in self:
            rec.branch_id = rec.school_id.branch_id.id

    @api.depends('subject_ids')
    def _compute_syllabus_ids(self):
        for rec in self:
            data = [(5, 0, 0)]
            for subject in rec.subject_ids:
                data.append((0, 0, {
                    'subject_id' : subject._origin.id,
                    'syllabus_doc': subject.syllabus,
                    'file_name': subject.file_name,
                }))
            rec.syllabus_ids = data

    @api.model
    def create(self, vals):
        res = super(SchoolStandard, self).create(vals)
        if vals.get('ems_subject_ids'):
            res.update_tracking_subject()
            res.update_group_class()
        return res

    def write(self, vals):
        if vals.get('user_id'):
            for record in self:
                record.user_id.standard_id = False
        res = super(SchoolStandard, self).write(vals)
        if vals.get('user_id'):
            for record in self:
                record.user_id.standard_id = record.id
        if vals.get('ems_subject_ids'):
            self.update_tracking_subject()
            self.update_group_class()
        return res

    def update_tracking_subject(self):
        for record in self:
            academic_tracking_ids = self.env['academic.tracking'].search([
                ('intake_ids.intake_id', 'in', record.ids),
            ])
            for tracking in academic_tracking_ids:
                if tracking.intake_ids.filtered(lambda r: r.status == 'active' and r.intake_id.id == record.id):
                    tracking.all_subject_ids.filtered(lambda r: r.intake_id.id == record.id).unlink()
                    tracking.all_subject_ids = [(0, 0, {
                        'intake_id': record.id,
                        'year': subject.year,
                        'subject_id': subject.subject_id and subject.subject_id.id or False,
                        'subject_type': subject.subject_type,
                        'year_id': subject.year_id and subject.year_id.id or False,
                        'term_id': subject.term_id and subject.term_id.id or False
                    }) for subject in record.intake_subject_line_ids]
                    tracking.current_subject_ids.unlink()
                    tracking.current_subject_ids = [(0, 0, {
                        'intake_id': record.id,
                        'year': subject.year,
                        'subject_id': subject.subject_id and subject.subject_id.id or False,
                        'subject_type': subject.subject_type,
                        'year_id': subject.year_id and subject.year_id.id or False,
                        'term_id': subject.term_id and subject.term_id.id or False
                    }) for subject in record.intake_subject_line_ids]

    def update_group_class(self):
        for record in self:
            group_class_ids = self.env['group.class'].search([
                ('intake', 'in', record.ids),
            ])
            for tracking in group_class_ids:
                if tracking.intake.filtered(lambda r: r.id == record.id):
                    # tracking.notebook_ems_subject_ids.filtered(lambda r: r.group_class_tracking_id.id == record.id).unlink()
                    for delete_records in tracking.notebook_ems_subject_ids:
                        delete_records.unlink()
                    for subject in record.intake_subject_line_ids:
                        dummy_data = [(0, 0, {
                                        'intake_id': record.id,
                                        'year': subject.year,
                                        'subject_id': subject.subject_id and subject.subject_id.id or False,
                                        'subject_type': subject.subject_type,
                                        'year_id': subject.year_id and subject.year_id.id or False,
                                        'term_id': subject.term_id and subject.term_id.id or False
                        })]
                        tracking.notebook_ems_subject_ids = dummy_data

    def action_admisson_register(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Admisson Register'),
            'res_model': 'student.student',
            'view_mode': 'tree,form',
            'domain': [('standard_id', '=', self.id)],
            'context': {},
            "target": "current",
        }

    def action_classes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Classes'),
            'res_model': 'ems.classes',
            'view_mode': 'tree,form',
            'domain': [('intake_id', '=', self.id)],
            'context': {},
            "target": "current",
        }

    def action_group_class(self):
        return{
            'type': 'ir.actions.act_window',
            'name': _('Group Class'),
            'res_model': 'group.class',
            'view_mode': 'tree,form',
            'domain': [('intake', '=', self.id)],
            'context': {},
            "target": "current",
        }

    def button_generate_group_class(self):
        if self.intake_student_line_ids:
            group_class = len(self.intake_student_line_ids.group_class_id)
            if group_class > 0:
                raise ValidationError("Group Class generated.")
        return{
            'type': 'ir.actions.act_window',
            'name': 'Generate Classes Wizard',
            'res_model': 'generate.group.class.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
        }

    @api.onchange('start_date')
    def onchange_start_date(self):
        start_year = False
        if self.start_date:
            start_year = self.start_date.strftime("%Y")
        self.start_year = start_year

    @api.onchange('standard_id')
    def _onchange_standard_id(self):
        self.intake_subject_line_ids = [(5, 0, 0)]
        data = []
        if self.standard_id and self.standard_id.program_subject_ids:
            for line in self.standard_id.program_subject_ids:
                data.append((0, 0, {
                    'subject_id': line.subject_id or False,
                    'subject_type': line.subject_type,
                }))
        self.intake_subject_line_ids = data

    # @api.constrains('school_id', 'standard_id')
    # def _check_existing_data(self):
    #     for record in self:
    #         if record.school_id and record.standard_id:
    #             school_id = self.search([('school_id', '=', record.school_id.id),
    #                           ('id', '!=', record.id),
    #                           ('standard_id', '=', record.standard_id.id)], limit=1)
    #             if school_id:
    #                 raise ValidationError("Intake already exists.")

    @api.constrains('standard_id', 'division_id')
    def check_standard_unique(self):
        """Method to check unique standard."""
        pass
        # standard_search = self.env['school.standard'].search([
        #                         ('standard_id', '=', self.standard_id.id),
        #                         ('division_id', '=', self.division_id.id),
        #                         ('school_id', '=', self.school_id.id),
        #                         ('id', 'not in', self.ids)])
        # if standard_search:
        #     raise ValidationError(_("Division and class should be unique!"))
    def name_get(self):
        '''Method to display standard and division'''
        return [(rec.id, rec.name) for rec in self]

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        recs = self.browse()
        if not recs:
            recs = self.search([('name', operator, name)] + args, limit=limit)
        return recs.name_get()

    @api.onchange('school_id', 'standard_id')
    def onchange_combine(self):
        '''Onchange to assign name respective of it's school and program'''
        self.name = self.name

    @api.depends('standard_id', 'school_id', 'division_id', 'medium_id', 'student_ids.state')
    def _compute_done_student(self):
        '''Compute student of done state'''
        student_obj = self.env['student.student']
        for rec in self:
            student_ids = student_obj.search([('standard_id', '=', rec.id), ('school_id', '=', rec.school_id.id), ('division_id', '=', rec.division_id.id), ('medium_id', '=', rec.medium_id.id), ('state', '=', 'done')])
            for student_id in student_ids:
                intake_student_id = self.env['intake.student.line'].search([('intake_id', '=', rec.id), ('student_id', '=', student_id.id)])
                if not intake_student_id:
                    # not created yet, create one
                    self.env['intake.student.line'].create({
                        'intake_id': rec.id,
                        'student_id': student_id.id,
                    })
                elif len(intake_student_id) > 1:
                    # created, delete.
                    intake_student_id.unlink()
            rec.done_student_ids = student_ids

    @api.model
    def set_dashboard_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'dashboard'),
            ('parent_id', '=', self.env.ref('school.menu_ems').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-accounting-account-dashboard'})

    @api.model
    def set_school_configuration_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'School Flow'),
            ('parent_id', '=', self.env.ref('school.menu_ems').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-flow'})

    @api.model
    def set_class_configuration_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'Class Flow'),
            ('parent_id', '=', self.env.ref('school.menu_ems').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-flow'})

    @api.model
    def set_ems_flow_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'EMS Flow'),
            ('parent_id', '=', self.env.ref('school.menu_ems').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-flow'})

    @api.model
    def set_school_announcement_icon(self):
        menu_id = self.env['ir.ui.menu'].search([
            ('name', 'ilike', 'Announcements'),
            ('parent_id', '=', self.env.ref('school.menu_ems').id)
        ], limit=1)
        if menu_id:
            menu_id.write({'equip_icon_class': 'o-hm-sidebar-main-announcement-announcement'})

class IntakeStudentLine(models.Model):
    _name = 'intake.student.line'

    intake_id = fields.Many2one('school.standard', string='Intake')
    student_id = fields.Many2one('student.student', string='Student', required=True)
    group_class_id = fields.Many2one('group.class', string='Group Class')

class ModuleName(models.Model):
    _name = 'intake.subject.line'

    intake_id = fields.Many2one('school.standard', string='Intake')
    program_id = fields.Many2one('standard.standard', string="Program", related='intake_id.standard_id')
    related_subject_ids = fields.Many2many('subject.subject', compute='_compute_related_subject_ids')
    year = fields.Char(string="Year")
    subject_id = fields.Many2one('subject.subject', string="Subject")
    subject_type = fields.Selection([('core', 'Core'), ('elective', 'Elective')], string='Subject Type', compute='_compute_subject_type')
    year_id = fields.Many2one("academic.year", string="Academic Year")
    term_id = fields.Many2one("academic.month", string="Term", domain="[('year_id', '=', year_id)]")

    @api.depends('program_id')
    def _compute_related_subject_ids(self):
        for rec in self:
            rec.related_subject_ids = self.env['program.subject.line'].search([('program_id', '=', rec.program_id.id)]).mapped('subject_id')

    @api.depends('subject_id')
    def _compute_subject_type(self):
        for rec in self:
            subject_id = self.env['program.subject.line'].search([('program_id', '=', rec.program_id.id), ('subject_id', '=', rec.subject_id.id)], limit=1)
            rec.subject_type = subject_id.subject_type
