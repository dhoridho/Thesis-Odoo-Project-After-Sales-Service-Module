from odoo import api, fields, models
from odoo.exceptions import ValidationError
from lxml import etree


class TrainingHistories(models.Model):
    _name = 'training.histories'
    _description = 'Training Histories'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('training.histories') or 'New'
        return super(TrainingHistories, self).create(vals)

    def _compute_training_required(self):
        for rec in self:
            if rec.course_ids in rec.job_id.course_ids:
                rec.training_required = 'yes'
            elif rec.created_by_model == 'by_employee_competencies_line':
                rec.training_required = 'yes'
            else:
                rec.training_required = 'no'
            if rec.state != 'expired':
                rec.update_state()
            else:
                rec.state = rec.state

    def _compute_training_context(self):
        for rec in self:
            if rec.created_by_model == 'by_request':
                rec.training_context = 'requested_training'
            elif rec.created_by_model == 'by_employee_competencies_line':
                rec.training_context = 'underperformance'
            elif rec.course_ids in rec.job_id.course_ids:
                rec.training_context = 'employee_onboarding'
            else:
                rec.training_context = 'requested_training'
            
    def update_state(self):
        for rec in self:
            if not rec.stage_course_id.stage_id:
                rec.state = 'to_do'
            elif rec.stage_course_id.stage_id.name == 'Approved' or rec.stage_course_id.stage_id.name == 'On Progress':
                rec.state = 'on_progress'
            elif rec.training_conduct_line_id.status == 'Success':
                rec.state = 'success'
            elif rec.training_conduct_line_id.status == 'Failed':
                rec.state = 'failed'
            if rec.training_conduct_line_id and not rec.training_conduct_line_id.attended:
                rec.state = 'not_attended'
            
            for conduct in rec.training_conduct_id:
                for conduct_line in rec.training_conduct_line_id:
                    emp_tpl = self.env['employee.training.plan.line'].search([
                            ('employee_id', '=', conduct_line.employee_id.id),
                            ('course_ids', '=', conduct.course_id.id)
                    ])

                    if emp_tpl:
                        for emp in emp_tpl.course_ids:
                            if emp.id == conduct.course_id.id:
                                emp_tpl.status = rec.state

    # def required_update(self):
    #     for rec in self:
    #         print ('ttttttttttttttt')
    #         if rec.course_ids in rec.job_id.course_ids:
    #             print ('ddddddddddddd')
    #             rec.training_required = 'yes'
    #         else:
    #             print ('qqqqqqqqqqqqqqqqqq')
    #             rec.training_required = 'no'

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    name = fields.Char(string='Name')
    employee_id = fields.Many2one('hr.employee', 'Employee', domain=_multi_company_domain)
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id')
    course_ids = fields.Many2many('training.courses', string='Courses')
    state = fields.Selection(
        [('to_do', 'To Do'), ('on_progress', 'On Progress'), ('success', 'Success'), ('failed', 'Failed'),
         ('expired', 'Expired'), ('not_attended', 'Not Attended')], string='State', tracking=True, default='to_do')
    training_required = fields.Selection([('no', 'No'), ('yes', 'Yes')], default='no', string='Training Required', compute='_compute_training_required')
    company_id = fields.Many2one('res.company', string='Company', tracking=True, default=lambda self: self.env.company)
    training_conduct_id = fields.Many2one('training.conduct', string='Training Conduct Origin')
    expiry_date = fields.Date(string='Expiry Date')
    start_date = fields.Date('Date Start', related='training_conduct_id.start_date')
    end_date = fields.Date('Date Completed', related='training_conduct_id.end_date')
    stage_course_id = fields.Many2one('training.courses.stages', related='training_conduct_id.stage_course_id')
    stage_course_domain_ids = fields.Many2many('training.courses.stages',
                                               related='training_conduct_id.stage_course_domain_ids')
    training_conduct_line_id = fields.Many2one('training.conduct.line', string='Training Conduct Line Origin')
    training_req_id = fields.Many2one('training.request', 'Training Request Id')
    created_by_model = fields.Selection([('by_job', 'By Job'), ('by_conduct', 'By Conduct'), ('by_request', 'By Request'), ('by_update_from_conduct', 'By Update from conduct'), ('by_employee_competencies_line', 'By Employee Competencies line')])
    training_context = fields.Selection([('employee_onboarding', 'Employee Onboarding'), ('underperformance', 'Underperformance'), ('requested_training', 'Requested Training')], string='Context', compute='_compute_training_context')
    # performance_id = fields.Many2one('employee.performance', 'Performance Evaluation', ondelete="cascade")
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(TrainingHistories, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(TrainingHistories, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def custom_menu(self):
        # search_view_id = self.env.ref("hr_contract.hr_contract_view_search")
        if  self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_training_supervisor') and not self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_reward_warning_hr_manager'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id','=',self.env.user.id)])
            if my_employee:
                for child_record in my_employee.child_ids:
                    employee_ids.append(my_employee.id)
                    employee_ids.append(child_record.id)
                    child_record._get_amployee_hierarchy(employee_ids,child_record.child_ids,my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Training Histories',
                'res_model': 'training.histories',
                'target':'current',
                'view_mode': 'tree,form',
                'domain': [('employee_id', 'in', employee_ids), ('state', 'not in', ['to_do'])],
                'context':{'search_default_group_employee_id':1},
                'help':"""<p class="o_view_nocontent_smiling_face">
                    Create a new Training 
                </p>"""
                # 'context':{'search_default_current':1, 'search_default_group_by_state': 1},
                # 'search_view_id':search_view_id.id,
                
            }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Training Histories',
                'res_model': 'training.histories',
                'target':'current',
                'view_mode': 'tree,form',
                'domain': [('state', 'not in', ['to_do'])],
                'context':{'search_default_group_employee_id':1,'is_approve_manager':True},
                'help':"""<p class="o_view_nocontent_smiling_face">
                    Create a new Training 
                </p>""",
                # 'context':{'is_approve_manager':True},
                # 'search_view_id':search_view_id.id,
            }

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=True, submenu=True):
        res = super(TrainingHistories, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                             submenu=submenu)
        if self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_training_manager') and not self.env.user.has_group(
                'equip3_hr_employee_access_right_setting.group_hr_training_director'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        elif self.env.user.has_group('equip3_hr_employee_access_right_setting.group_hr_training_director'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'false')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res