# -*- coding: utf-8 -*-
import werkzeug
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from lxml import etree

class EmployeeOffboarding(models.Model):
    _name = 'employee.offboarding'
    _description = "Employee Offboarding"
    _inherit = 'mail.thread'

    @api.model
    def _default_employee_id(self):
        return self.env.user.employee_id
    
    name = fields.Char(string='Employee Offboarding', readonly=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True,default=_default_employee_id)
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id',
                                    required=True)
    start_date_offboarding = fields.Date('Start Date')
    end_date_offboarding = fields.Date('End Date')
    job_id = fields.Many2one('hr.job', string='Job Title', related='employee_id.job_id',
                             domain="[('department_id', '=', department_id)]")
    responsible_user_id = fields.Many2one('res.users', string='Responsible User')
    parent_id = fields.Many2one('hr.employee', string='Manager', related='employee_id.parent_id')
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                       default=lambda self: self.env.company)
    exit_checklist_id = fields.Many2one('employee.exit.checklist', string='Exit Checklist',
                                     domain="[('department_ids','in', [department_id])]", required=True)
    exit_interview_id = fields.Many2one('survey.survey', string='Exit Interview',
                                     domain="[('survey_type','=','exit_interview')]", required=True)
    note_id = fields.Text('Description')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Canceled'),
        ('complete', 'Completed'),
    ], string='Status', readonly=True, copy=False, index=True, tracking=True, default='draft')
    employee_domain_ids = fields.Many2many('hr.employee',string="Employee Domain",compute='_get_employee_domain_ids')
    exit_checklist_line_ids = fields.One2many('offboarding.exit.checklist', 'emp_offboarding_id', string="Exit Checklist Line")
    exit_interview_line_ids = fields.One2many('offboarding.exit.interview', 'emp_offboarding_id', string="Exit Interview Line")
    scoring_progress_ids = fields.One2many('offboarding.scoring.progress', 'emp_offboarding_id', string='Scoring Progress')
    total_exit_weightage = fields.Float('Total Exit Weightage', compute='_compute_total_exit_weightage', store=True)
    total_current_exit_weight = fields.Float('Current Progress', compute='_compute_total_current_exit_weight')
    document_count = fields.Integer(compute='_document_count', string="Offboarding's Document")
    
    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('employee.offboarding')
        result = super(EmployeeOffboarding, self).create(vals)
        return result
    
    def write(self, vals):
        res = super(EmployeeOffboarding, self).write(vals)
        for rec in self:
            for line in rec.exit_checklist_line_ids:
                emp_checklist = self.env['employee.exit.checklist.line'].search([('line_id','=',line.id),('employee_id','=',rec.employee_id.id)])
                if line.state == 'completed':
                    emp_checklist.check = True
                else:
                    emp_checklist.check = False
            for line in rec.exit_interview_line_ids:
                emp_interview = self.env['employee.exit.interview.line'].search([('line_id','=',line.id),('employee_id','=',rec.employee_id.id)])
                if line.state == 'completed':
                    emp_interview.check = True
                else:
                    emp_interview.check = False
        return res
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeOffboarding, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeOffboarding, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.depends('employee_id')
    def _get_employee_domain_ids(self):
        for record in self:
            if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
                my_employee = self.env['hr.employee'].sudo().search([('user_id','=',self.env.user.id),('company_id','in',self.env.company.ids)])
                employee_ids = []
                if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
                record.employee_domain_ids = employee_ids
            else:
                employee = self.env['hr.employee'].sudo().search([('company_id','in',self.env.company.ids)])
                employee_ids = []
                if employee:
                    for record_employee in employee:
                        employee_ids.append(record_employee.id)
                record.employee_domain_ids = employee_ids
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(EmployeeOffboarding, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        
        if self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_departmen_leader') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res
    
    def custom_menu(self):
        views = [(self.env.ref('equip3_hr_employee_onboarding.view_employee_offboarding_tree').id,'tree'),
                 (self.env.ref('equip3_hr_employee_onboarding.view_employee_offboarding_form').id,'form')]
        search_view_id = self.env.ref('equip3_hr_employee_onboarding.view_employee_offboarding_search').id
        if  self.env.user.has_group('hr.group_hr_user') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_officer'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Offboarding',
                'res_model': 'employee.offboarding',
                'view_mode': 'tree,form',
                'views':views,
                'search_view_id':search_view_id,
                'domain': [('employee_id.user_id', '=', self.env.user.id)]
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Employee Offboarding',
                'res_model': 'employee.offboarding',
                'view_mode': 'tree,form',
                'views':views,
                'search_view_id':search_view_id,
            }
    
    @api.onchange('exit_checklist_id')
    def onchange_exit_checklist(self):
        for rec in self:
            rec.exit_checklist_line_ids = [(5,0,0)]
            exit_checklist = []
            for line in rec.exit_checklist_id.checklist_line_ids:
                exit_checklist.append((0, 0, {'checklist_id': line.id,'document_type': line.document_type,'activity_type': line.activity_type,'responsible_user_id': line.responsible_user_id.id}))
            rec.exit_checklist_line_ids = exit_checklist
    
    @api.onchange('exit_interview_id')
    def onchange_exit_interview(self):
        for rec in self:
            rec.exit_interview_line_ids = [(5,0,0)]
            exit_interview = []
            if rec.exit_interview_id:
                exit_interview.append((0, 0, {'name': rec.exit_interview_id.id}))
            rec.exit_interview_line_ids = exit_interview
    
    @api.onchange('name')
    def _onchange_name(self):
        for rec in self:
            line_list = []
            line_list.append((0,0,{'offboarding_component':"EXIT CHECKLIST"}))
            line_list.append((0,0,{'offboarding_component':"EXIT INTERVIEW"}))
            rec.scoring_progress_ids = line_list
    
    @api.onchange('scoring_progress_ids')
    def _onchange_scoring_progress_ids(self):
        for record in self:
            if record.scoring_progress_ids:
                total = sum([line.offboarding_weightage for line in record.scoring_progress_ids])
                if total > 100:
                    raise ValidationError("Maximum Total Weightage is 100. Please re-enter the value for each component !")
    
    @api.depends('scoring_progress_ids','scoring_progress_ids.offboarding_weightage')
    def _compute_total_exit_weightage(self):
        for rec in self:
            if rec.scoring_progress_ids:
                total = sum([data.offboarding_weightage for data in rec.scoring_progress_ids])
                rec.total_exit_weightage = total
            else:
                rec.total_exit_weightage = 0
    
    @api.depends('scoring_progress_ids','scoring_progress_ids.offboarding_weightage','exit_checklist_line_ids','exit_checklist_line_ids.state','exit_interview_line_ids','exit_interview_line_ids.state')
    def _compute_total_current_exit_weight(self):
        for rec in self:
            total = 0
            if rec.exit_checklist_line_ids:
                checklist_weightage = sum(rec.scoring_progress_ids.filtered(lambda r: r.offboarding_component == 'EXIT CHECKLIST').mapped("offboarding_weightage"))
                checklist_done = len(rec.exit_checklist_line_ids.filtered(lambda r: r.state == 'completed'))
                all_checklist = len(rec.exit_checklist_line_ids)
                component_checklist = (checklist_done/all_checklist) * checklist_weightage
                total += component_checklist
            if rec.exit_interview_line_ids:
                interview_weightage = sum(rec.scoring_progress_ids.filtered(lambda r: r.offboarding_component == 'EXIT INTERVIEW').mapped("offboarding_weightage"))
                interview_done = len(rec.exit_interview_line_ids.filtered(lambda r: r.state == 'completed'))
                all_interview = len(rec.exit_interview_line_ids)
                component_training = (interview_done/all_interview) * interview_weightage
                total += component_training
            rec.total_current_exit_weight = total
            rec.employee_id.offboarding_progress = total

            if rec.total_exit_weightage > 0 and rec.total_current_exit_weight == rec.total_exit_weightage and rec.state == 'confirm':
                rec.write({'state': 'complete'})

    def action_confirm(self):
        if self.employee_id.offboarding_exit_checklist_ids:
            self.employee_id.offboarding_exit_checklist_ids = [(5,0,0)]
        for rec in self.exit_checklist_line_ids:
            if rec.state == 'completed':
                check = True
            else:
                check = False
            self.env['employee.exit.checklist.line'].create({
                'line_id': rec.id,
                'employee_id': self.employee_id.id,
                'name': rec.checklist_id.name,
                'check': check,
            })
        if self.employee_id.offboarding_exit_interview_ids:
            self.employee_id.offboarding_exit_interview_ids = [(5,0,0)]
        for rec in self.exit_interview_line_ids:
            if rec.state == 'completed':
                check = True
            else:
                check = False
            self.env['employee.exit.interview.line'].create({
                'line_id': rec.id,
                'employee_id': self.employee_id.id,
                'name': rec.name.title,
                'check': check,
            })
        self.write({'state': 'confirm'})
    
    def action_cancel(self):
        self.write({'state': 'cancel'})
    
    def action_complete(self):
        self.write({'state': 'complete'})
        checklist_line = self.exit_checklist_line_ids.filtered(lambda r: r.activity_type == 'upload_document' and r.attachment)
        if checklist_line:
            number = 1
            for rec in checklist_line:
                doc_number = self.name + "/" + str(number)
                binary = self.env["ir.attachment"].sudo().search([("res_model", "=", "offboarding.exit.checklist"),("res_id", "=", rec.id),("res_field", "=", "attachment")],limit=1)
                if binary:
                    self.env['hr.employee.document'].create({
                        'offboarding_id': self.id,
                        'name': doc_number,
                        'checklist_document_id': rec.checklist_id.id,
                        'employee_ref': self.employee_id.id,
                        'issue_date': self.end_date_offboarding,
                        'doc_attachment_id': [(4, file.id) for file in binary],
                    })
                    number += 1
    
    def _document_count(self):
        for rec in self:
            document_ids = self.env['hr.employee.document'].sudo().search([('offboarding_id', '=', rec.id)])
            rec.document_count = len(document_ids)
    
    def document_view(self):
        self.ensure_one()
        domain = [
            ('offboarding_id', '=', self.id)]
        return {
            'name': _("Offboarding's Document"),
            'domain': domain,
            'res_model': 'hr.employee.document',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [(self.env.ref('equip3_hr_employee_onboarding.employee_documents_onboarding_tree_view').id, 'tree'), (self.env.ref('equip3_hr_employee_onboarding.employee_document_onboarding_form_view').id, 'form')],
            'help': _('''<p class="oe_view_nocontent_create">
                           Click to Create for New Documents
                        </p>'''),
            'limit': 80,
            'context': "{'default_employee_ref': %s}" % self.employee_id.id
        }

