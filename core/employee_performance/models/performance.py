# -*- coding: utf-8 -*-
import logging
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo import tools
_logger = logging.getLogger(__name__)

class AddEmployees(models.TransientModel):
    _name = 'add.employees'
    _description = 'Generate Performance Evaluation records'

    date_range_id = fields.Many2one('performance.date.range', string='Period', required=True)
    employee_ids = fields.Many2many('hr.employee', 'employee_performance_group_class_rel', 'performance_id', 'employee_id', string='Employees')
    date_start = fields.Date(string="Start Date", related='date_range_id.date_start')
    date_end = fields.Date(string="End Date", related='date_range_id.date_end')

    def compute_sheet(self):
        [data] = self.read()
        if not data['employee_ids']:
            raise UserError(_("You must select employee(s) to generate evaluation(s)."))
        # Add 1 day.
        for employee in self.employee_ids:
            performance_id = self.env['employee.performance'].create({
                'employee_id':employee.id,
                'date_range_id':self.date_range_id.id,
            })
            performance_id.onchange_employee_id()
            performance_id.onchange_template_id()
            performance_id.onchange_comp_template_id()

class PerformanceDateRange(models.Model):
    _name = "performance.date.range"
    _description = "Performance Date Range"

    name = fields.Char(required=True,string="Name")
    date_start = fields.Date(string='Start date', required=True)
    date_end = fields.Date(string='End date', required=True)

class HrJob(models.Model):
    _inherit = 'hr.job'
    _description = 'HR Job'

    template_id = fields.Many2one('performance.template', string='Template ID')
    comp_template_id = fields.Many2one('competencies.template', string='Competencies Template')

class EmployeePerformance(models.Model):
    _name = 'employee.performance'
    _description = 'Employee Performance'
    # _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    name = fields.Char(string='Name', default='New')
    company_id = fields.Many2one(string="Current Company", comodel_name='res.company', default=_get_current_company)
    employee_id = fields.Many2one('hr.employee', required=True)
    template_id = fields.Many2one('performance.template', string='Key Performance Template')
    comp_template_id = fields.Many2one('competencies.template', string='Competencies Template')
    competencies_ids = fields.One2many('key.competencies', 'performance_id', string='Key Performance')
    key_performance_ids = fields.One2many('key.performance', 'performance_id', string='COMPETENCIES')
    date_range_id = fields.Many2one('performance.date.range', string='Period')
    date_start = fields.Date(string="Start Date", related='date_range_id.date_start')
    date_end = fields.Date(string="End Date", related='date_range_id.date_end')
    state = fields.Selection([('draft', 'Draft'), ('sent_to_employee', 'Sent To Employee'),('sent_to_manager', 'Sent To Manager'), ('done', 'Done'),('cancel', 'Cancel')],
                             string='Status', required=True,
                             copy=False, default='draft')
    planning = fields.Char(string="PLANNING AND ORGANIZING:",default="Draws a detailed and comprehensive plan before starting an important task/projec Develops clear and realistic plans follows up and revisits status as task proceeds Is able to manage multiple competing & important activities effectively", readonly=True)
    planning_text = fields.Text(string='Comments')
    planning_score = fields.Float(string='Score')
    leadership = fields.Char(string="Leadership",default="Works co-operatively & effectively with team members within and outside the group Takes ownership of job, situations & results Is able to establish & share a clear vision and influence team to achieve it Is able to coach, mentor, guide & motivate own & extended teams to achieve results", readonly=True)
    leadership_text = fields.Text(string='Comments')
    leadership_score = fields.Float(string='Score')

    accountability = fields.Char(string="ACCOUNTABILITY",default="Accepts responsibility for own actions & decisions & demonstrates commitment to accomplish work in an ethical, efficient and cost-effective manner Establishes priorities, monitors progress and makes effective recommendation", readonly=True)
    accountability_text = fields.Text(string='Comments')
    accountability_score = fields.Float(string='Score')

    innovation = fields.Char(string="INNOVATION",default="Anticipates organizational needs, identifies and acts upon new opportunities to enhance results / minimize problems Offers creative suggestions for improvement & develops new approaches to work", readonly=True)
    innovation_text = fields.Text(string='Comments')
    innovation_score = fields.Float(string='Score')

    collaboration = fields.Char(string="COLLABORATION",default="Builds rapport and goodwill with Principals/Vendors/Customers/Internal teams Acts beyond required or expected effort and proactively originates results Is resourceful and develops healthy inter department relationships to ensure work effectiveness", readonly=True)
    collaboration_text = fields.Text(string='Comments')
    collaboration_score = fields.Float(string='Score')

    job_skill = fields.Float(string='Job Knowledge	')
    handle_skill = fields.Float(string='Work handling skills')
    learn_skill = fields.Float(string='Learn new skill')
    one_time = fields.Float(string='Completion on time')
    pressure = fields.Float(string='handling work pressure')
    portfolio = fields.Float(string='handling new portfolio')
    achievement = fields.Text(string='Achievement')
    improvement = fields.Text(string='improvement')
    development = fields.Text(string='development')
    deadline_end = fields.Boolean(string='development')
    deadline = fields.Date(string='Deadline')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('employee.performance')
        return super(EmployeePerformance, self).create(vals)

    def action_done(self):
        self.write({'state':'done'})

    def action_cancel(self):
        self.write({'state':'cancel'})

    def action_draft(self):
        self.write({'state':'draft'})

    def action_sent_employee(self):
        self.write({'state':'sent_to_employee'})

    def action_sent_manager(self):
        self.write({'state':'sent_to_manager'})

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.template_id = self.employee_id.job_id.template_id.id
            self.comp_template_id = self.employee_id.job_id.comp_template_id.id

    @api.onchange('template_id')
    def onchange_template_id(self):
        if self.template_id:
            key_lines = []
            key_performance_ids = self.template_id.key_performance_ids
            for line in key_performance_ids:
                key_lines.append(line.copy())
            self.key_performance_ids = [(6, 0, [x.id for x in key_lines])]

    @api.onchange('comp_template_id')
    def onchange_comp_template_id(self):
        if self.comp_template_id:
            key_lines = []
            competencies_ids = self.comp_template_id.competencies_ids
            for line in competencies_ids:
                key_lines.append(line.copy())
            self.competencies_ids = [(6, 0, [x.id for x in key_lines])]

