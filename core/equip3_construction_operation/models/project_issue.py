from asyncore import read
import base64
from odoo.tools import human_size
from odoo import api, fields, models, _
from datetime import datetime, date , timedelta
from odoo.exceptions import ValidationError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT,DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
import pytz, json, calendar
from lxml import etree


class ProjectIssueInherit(models.Model):
    _name = 'project.issue'
    _inherit = ['project.issue', 'portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _rec_name = 'number'

    @api.model
    def create(self , vals):
        vals['number'] = self.env['ir.sequence'].next_by_code('project.issue.sequence') 
        return super(ProjectIssueInherit, self).create(vals)

    def default_issue_stage_id(self):
        stage = self.env['issue.stage'].search([('name', '=', 'Found')], limit=1)
        return stage.id

    def _default_is_timesheet(self):
        equip3_construction_hr_operation = self.env['ir.module.module'].search(
            [('name', '=', 'equip3_construction_hr_operation')])
        # if construction_hr_operation not installed
        if not equip3_construction_hr_operation or equip3_construction_hr_operation.state != 'installed':
            return False
        # if installed
        else:
            return True
        
    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]
    
   

    number = fields.Char(string='Issue ID', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    active = fields.Boolean(string='Active', default=True)
    contract_id = fields.Many2one('sale.order.const', string="Contract", domain="[('project_id','=', project_id)]")
    description_new = fields.Html(string = 'Description')
    priority = fields.Selection([
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High')
        ], string='Priority', default='low')
    tag_ids = fields.Many2many('project.tags', string = "Tags")
    issue_stage_id = fields.Many2one('issue.stage', group_expand='_read_group_stage_ids', default = default_issue_stage_id, string='Issue Stage')
    issue_stage_name = fields.Char(string='Issue Stage Name', related='issue_stage_id.name', store=True)
    issue_found_date = fields.Datetime(string='Issue Found Date')
    issue_solved_date = fields.Datetime(string='Issue Solved Date')
    attachment_ids= fields.One2many('attachment.issue.file', 'issue')
    timesheet_ids = fields.One2many('project.issue.timesheet', 'issue', 'Timesheets')
    job_order_id = fields.Many2one('project.task', string = 'Job Order', domain="[('project_id','=', project_id), ('sale_order','=', contract_id)]")
    working_hours_to_solve = fields.Float(string="Working Hours to Solve", compute='_compute_working_hours_to_solve', store=True)
    days_since_last_action = fields.Float(string="Days Since The Last Action", compute='_compute_days_since_last_action', store=True)
    days_since_create_date = fields.Float(string="Days Since Creation Date", compute='_compute_days_since_create_date', store=True) 
    days_since_issue_found = fields.Float(string="Days Since Issue Found", compute='_compute_days_since_issue_found', store=True) 
    employee_ids = fields.Many2many('hr.employee', string="Assigned To")
    state = fields.Selection([
        ('found', 'Found'),
        ('in_progress', 'In Progress'),
        ('solved', 'Solved'),
        ('cancelled', 'Cancelled')], string='state', readonly=True, store=True, default='found', compute='_compute_state')
    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, readonly=True,
                                 default=lambda self: self.env.company.id)
    branch_id = fields.Many2one('res.branch', string="Branch", default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, 
                                domain=_domain_branch)
    is_timesheet = fields.Boolean(string="Is Timesheet", compute='_compute_is_timesheet', default=_default_is_timesheet)
    

    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ProjectIssueInherit, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('abs_construction_management.group_construction_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
            
        return res
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if  self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('abs_construction_management.group_construction_manager'):
            domain.append('|')
            domain.append('&')
            domain.append(('project_id','in',self.env.user.project_ids.ids))
            domain.append(('employee_ids.id','in',[self.env.user.employee_id.id]))
            domain.append('&')
            domain.append(('project_id','in',self.env.user.project_ids.ids))
            domain.append(('create_uid','=',self.env.user.id))
        elif self.env.user.has_group('abs_construction_management.group_construction_manager') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id','in',self.env.user.project_ids.ids))
            
        return super(ProjectIssueInherit, self).search_read(domain, fields, offset, limit, order)
    
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        if  self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('abs_construction_management.group_construction_manager'):
            domain.append('|')
            domain.append('&')
            domain.append(('project_id','in',self.env.user.project_ids.ids))
            domain.append(('employee_ids.id','in',[self.env.user.employee_id.id]))
            domain.append('&')
            domain.append(('project_id','in',self.env.user.project_ids.ids))
            domain.append(('create_uid','=',self.env.user.id))
        elif self.env.user.has_group('abs_construction_management.group_construction_manager') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
            domain.append(('project_id','in',self.env.user.project_ids.ids))
        return super(ProjectIssueInherit, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    
    @api.onchange('project_id')
    def _onchange_project_id_branch(self):
        for rec in self:
            project = rec.project_id
            if project:
                rec.branch_id = project.branch_id.id
            else:
                rec.branch_id = False

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if  self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '=', 'progress'), ('company_id', '=', rec.company_id.id)]}
                    }
    
    @api.depends('issue_stage_id')
    def _compute_state(self):
        choices = {
            'Found': 'found',
            'In Progress': 'in_progress',
            'Solved': 'solved',
            'Cancelled': 'cancelled'
        }
        if self.issue_stage_id:
            for record in self:
                record.write({'state': choices[record.issue_stage_id.name]})
    
    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        # perform search
        stage_ids = stages._search([], order=order)
        return stages.browse(stage_ids)
    
    def action_in_progress(self):
        for rec in self:
            stage = self.env['issue.stage'].search([('name', '=', 'In Progress')], limit=1).id
            rec.update({'issue_stage_id': stage})
            rec.write({'state': 'in_progress'})

    def action_solved(self):
        return{             
            'type': 'ir.actions.act_window',
            'name': 'Solved Date',
            'view_mode': 'form', 
            'target': 'new',
            'res_model': 'solve.issue.date',
            'context': {'default_issue_id' : self.id}
        }

    def action_cancel(self):
        for rec in self:
            stage = self.env['issue.stage'].search([('name', '=', 'Cancelled')], limit=1).id
            rec.update({'issue_stage_id': stage})
            rec.write({'state': 'cancelled'})
    
    @api.depends('issue_found_date')
    def _compute_days_since_issue_found(self):
        self.days_since_issue_found = 0
        for rec in self:
            if rec.name and rec.issue_found_date:
                date_differences = relativedelta(datetime.now(pytz.timezone('Asia/Jakarta')).date(), rec.issue_found_date.date())
                years_diff_to_days = date_differences.years*365
                days_diff = date_differences.days + years_diff_to_days
                rec.days_since_issue_found = days_diff

    def _compute_is_timesheet(self):
        for rec in self:
            equip3_construction_hr_operation = self.env['ir.module.module'].search(
                [('name', '=', 'equip3_construction_hr_operation')])
            # if construction_hr_operation not installed
            if not equip3_construction_hr_operation or equip3_construction_hr_operation.state != 'installed':
                rec.is_timesheet = False
            # if installed
            else:
                rec.is_timesheet = True
            
    @api.depends('create_date')
    def _compute_days_since_create_date(self):
        self.days_since_create_date = 0
        for rec in self:
            if rec.name:
                date_now = datetime.now()
                date_differences = relativedelta(date_now, rec.create_date)
                years_diff_to_days = date_differences.years*365
                days_diff = date_differences.days + years_diff_to_days
                rec.days_since_create_date = days_diff
    
    @api.depends('timesheet_ids')
    def _compute_working_hours_to_solve(self):
        self.working_hours_to_solve = 0
        for rec in self:
            if rec.name:
                sum_hours_timesheet = sum([x.unit_amount for x in rec.timesheet_ids])
                rec.working_hours_to_solve = sum_hours_timesheet

    @api.depends('timesheet_ids')
    def _compute_days_since_last_action(self):
        self.days_since_last_action = 0
        for rec in self:
            if rec.name:
                list_date_of_timesheet = [x.date for  x in rec.timesheet_ids]
                if list_date_of_timesheet:
                    latest_date_of_timesheet = max(list_date_of_timesheet)
                    date_differences = relativedelta(datetime.now(pytz.timezone('Asia/Jakarta')).date(), latest_date_of_timesheet)
                    years_diff_to_days = date_differences.years*365
                    days_diff = date_differences.days + years_diff_to_days
                    rec.days_since_last_action = days_diff
                else:
                    rec.days_since_last_action = 0
    