class OffboardingExitChecklist(models.Model):
    _name = 'offboarding.exit.checklist'
    _description = "Offboarding Exit Checklist"

    emp_offboarding_id = fields.Many2one('employee.offboarding', string="Employee Offboarding", ondelete='cascade')
    checklist_id = fields.Many2one('employee.checklists', string="Checklist")
    document_type = fields.Selection([('entry', 'Entry Process'),
                                      ('exit', 'Exit Process')], string='Checklist Type')
    activity_type = fields.Selection([('to_do', 'To Do'),
                                      ('upload_document', 'Upload Document')], string='Activity Type')
    responsible_user_id = fields.Many2one('res.users', string="Responsible User")
    attachment = fields.Binary('Attachment')
    attachment_name = fields.Char('Attachment Name')
    feedback = fields.Text('Feedback')
    state = fields.Selection([('not_completed', 'Not Completed'),
                              ('completed', 'Completed')], default='not_completed', string='Status')

    @api.onchange('attachment')
    def onchange_attachment(self):
        for rec in self:
            if rec.attachment:
                rec.state = 'completed'
            else:
                rec.state = 'not_completed'
    
    def action_done(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'offboarding.exit.checklist.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Mark Done",
            'target': 'new',
            'context':{'default_offboard_exit_checklist_id':self.id},
        }