class PerformanceTemplate(models.Model):
    _name = 'performance.template'
    _description = 'Employee Performance Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    company_id = fields.Many2one(string="Current Company", comodel_name='res.company', default=_get_current_company)
    name = fields.Char('Name', required=True)
    key_performance_ids = fields.One2many('key.performance', 'key_id', string='Key Performance')

class KeyPerformance(models.Model):
    _name = 'key.performance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Key Performance'

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    company_id = fields.Many2one(string="Current Company", comodel_name='res.company', default=_get_current_company)
    name = fields.Char('KEY PERFORMANCE AREAS', required=True)
    description = fields.Char('Description')
    hint = fields.Char('Hint')
    weightage = fields.Integer('WEIGHTAGE')
    key_id = fields.Many2one('performance.template', 'Template',  copy=False)
    employee_rate = fields.Integer('Employee Self-Assessment')
    employee_remark = fields.Char('Employee Remarks')
    manager_rate = fields.Integer('Manager Rating')
    manager_remark = fields.Char('Manager Remarks')
    performance_id = fields.Many2one('employee.performance', 'Performance Evaluation')
    comment = fields.Char(string="Comment")
    sequence = fields.Integer(string='Sequence', default=10)
    state = fields.Selection([('draft', 'Draft'), ('sent_to_employee', 'Sent To Employee'),('sent_to_manager', 'Sent To Manager'), ('done', 'Done'),('cancel', 'Cancel')],
                             'Status', tracking=True, required=True,
                             copy=False, default='draft')
    employee_id = fields.Many2one('hr.employee', 'Employee', related='performance_id.employee_id')

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")

class CompetenciesTemplate(models.Model):
    _name = 'competencies.template'
    _description = 'Employee Competencies Template'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    company_id = fields.Many2one(string="Current Company", comodel_name='res.company', default=_get_current_company)
    name = fields.Char('Name', required=True)
    competencies_ids = fields.One2many('key.competencies', 'key_id', string='Key Performance')