class AttachmentsIssueFile(models.Model):
    _name = 'attachment.issue.file'
    _description = 'Attachments Issue Tab'
    _order = 'sequence'

    issue = fields.Many2one('project.issue', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Datetime(string="Date")
    attachment = fields.Binary(string= 'Attachment', widget='many2many_binary')
    name = fields.Char(string="File Name")
    file_size = fields.Integer(compute='_compute_file_size', string='File Size', store=True)
    size = fields.Char("File Size", compute="_compute_file_size", store=True)
    description = fields.Text(string="Description")

    @api.depends('attachment')
    def _compute_file_size(self):
        for rec in self:
            if rec.attachment:
                file_detail = base64.b64decode(rec.attachment)
                rec.file_size = int(len(file_detail))
                rec.size = human_size(len(file_detail))

    @api.depends('issue.attachment_ids', 'issue.attachment_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.issue.attachment_ids:
                no += 1
                l.sr_no = no


class ProjectIssueTimesheet(models.Model):
    _name = 'project.issue.timesheet'
    _description = 'Project Issue Timesheet'
    _order = 'sequence'

    issue = fields.Many2one('project.issue', ondelete='cascade')
    sequence = fields.Integer(string="Sequence", default=0)
    sr_no = fields.Integer('No.', compute="_sequence_ref")
    date = fields.Date(string="Date")
    name = fields.Char(string="Description")
    employee_id = fields.Many2many('hr.employee', string="Employee")
    unit_amount = fields.Float(string="Duration (Hours)")
    
    @api.constrains('date')
    def _check_date(self):
        for rec in self:
            date_differences = relativedelta(rec.date, rec.issue.issue_found_date.date())
            years_diff_to_days = date_differences.years*365
            days_diff = date_differences.days + years_diff_to_days
            if days_diff < 0:
                raise ValidationError("The timesheet date cannot be less than the date the issue was found")
    
    
    @api.depends('issue.timesheet_ids', 'issue.timesheet_ids.sequence')
    def _sequence_ref(self):
        for line in self:
            no = 0
            line.sr_no = no
            for l in line.issue.timesheet_ids:
                no += 1
                l.sr_no = no
    
     
    @api.onchange('issue')
    def _onchange_issue(self):
        self.ensure_one()
        res={}
        domain = []
        if self.issue:
            list_ids = self.issue.employee_ids
            domain = [("id", "in", [x._origin.id for x in list_ids])]       
        if not domain:
            domain = [("id", "=", False)]
        res['domain'] = {'employee_id' : domain}
        return res
    
    
    @api.model
    def create(self, vals):
        record = super(ProjectIssueTimesheet, self).create(vals)
        for employee in record.employee_id:
            self.env['account.analytic.line'].create({
                "date":record.date,
                "employee_id":employee.id,
                "project_id":record.issue.project_id.id,
                "task_id":record.issue.job_order_id.id,
                "name": record.name,
                "unit_amount": record.unit_amount
                })
        return record
    
    
    def unlink(self):
        record = False
        for rec in self:
            for employee in rec.employee_id:
                self.env['account.analytic.line'].search([
                    ("date", '=', rec.date),
                    ("employee_id", "=", employee.id),
                    ("project_id", "=", rec.issue.project_id.id),
                    ("task_id", "=", rec.issue.job_order_id.id),
                    ("unit_amount", "=", rec.unit_amount)
                    ]).unlink()
            record = super(ProjectIssueTimesheet, rec).unlink()
        return record

    def write(self, vals):
        old_employee = [x.id for x in self.employee_id]
        if 'employee_id' in vals:
            update_vals = vals.copy()
            new_employee = update_vals.pop('employee_id')
            for rec in self.employee_id:
                if rec.id not in new_employee[0][2]:
                    self.env['account.analytic.line'].search([
                        ("date", '=', self.date),
                        ("employee_id", "=", rec.id),
                        ("project_id", "=", self.issue.project_id.id),
                        ("task_id", "=", self.issue.job_order_id.id),
                        ("unit_amount", "=", self.unit_amount)
                        ]).unlink()
                elif rec.id in new_employee[0][2]:
                    self.env['account.analytic.line'].search([
                        ("date", '=', self.date),
                        ("employee_id", "=", rec.id),
                        ("project_id", "=", self.issue.project_id.id),
                        ("task_id", "=", self.issue.job_order_id.id),
                        ("unit_amount", "=", self.unit_amount)
                        ]).write(update_vals)
        else:
            for rec in self.employee_id:
                self.env['account.analytic.line'].search([
                        ("date", '=', self.date),
                        ("employee_id", "=", rec.id),
                        ("project_id", "=", self.issue.project_id.id),
                        ("task_id", "=", self.issue.job_order_id.id),
                        ("unit_amount", "=", self.unit_amount)
                        ]).write(vals)
        record = super(ProjectIssueTimesheet, self).write(vals)
        for employee in self.employee_id:
            if employee.id not in old_employee:
                self.env['account.analytic.line'].create({
                "date": self.date,
                "employee_id":employee.id,
                "project_id":self.issue.project_id.id,
                "task_id":self.issue.job_order_id.id,
                "name": self.name,
                "unit_amount": self.unit_amount
                })
        return record


class ProjectNotesInherit(models.Model):
    _inherit = 'project.notes'
    
    @api.model
    def _domain_user(self):
        return [('company_id','=', self.env.company.id)]

    department_type = fields.Selection(related='project_id.department_type', string='Type of Department')
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, readonly=True,
                                 default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string = 'Responsible Person',domain=_domain_user)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(ProjectNotesInherit, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group('abs_construction_management.group_construction_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
            
        return res
    
    def custom_menu(self):
        if  self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Project Notes',
                'res_model': 'project.notes',
                'view_mode': 'tree,form',
                # 'views':views,
                'domain': [('project_id','in',self.env.user.project_ids.ids),('user_id','=',self.env.user.id),('department_type', '=', 'department')],
                'context':{'default_department_type': 'department'},
                # 'view_id':view_id,
                'help':"""
                <p class="o_view_nocontent_smiling_face">
                    No Project Note found. Let's create one!
                </p>
            """
            }
        elif  self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group('abs_construction_management.group_construction_manager'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Project Notes',
                'res_model': 'project.notes',
                'view_mode': 'tree,form',
                # 'views':views,
                'domain': ['|','&','&',('project_id','in',self.env.user.project_ids.ids),('user_id','=',self.env.user.id),('department_type', '=', 'department'),'&',('project_id','in',self.env.user.project_ids.ids),('create_uid','=',self.env.user.id),('department_type', '=', 'department')],
                'context':{'default_department_type': 'department'},
                # 'view_id':view_id,
                'help':"""
                <p class="o_view_nocontent_smiling_face">
                    No Project Note found. Let's create one!
                </p>
            """
            }
        elif self.env.user.has_group('abs_construction_management.group_construction_manager') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
              return {
                'type': 'ir.actions.act_window',
                'name': 'Project Notes',
                'res_model': 'project.notes',
                'view_mode': 'tree,form',
                # 'views':views,
                'domain': [('project_id','in',self.env.user.project_ids.ids),('department_type', '=', 'department')],
                'context':{'default_department_type': 'department'},
                # 'view_id':view_id,
                'help':"""
                 <p class="o_view_nocontent_smiling_face">
                    No Project Note found. Let's create one!
                </p>
            """
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Project Notes',
                'res_model': 'project.notes',
                'view_mode': 'tree,form',
                # 'views':views,
                'domain': [('department_type', '=', 'department')],
                'context':{'default_department_type': 'department'},
                # 'view_id':view_id,
                'help':"""
                 <p class="o_view_nocontent_smiling_face">
                    No Project Note found. Let's create one!
                </p>
            """
            }
    
    def custom_menu_management(self):
        # views = [(self.env.ref('abs_construction_management.view_project_notes_menu_tree').id,'tree')]
        # search_view_id = self.env.ref("project.view_project_project_filter").id
        # view_id = self.env.ref("abs_construction_management.view_project_notes_menu_tree").id
        # query_paramaters = []
        # query_statement = """
        #     SELECT id FROM job_cost_sheet 
        #     """
        if  self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Project Notes',
                'res_model': 'project.notes',
                'view_mode': 'tree,form',
                # 'views':views,
                'domain': [('project_id','in',self.env.user.project_ids.ids),('user_id','=',self.env.user.id)],
                'context':{'default_department_type': 'project'}
            }
        elif  self.env.user.has_group('equip3_construction_accessright_setting.group_construction_engineer') and not self.env.user.has_group('abs_construction_management.group_construction_manager'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Project Notes',
                'res_model': 'project.notes',
                'view_mode': 'tree,form',
                # 'views':views,
                'domain': ['|','&',('project_id','in',self.env.user.project_ids.ids),('user_id','=',self.env.user.id),'&',('project_id','in',self.env.user.project_ids.ids),('create_uid','=',self.env.user.id)],
                'context':{'default_department_type': 'project'},
      
            }
        elif self.env.user.has_group('abs_construction_management.group_construction_manager') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
              return {
                'type': 'ir.actions.act_window',
                'name': 'Project Notes',
                'res_model': 'project.notes',
                'view_mode': 'tree,form',
                # 'views':views,
                'domain': [('project_id','in',self.env.user.project_ids.ids)],
                'context':{'default_department_type': 'project'},
                # 'view_id':view_id,
            #     'help':"""
            #      <p class="oe_view_nocontent_create">
            #         Create a new project.
            #     </p><p>
            #         Organize your activities (plan tasks, track issues, invoice timesheets) for internal, personal or customer projects.
            #     </p>
            # """
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Project Notes',
                'res_model': 'project.notes',
                'view_mode': 'tree,form',
                # 'views':views,
                'domain': [],
                'context':{'default_department_type': 'project'},
                # 'view_id':view_id,

            }

    @api.onchange('department_type')
    def _onchange_department_type(self):
        for rec in self:
            if  self.env.user.has_group('abs_construction_management.group_construction_user') and not self.env.user.has_group('equip3_construction_accessright_setting.group_construction_director'):
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id),('id','in',self.env.user.project_ids.ids)]}
                    }
            else:
                if rec.department_type == 'project':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'project'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id)]}
                    }
                elif rec.department_type == 'department':
                    return {
                        'domain': {'project_id': [('department_type', '=', 'department'), ('primary_states', '!=', 'cancelled'), ('company_id', '=', rec.company_id.id)]}
                    }