class OffboardingExitInterview(models.Model):
    _name = 'offboarding.exit.interview'
    _description = "Offboarding Exit Interview"

    emp_offboarding_id = fields.Many2one('employee.offboarding', string="Employee Offboarding", ondelete='cascade')
    name = fields.Many2one('survey.survey', string="Name")
    state = fields.Selection([('pending', 'Pending'),
                              ('in_progress', 'In Progress'),
                              ('completed', 'Completed')], string='Status', default='pending')
    email = fields.Many2one('mail.mail', string="Email")
    email_state = fields.Selection(related='email.state', string="Email Status")
    response_id = fields.Many2one('survey.user_input', "Response", ondelete="set null")
    interview_result_count = fields.Integer("Interview Results", compute='_compute_interview_result')

    def get_url_survey(self):
        self.ensure_one()
        if not self.response_id:
            response = self.name._create_answer(user=self.emp_offboarding_id.employee_id.user_id)
            self.response_id = response.id
        else:
            response = self.response_id
        url = '%s?%s' % (self.name.get_start_url(), werkzeug.urls.url_encode({'answer_token': response and response.access_token or None}))
        return url

    def action_send_to_employee(self):
        for rec in self:
            template_id = self.env.ref('equip3_hr_employee_onboarding.mail_template_exit_interview', raise_if_not_found=False)
            context = self.env.context = dict(self.env.context)
            survey_url = self.get_url_survey()
            context.update({
                'email_from' : rec.emp_offboarding_id.company_id.email,
                'email_to': rec.emp_offboarding_id.employee_id.work_email,
                'employee_name': rec.emp_offboarding_id.employee_id.name,
                'url_interview': survey_url,
                'title': rec.name.title,
            })
            template_id.with_context(context)
            mail_send = template_id.send_mail(rec.emp_offboarding_id.id, force_send=True)
            mail = self.env["mail.mail"].sudo().browse(int(mail_send))
            rec.email = mail
            rec.state = 'in_progress'
    
    def action_resend_survey(self):
        for rec in self:
            template_id = self.env.ref('equip3_hr_employee_onboarding.mail_template_exit_interview', raise_if_not_found=False)
            context = self.env.context = dict(self.env.context)
            survey_url = self.get_url_survey()
            context.update({
                'email_from' : rec.emp_offboarding_id.company_id.email,
                'email_to': rec.emp_offboarding_id.employee_id.work_email,
                'employee_name': rec.emp_offboarding_id.employee_id.name,
                'url_interview': survey_url,
                'title': rec.name.title,
            })
            template_id.with_context(context)
            mail_send = template_id.send_mail(rec.emp_offboarding_id.id, force_send=True)
            mail = self.env["mail.mail"].sudo().browse(int(mail_send))
            rec.email = mail
    
    def _compute_interview_result(self):
        for rec in self:
            if self.response_id:
                interview_result = self.env['survey.user_input'].sudo().search([('access_token','=',self.response_id.access_token),('survey_type','=','EXIT_INTERVIEW'),('state','=','done')])
                if interview_result:
                    rec.interview_result_count = len(interview_result)
                else:
                    rec.interview_result_count = 0
            else:
                rec.interview_result_count = 0

    def action_see_results(self):
        if self.response_id:
            interview_result = self.env['survey.user_input'].sudo().search([('access_token','=',self.response_id.access_token),('survey_type','=','EXIT_INTERVIEW'),('state','=','done')])
            interview_ids = []
            for data in interview_result:
                interview_ids.append(data.id)
            view_id = self.env.ref('survey.survey_user_input_view_form').id
            if interview_ids:
                if len(interview_ids) > 1:
                    value = {
                        'domain': [('id', 'in', interview_ids)],
                        'view_type': 'form',
                        'view_mode': 'tree,form',
                        'res_model': 'survey.user_input',
                        'view_id': False,
                        'type': 'ir.actions.act_window',
                        'name': _('Feedback Results'),
                    }
                else:
                    value = {
                        'view_mode': 'form',
                        'res_model': 'survey.user_input',
                        'view_id': view_id,
                        'type': 'ir.actions.act_window',
                        'name': _('Feedback Results'),
                        'res_id': interview_ids and interview_ids[0]
                    }
                return value
        else:
            return False
    
    def action_done(self):
        for rec in self:
            rec.state = 'completed'
            emp_interview = self.env['employee.exit.interview.line'].search([('line_id','=',rec.id),('employee_id','=',rec.emp_offboarding_id.employee_id.id)])
            if emp_interview:
                emp_interview.check = True

class OffboardingScoringProgress(models.Model):
    _name = 'offboarding.scoring.progress'
    _description = "Offboarding Scoring Progress"

    emp_offboarding_id = fields.Many2one('employee.offboarding', string="Employee Offboarding", ondelete='cascade')
    offboarding_component = fields.Char('Offboarding Component')
    offboarding_weightage = fields.Float('weightage')