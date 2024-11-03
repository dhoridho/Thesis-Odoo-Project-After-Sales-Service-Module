# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from ...equip3_general_features.models.approval_matrix import approvalMatrix,approvalMatrixUser
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam
from datetime import date

class PerformancePlanning(models.Model):
    _name = 'performance.planning'
    _order = "create_date desc"

    def _default_employee(self):
        return self.env.user.employee_id

    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee',default=_default_employee)
    period_id = fields.Many2one('performance.date.range', string='Period', domain="[('company_id','=',company_id)]")
    date_start = fields.Date(string="Start Date", related='period_id.date_start')
    date_end = fields.Date(string="End Date", related='period_id.date_end')
    deadline = fields.Date(string="Deadline", related='period_id.deadline')
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    performance_ids = fields.One2many('employee.performance', 'performance_planning_id', string='Performance', readonly=True,
                               states={'draft': [('readonly', False)]})
    approval_matrix_ids = fields.Many2many('performance.matrix.line','planning_id')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', index=True, readonly=True, copy=False, default='draft')
    user_approval_ids = fields.Many2many('res.users',compute="_is_hide_approve")
    is_hide_reject = fields.Boolean(default=True,compute='_get_is_hide')
    is_hide_approve = fields.Boolean(default=True,compute='_get_is_hide')
    domain_employee_ids = fields.Many2many('hr.employee',compute='_compute_domain_employee_ids')
    is_period_task_challenge = fields.Boolean('')
    is_hide_task_challenge = fields.Boolean(default=True)
    is_email_sent = fields.Boolean(default=False)
    is_wa_sent = fields.Boolean(default=False)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(PerformancePlanning, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(PerformancePlanning, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def get_auto_follow_up_self_evaluation(self):
        send_by_email = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_appraisals.send_by_email')
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_appraisals.send_by_wa')
        today = date.today()
        request_approved = self.search([('state', '=', 'approved')])
        today - date.today()

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu_id = self.env['ir.model.data'].get_object_reference(
            'employee_performance', 'menu_my_performance_emp')[1]
        action_id = self.env['ir.model.data'].get_object_reference(
            'employee_performance', 'action_my_employee_performance')[1]

        if send_by_email:
            template_id = self.env.ref(
                'equip3_hr_employee_appraisals.mail_template_appraisals_self_evaluation',
                raise_if_not_found=False
            )
            context = self.env.context = dict(self.env.context)
            if request_approved:
                for rec in request_approved:
                    if today >= rec.date_start and today <= rec.deadline and not rec.is_email_sent:
                        for performance_id in rec.performance_ids:
                            employee_performance = self.env['employee.performance'].search([('id', '=', performance_id.id)])
                            for emp in employee_performance:
                                # for line in employee_performance:
                                url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(emp.id) + "&view_type=form&model=employee.performance&menu_id=" + str(
                                menu_id) + "&action=" + str(action_id)
                                context.update({
                                    'email_to': emp.employee_id.work_email,
                                    'employee_name': emp.employee_id.name,
                                    'url': url,
                                })
                                print(context)
                                template_id.send_mail(rec.id, force_send=False)
                                template_id.with_context(context)
                                emp.action_sent_feedback()
                                rec.is_email_sent = True

        if send_by_wa:
            template= self.env.ref('equip3_hr_employee_appraisals.wa_template_self_evaluation')
            wa_sender = waParam()
            if request_approved:
                for rec in request_approved:
                    if today >= rec.date_start and today <= rec.deadline and not rec.is_wa_sent:
                        for performance_id in rec.performance_ids:
                            employee_performance = self.env['employee.performance'].search([('id', '=', performance_id.id)])
                            for emp in employee_performance:
                                # for line in employee_performance:
                                url = base_url + "/web?db=" + str(self._cr.dbname) + "#id=" + str(emp.id) + "&view_type=form&model=employee.performance&menu_id=" + str(
                                menu_id) + "&action=" + str(action_id)
                                wa_string = str(template.message)
                                phone_num = str(emp.employee_id.mobile_phone)

                                if "${employee_name}" in wa_string:
                                    wa_string = wa_string.replace("${employee_name}", emp.employee_id.name)
                                if "${url}" in wa_string:
                                    wa_string = wa_string.replace("${url}", url)
                                if "+" in phone_num:
                                    phone_num = int(phone_num.replace("+", ""))
                                
                                wa_sender.set_wa_string(wa_string,template._name,template_id=template)
                                wa_sender.send_wa(phone_num)
                                rec.is_wa_sent = True

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft']:
                raise Warning("You can delete Performance Planning only state Draft.")
            return super(PerformancePlanning, rec).unlink()

    @api.depends('employee_id')
    def _compute_domain_employee_ids(self):
        for record in self:
            employee_ids = []
            if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
                my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
                if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(my_employee.id)
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
                    record.domain_employee_ids = [(6,0,employee_ids)]
                else:
                    record.domain_employee_ids = False
            else:
                my_employee = self.env['hr.employee'].sudo().search([('company_id','in',self.env.company.ids)])
                record.domain_employee_ids = my_employee.ids
            
    
    def custom_menu(self):
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            return {
                'type': 'ir.actions.act_window',
                'name': 'Performance Planning',
                'res_model': 'performance.planning',
                'view_mode': 'tree,form',
                'domain':[('employee_id','=',self.env.user.employee_id.id)]
                }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Performance Planning',
                'res_model': 'performance.planning',
                'view_mode': 'tree,form'
                }
    
    
    @api.depends('approval_matrix_ids')
    def _is_hide_approve(self):
        for record in self:
            approval = approvalMatrixUser(record)
            approval.get_approval_user()
            
    @api.depends('user_approval_ids')
    def _get_is_hide(self):
        for record in self:
            if not record.user_approval_ids or record.state != 'submitted':
                record.is_hide_approve = True
                record.is_hide_reject = True
            else:
                record.is_hide_approve = False
                record.is_hide_reject = False
    
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            if record.employee_id:
                approval_matrix = approvalMatrix('hr.appraisals.approval.matrix',record,'equip3_hr_employee_appraisals.appraisal_type_approval','equip3_hr_employee_appraisals.appraisal_level')
                apply = [{'apply_to':"""[('apply_to','=','by_employee')]""",
                                            'filter':"""lambda line:record.employee_id.id in line.employee_ids.ids""",
                                                'order':"""'create_date desc'""",
                                                'limit':1
                                            
                                            },
                        
                        {'apply_to':"""[('apply_to','=','by_job_position')]""",
                                            'filter':"""lambda line: record.employee_id.job_id.id in line.job_ids.ids""",
                                            'order':"""'create_date desc'""",
                                            'limit':1
                                            
                                            },
                        {'apply_to':"""[('apply_to','=','by_department')]""",
                                            'filter':"""lambda line: record.employee_id.department_id.id in line.department_ids.ids""",
                                            'order':"""'create_date desc'""",
                                            'limit':1
                                            
                                            }
                        ]
                
                approval_matrix.set_apply_to(apply)
                approval_matrix.get_approval_matrix(is_approver_by_type=True)
        
    @api.onchange('employee_ids')
    def _ochange_employee(self):
        for record in self:
            if record.employee_ids.filtered(lambda line: not line.user_id):
                employee_ids = record.employee_ids.filtered(lambda line: not line.user_id)
                name_list = [f"-{data.name}" for data in employee_ids]
                name_str = "\n".join(name_list)
                if employee_ids:
                    raise ValidationError(f"The following employees do not have users: \n {name_str}")
  
                    

    def action_confirm(self):
        for record in self:
            if not record.employee_ids:
                raise UserError(_("You must select employee(s)."))
            record.write({'state': 'submitted'})

    def action_generate(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'performance.approve.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_performance_id':self.id,'default_state':'approved'},
        }
        
        
    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'performance.approve.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name':"Confirmation Message",
            'target': 'new',
            'context':{'default_performance_id':self.id,'default_state':'rejected'},
        }
        # for record in self:
        #     performances = self.env['employee.performance']
        #     for employee in record.employee_ids:
        #         if not employee.job_id.template_id.id:
        #             raise UserError(_("You must select Performance(s) in Job Position '%s' first.") % employee.job_id.name)

        #         if not employee.job_id.comp_template_id.id:
        #             raise UserError(_("You must select Competencie(s) in Job Position '%s' first.") % employee.job_id.name)

        #         if employee.job_id.template_id:
        #             performance_lines = []
        #             performance_ids = employee.job_id.template_id.key_performance_ids
        #             for line in performance_ids:
        #                 performance_lines.append((0, 0, {'name': line.name.id,
        #                                 'description': line.description,
        #                                 'weightage': line.weightage,
        #                                 'key_id': line.key_id.id,
        #                                 'sequence': line.sequence,
        #                                 'kpi_target':line.kpi_target
        #                                 }))

        #         if employee.job_id.comp_template_id:
        #             competencies_lines = []
        #             competencies_ids = employee.job_id.comp_template_id.competencies_ids
        #             for line in competencies_ids:
        #                 competencies_lines.append((0, 0, {'name': line.name.id,
        #                                 'description': line.description,
        #                                 'key_id': line.key_id.id,
        #                                 'sequence': line.sequence,
        #                                 'weightage':line.weightage,
        #                                 'target_score_id':line.target_score_id.id,
        #                                 }))
        #         res = {
        #             'performance_planning_id': record.id,
        #             'employee_id': employee.id,
        #             'manager_id': employee.parent_id.id or False,
        #             'template_id': employee.job_id.template_id.id,
        #             'comp_template_id': employee.job_id.comp_template_id.id,
        #             'date_range_id': record.period_id.id,
        #             'date_start': record.date_start,
        #             'date_end': record.date_end,
        #             'deadline': record.deadline,
        #             'performances_line_ids': performance_lines,
        #             'competencies_line_ids': competencies_lines,
        #         }
        #         performances += self.env['employee.performance'].create(res)
        #     performances.action_sent_employee()
        #     record.write({'state': 'approved'})

    # @api.model
    # def _domain_employee_ids(self):
    #     domain = []
    #     if self.period_id:
    #         period = self.search([('period_id', '=', self.period_id.id)])
    #         if period:
    #             for pf_planning in period:
    #                 for emp in pf_planning.employee_ids:
    #                     domain.append((emp.id))
    #     return domain

    # @api.onchange('period_id')
    # def _onchange_period_id(self):
    #     domain = self._domain_employee_ids()
    #     return {'domain': {'employee_ids': [('id', '!=', domain)]}}

    @api.constrains('employee_ids')
    def _constrains_employee(self):
        for record in self:
            period = self.search([('id', '!=', record.id), ('period_id', '=', record.period_id.id),
                                  ('employee_ids', 'in', record.employee_ids.ids)])
            if period:
                raise ValidationError(
                    "There are employees that are present in other Performance Plans with the same period!")
    
    @api.onchange('period_id')
    def onchange_period_id(self):
        for rec in self:
            line_task_challenge = rec.period_id.performance_line_ids.filtered(lambda line:line.component == 'task_challenges')
            if line_task_challenge:
                rec.is_period_task_challenge = True
            else:
                rec.is_period_task_challenge = False
    
    def action_set_task(self):
        for record in self:
            for rec in record.performance_ids:
                if not rec.employee_id.job_id.task_challenge_id:
                    raise UserError(_("You must select Task/Challenges in Job Position '%s' first.") % rec.employee_id.job_id.name)
                line_task_challenge = record.period_id.performance_line_ids.filtered(lambda line:line.component == 'task_challenges')
                if line_task_challenge:
                    rec.is_period_task_challenge = True
                    rec.period_task_challenge_weightage = line_task_challenge.weight
                if rec.employee_id.job_id.task_challenge_id:
                    task_challenge_lines = []
                    task_challenge_ids = rec.employee_id.job_id.task_challenge_id.line_ids
                    for line in task_challenge_ids:
                        task_challenge_lines.append((0, 0, {'task_challenge_id': line.task_challenge_id.id,
                                        'target_score': line.target_score,
                                        'weightage': line.weightage
                                        }))
                    rec.task_challenge_line_ids = [(5, 0, 0)]
                    rec.task_challenge_line_ids = task_challenge_lines
                    template_id = self.env.ref('equip3_hr_employee_appraisals.mail_template_task_challenge', raise_if_not_found=False)
                    for task in rec.task_challenge_line_ids:
                        survey_task = self.env['survey.invite'].create(
                            {'survey_id': task.task_challenge_id.id,
                            'emails': str(rec.employee_id.work_email), 'template_id': template_id.id})
                        context = self.env.context = dict(self.env.context)
                        url_task_challenge = survey_task.survey_start_url + f"?surveyId={task.task_challenge_id.id}&performanceId={rec.id}&email={rec.employee_id.work_email}"
                        context.update({
                            'email_to': rec.employee_id.work_email,
                            'employee_name': rec.employee_id.name,
                            'url_task_challenge': url_task_challenge,
                            'title': task.task_challenge_id.title
                        })
                        template_id.send_mail(rec.id, force_send=False)
                        template_id.with_context(context)
            record.is_hide_task_challenge = True
            
class equip3PerformanceApprovalMatrix(models.Model):
    _name = 'performance.matrix.line'
    _description="Performance Approval Matrix"
    planning_id = fields.Many2one('performance.planning')
    sequence = fields.Integer()
    approver_id = fields.Many2many('res.users',string="Approvers")
    approver_confirm = fields.Many2many('res.users','performance_line_user_approve_ids','user_id',string="Approvers confirm")
    approval_status = fields.Text()
    timestamp = fields.Text()
    feedback = fields.Text()
    minimum_approver = fields.Integer(default=1)
    is_approve = fields.Boolean(string="Is Approve", default=False)