class KeyCompetencies(models.Model):
    _name = 'key.competencies'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Key Competencies'

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    company_id = fields.Many2one(string="Current Company", comodel_name='res.company', default=_get_current_company)
    name = fields.Char('KEY PERFORMANCE AREAS', required=True)
    description = fields.Char('Description')
    key_id = fields.Many2one('competencies.template', 'Template Name', copy=False)
    performance_id = fields.Many2one('employee.performance', 'Performance Evaluation')
    comment = fields.Char(string="Comment")
    sequence = fields.Integer(string='Sequence', default=10)
    score = fields.Float('Score')
    employee_id = fields.Many2one('hr.employee', 'Employee', related='performance_id.employee_id')

    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")
    state = fields.Selection(tracking=True, copy=False, related='performance_id.state')



class ReportKeyPerformance(models.Model):
    _name = "report.key.performance"
    _description = "Performance"
    _auto = False

    create_date = fields.Datetime('Creation Date', readonly=True)
    performance_id = fields.Many2one('employee.performance', 'Performance', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    date_range_id = fields.Many2one('performance.date.range', 'Period')
    weightage = fields.Float('Weightage')
    employee_rate = fields.Float(
        'Employee Rate', required=True)
    manager_rate = fields.Float(
        'Manager Rate', required=True)
    template_id = fields.Many2one('performance.template', 'Evaluation Template')
    key_performance_id = fields.Many2one('key.performance', 'Key performance')

    def _select(self):
        return """
            SELECT
                performance.id AS id,                
                performance.id AS key_performance_id,                
                ep.id AS performance_id,
                employee.id AS employee_id,  
                dr.id AS date_range_id,                             
                pt.id AS template_id,                             
                performance.weightage AS weightage,
                performance.employee_rate AS employee_rate,
                performance.manager_rate AS manager_rate,
                ep.create_date AS create_date
            """

    def _from(self):
        return """
            FROM
                employee_performance ep
                JOIN key_performance performance ON ep.id = performance.performance_id
                JOIN performance_date_range dr ON dr.id = ep.date_range_id
                JOIN hr_employee employee ON ep.employee_id = employee.id
                JOIN performance_template pt ON pt.id = ep.template_id
            """

    def _group_by(self):
        return """
            GROUP BY
                performance.id,                            
                employee.id,
                dr.id,
                pt.id,
                ep.create_date,
                ep.id
            """

    def _order_by(self):
        return """
            ORDER BY
                employee_id
            """

    def _where(self):
        return """
            WHERE
                performance.display_type = 'False' AND performance.id IS NOT NULL
            """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            "CREATE or REPLACE VIEW %s as (%s %s %s %s)" % (
                self._table, self._select(), self._from(),self._group_by(), self._order_by()
            )
        )

class ReportCompetencies(models.Model):
    _name = "report.competencies"
    _description = "Competencies Report"
    _auto = False

    create_date = fields.Datetime('Creation Date', readonly=True)
    performance_id = fields.Many2one('employee.performance', 'Performance', required=True)
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    date_range_id = fields.Many2one('performance.date.range', 'Period')
    employee_rate = fields.Float(
        'Score', required=True)
    template_id = fields.Many2one('competencies.template', 'Evaluation Template')
    key_performance_id = fields.Many2one('key.competencies', 'Competencies')

    def _select(self):
        return """
            SELECT
                performance.id AS id,   
                performance.id AS key_performance_id,                             
                ep.id AS performance_id,
                employee.id AS employee_id,  
                dr.id AS date_range_id,                             
                pt.id AS template_id,                             
                performance.score AS employee_rate,
                ep.create_date AS create_date
            """

    def _from(self):
        return """
            FROM
                employee_performance ep
                JOIN key_competencies performance ON ep.id = performance.performance_id
                JOIN performance_date_range dr ON dr.id = ep.date_range_id
                JOIN hr_employee employee ON ep.employee_id = employee.id
                JOIN competencies_template pt ON pt.id = ep.comp_template_id
            """

    def _group_by(self):
        return """
            GROUP BY
                performance.id,                            
                employee.id,
                dr.id,
                pt.id,
                ep.create_date,
                ep.id
            """

    def _order_by(self):
        return """
            ORDER BY
                employee_id
            """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            "CREATE or REPLACE VIEW %s as (%s %s %s %s)" % (
                self._table, self._select(), self._from(), self._group_by(), self._order_by()
            )
        )