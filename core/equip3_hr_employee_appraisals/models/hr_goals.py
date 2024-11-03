# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import statistics
from lxml import etree

class HrGoals(models.Model):
    _name = 'hr.goals'
    _description = 'HR Goals'

    def get_applicable_to_selection(self):
        context = self._context
        division_goals = self.env.ref('equip3_hr_employee_appraisals.hr_goal_types_division')
        team_goals = self.env.ref('equip3_hr_employee_appraisals.hr_goal_types_my_team')
        if context.get('default_goal_types_id') == division_goals.id:
            result = [('by_division', 'By Division'),
                    ('by_job_position', 'By Job Position'),
                    ('by_team', 'By Team'),
                    ('by_employee', 'By Employee')]
        elif context.get('default_goal_types_id') == team_goals.id:
            result = [('by_job_position', 'By Job Position'),
                    ('by_team', 'By Team'),
                    ('by_employee', 'By Employee')]
        else:
            result = [('by_company', 'By Company'),
                    ('by_division', 'By Division'),
                    ('by_job_position', 'By Job Position'),
                    ('by_team', 'By Team'),
                    ('by_employee', 'By Employee')]
        return result

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    name = fields.Char('Goal Title', required=True)
    allowed_goals_parent_ids = fields.Many2many('hr.goals', string="Allowed Goals Parent", compute="_compute_allowed_goals_parent")
    goals_parent_id = fields.Many2one('hr.goals', string="Goals Parent", domain="[('id', 'in', allowed_goals_parent_ids)]")
    key_result_area_parent_id = fields.Many2one('hr.key.result', string="Key Result Area")
    goal_types_id = fields.Many2one('hr.goal.types', string='Goal Types')
    goal_types_name = fields.Char(related='goal_types_id.name')
    goal_types_domain_ids = fields.Many2many('hr.goal.types',compute="_compute_goal_types_domain")
    applicable_to = fields.Selection(selection= lambda self: self.get_applicable_to_selection(), string='Applicable To')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    division_ids = fields.Many2many('hr.department', string='Division', domain=_multi_company_domain)
    job_position_ids = fields.Many2many('hr.job', string='Job Position', domain=_multi_company_domain)
    teams_ids = fields.Many2many('hr.teams', string='Teams', domain=_multi_company_domain)
    employee_ids = fields.Many2many('hr.employee', string='Employees', domain=_multi_company_domain)
    evaluation_period_id = fields.Many2one('performance.date.range', string='Evaluation Period', domain=_multi_company_domain)
    weightage = fields.Float('Weightage')
    formula = fields.Selection([('none','None'), ('average','Average'), ('sum','Sum'), ('max','Max'),
                                ('min','Min'), ('median','Median')], default='none', string='Formula')
    achievement_score = fields.Float('Achievement Score')
    achievement_score_shadow = fields.Float('Achievement Score Shadow', compute="_compute_achievement_score_shadow")
    description = fields.Text('Description')
    is_self_service = fields.Boolean(compute='_compute_is_self_service')
    state = fields.Selection([('draft', 'Draft'), ('submitted', 'Submitted')], default='draft', string='Stages')
    key_result_area_ids = fields.One2many('hr.key.result', 'goal_title_id', string='Key Result Area')
    assign_employee_ids = fields.Many2many('hr.employee','goal_employee_rel','goal_id','employee_id')
    assign_user_ids = fields.Many2many('res.users','goal_assign_user_rel','goal_id','user_id')
    goal_types_readonly = fields.Boolean(compute='_compute_goal_types_readonly')
    goal_child_ids = fields.One2many('hr.goals.child', 'goals_id', string='Goals Child')
    is_childs = fields.Boolean('Is Childs', compute="_compute_is_childs")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrGoals, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrGoals, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(HrGoals, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        
        if self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_self_service') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager'):
            goal_types_ids = self.env['hr.goal.types'].search([]).filtered(lambda line: self.env.ref('equip3_hr_employee_appraisals.group_hr_appraisal_self_service').id in line.group_ids.ids)
        if self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            goal_types_ids = self.env['hr.goal.types'].search([]).filtered(lambda line: self.env.ref('equip3_hr_employee_appraisals.group_hr_appraisal_manager').id in line.group_ids.ids)
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            goal_types_ids = self.env['hr.goal.types'].search([]).filtered(lambda line: self.env.ref('equip3_hr_employee_appraisals.group_hr_appraisal_administrator').id in line.group_ids.ids)
        
        context = self._context
        goal_types_id = 0
        if context.get('default_goal_types_id'):
            goal_types_id = int(context.get('default_goal_types_id'))

        if goal_types_id in goal_types_ids.ids:
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'true')
            root.set('delete', 'false')
            res['arch'] = etree.tostring(root)
        return res
    
    @api.depends('goal_types_id')
    def _compute_allowed_goals_parent(self):
        for record in self:
            company_goals = self.env.ref('equip3_hr_employee_appraisals.hr_goal_types_company')
            division_goals = self.env.ref('equip3_hr_employee_appraisals.hr_goal_types_division')
            team_goals = self.env.ref('equip3_hr_employee_appraisals.hr_goal_types_my_team')
            if record.goal_types_id == division_goals:
                type_ids = [company_goals.id,division_goals.id]
                allowed_goals_parent = self.env['hr.goals'].search([]).filtered(lambda line: self.env.user.id in line.assign_user_ids.ids and line.goal_types_id.id in type_ids)
            elif record.goal_types_id == team_goals:
                type_ids = [company_goals.id,division_goals.id,team_goals.id]
                allowed_goals_parent = self.env['hr.goals'].search([]).filtered(lambda line: self.env.user.id in line.assign_user_ids.ids and line.goal_types_id.id in type_ids)
            else:
                allowed_goals_parent = self.env['hr.goals'].search([]).filtered(lambda line: self.env.user.id in line.assign_user_ids.ids)
            record.allowed_goals_parent_ids = [(6, 0, allowed_goals_parent.ids)]

    @api.depends('company_id')
    def _compute_is_self_service(self):
        for record in self:
            if self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_self_service') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager'):
                record.is_self_service = True
            else:
                record.is_self_service = False

    @api.depends('company_id')
    def _compute_goal_types_domain(self):
        for record in self:
            ids = []
            if self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_self_service') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager'):
                group_ids = self.env['hr.goal.types'].search([]).filtered(lambda line: self.env.ref('equip3_hr_employee_appraisals.group_hr_appraisal_self_service').id in line.group_ids.ids)
            if self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
                group_ids = self.env['hr.goal.types'].search([]).filtered(lambda line: self.env.ref('equip3_hr_employee_appraisals.group_hr_appraisal_manager').id in line.group_ids.ids)
            if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
                group_ids = self.env['hr.goal.types'].search([]).filtered(lambda line: self.env.ref('equip3_hr_employee_appraisals.group_hr_appraisal_administrator').id in line.group_ids.ids) 
            if group_ids:
                data_id = [data.id for data in group_ids]
                ids.extend(data_id)
                record.goal_types_domain_ids = [(6,0,ids)]
            else:
                record.goal_types_domain_ids = False
    
    @api.onchange('is_self_service','goal_types_id')
    def onchange_is_self_service(self):
        for rec in self:
            if rec.is_self_service or rec.goal_types_id.name == 'Employee Goals':
                rec.applicable_to = 'by_employee'
                employee = self.env['hr.employee'].search([('user_id','=',self.env.user.id)],limit=1)
                if employee:
                    rec.employee_ids = [(6,0,[employee.id])]

    @api.depends('goal_types_id')
    def _compute_goal_types_readonly(self):
        for rec in self:
            if rec.goal_types_id.name == 'Employee Goals':
                rec.goal_types_readonly = True
            else:
                rec.goal_types_readonly = False

    def action_submit(self):
        for rec in self:
            ids = []
            user_ids = []
            if rec.applicable_to == 'by_company':
                emp_obj = self.env['hr.employee'].search([('company_id','=',rec.company_id.id)])
            if rec.applicable_to == 'by_division':
                emp_obj = self.env['hr.employee'].search([('department_id','in',rec.division_ids.ids)])
            if rec.applicable_to == 'by_job_position':
                emp_obj = self.env['hr.employee'].search([('job_id','in',rec.job_position_ids.ids)])
            if rec.applicable_to == 'by_team':
                team_obj = self.env['hr.teams'].search([('id','in',rec.teams_ids.ids)])
                teams = []
                for data in team_obj:
                    for team in data.team_member_ids:
                        teams.append(team.id)
                emp_obj = self.env['hr.employee'].search([('id','in',teams)])
            if rec.applicable_to == 'by_employee':
                emp_obj = self.env['hr.employee'].search([('id','in',rec.employee_ids.ids)])
            if emp_obj:
                data_id = [data.id for data in emp_obj]
                ids.extend(data_id)
                rec.assign_employee_ids = [(6,0,ids)]

                data_user_id = []
                for user in emp_obj:
                    if user.user_id:
                        data_user_id.append(user.user_id.id)
                user_ids.extend(data_user_id)
                rec.assign_user_ids = [(6,0,user_ids)]
            else:
                rec.assign_employee_ids = False
                rec.assign_user_ids = False
            rec.state = 'submitted'

            if rec.goals_parent_id:
                child_vals = {
                            'goals_child_id': rec.id,
                            'goal_types_id': rec.goal_types_id.id,
                            'goal_title': rec.name,
                            'key_result_area_id': rec.key_result_area_parent_id.id,
                            'create_by': rec.create_uid.id,
                            'achievement_score': rec.achievement_score, 
                            'weightage': rec.weightage,
                            }
                rec.goals_parent_id.write({'goal_child_ids': [(0,0, child_vals)]})
                goal_child = rec.goals_parent_id.mapped("goal_child_ids").filtered(lambda r: r.key_result_area_id == rec.key_result_area_parent_id)
                sum_score = sum(goal_child.mapped("score"))
                goal_child_count = len(goal_child)
                # final_score = sum_score / goal_child_count
                rec.key_result_area_parent_id.write({'actual': sum_score})

                sum_data = sum(rec.goals_parent_id.key_result_area_ids.mapped("achievement"))

                data_achievement = []
                for data in rec.goals_parent_id.key_result_area_ids:
                    data_achievement.append(data.achievement)
                    
                if rec.goals_parent_id.formula == 'average':
                    count = len(rec.goals_parent_id.key_result_area_ids)
                    rec.goals_parent_id.achievement_score = sum_data / count if count > 0 else 0
                elif rec.goals_parent_id.formula == 'sum':
                    rec.goals_parent_id.achievement_score = sum_data
                elif rec.goals_parent_id.formula == 'max':
                    rec.goals_parent_id.achievement_score = max(data_achievement)
                elif rec.goals_parent_id.formula == 'min':
                    rec.goals_parent_id.achievement_score = min(data_achievement)
                elif rec.goals_parent_id.formula == 'median':
                    rec.goals_parent_id.achievement_score = statistics.median(data_achievement)
                else:
                    continue
    
                parents = self.get_parent_goal(rec)
                for parent in parents:
                    parent_obj = self.env['hr.goals'].search([('id','=',parent)])
                    for rec in parent_obj:
                        if rec.goals_parent_id:
                            child = self.env['hr.goals.child'].search([('goals_id','=',rec.goals_parent_id.id),('goals_child_id','=',rec.id),('key_result_area_id','=',rec.key_result_area_parent_id.id)], limit=1)
                            child.write({'achievement_score': rec.achievement_score})
                            goal_child = rec.goals_parent_id.mapped("goal_child_ids").filtered(lambda r: r.key_result_area_id == rec.key_result_area_parent_id)
                            sum_score = sum(goal_child.mapped("score"))
                            rec.key_result_area_parent_id.write({'actual': sum_score})

                            sum_data = sum(rec.goals_parent_id.key_result_area_ids.mapped("achievement"))

                            data_achievement = []
                            for data in rec.goals_parent_id.key_result_area_ids:
                                data_achievement.append(data.achievement)
                                
                            if rec.goals_parent_id.formula == 'average':
                                count = len(rec.goals_parent_id.key_result_area_ids)
                                rec.goals_parent_id.achievement_score = sum_data / count if count > 0 else 0
                            elif rec.goals_parent_id.formula == 'sum':
                                rec.goals_parent_id.achievement_score = sum_data
                            elif rec.goals_parent_id.formula == 'max':
                                rec.goals_parent_id.achievement_score = max(data_achievement)
                            elif rec.goals_parent_id.formula == 'min':
                                rec.goals_parent_id.achievement_score = min(data_achievement)
                            elif rec.goals_parent_id.formula == 'median':
                                rec.goals_parent_id.achievement_score = statistics.median(data_achievement)
                            else:
                                continue
            goal_types_employee = self.env.ref('equip3_hr_employee_appraisals.hr_goal_types_employee')
            if rec.goal_types_id == goal_types_employee:
                my_evaluation = self.env['employee.performance'].search([('date_range_id','=',rec.evaluation_period_id.id),('is_evaluation_okr','=',True),('employee_id','in',rec.assign_employee_ids.ids)],limit=1)
                if my_evaluation:
                    my_evaluation.write({
                        'okr_line_ids': [(0, 0, {
                            'goals_id': rec.id,
                            'goals_parent_id': rec.goals_parent_id.id,
                            'achievement_score': rec.achievement_score,})]
                    })
                    okr_count = len(my_evaluation.okr_line_ids)
                    weightage = 100 / okr_count if okr_count > 0 else 0
                    for okr_line in my_evaluation.okr_line_ids:
                        okr_line.weightage = weightage
    
    @api.depends('formula','key_result_area_ids','key_result_area_ids.achievement')
    def _compute_achievement_score_shadow(self):
        for rec in self:
            sum_data = sum(rec.key_result_area_ids.mapped("achievement"))

            data_achievement = []
            for data in rec.key_result_area_ids:
                data_achievement.append(data.achievement)
                
            if rec.formula == 'average':
                count = len(rec.key_result_area_ids)
                rec.achievement_score_shadow = sum_data / count if count > 0 else 0
            elif rec.formula == 'sum':
                rec.achievement_score_shadow = sum_data
            elif rec.formula == 'max':
                rec.achievement_score_shadow = max(data_achievement)
            elif rec.formula == 'min':
                rec.achievement_score_shadow = min(data_achievement)
            elif rec.formula == 'median':
                rec.achievement_score_shadow = statistics.median(data_achievement)
            else:
                rec.achievement_score_shadow = 0
    
    @api.onchange('formula','achievement_score_shadow')
    def onchange_achievement_score_shadow(self):
        for rec in self:
            if not rec.formula:
                continue
            rec.achievement_score = rec.achievement_score_shadow
    
    @api.onchange('goals_parent_id')
    def onchange_goals_parent(self):
        for rec in self:
            if rec.goals_parent_id:
                rec.evaluation_period_id = rec.goals_parent_id.evaluation_period_id.id
                rec.formula = rec.goals_parent_id.formula

    def action_goals_child(self):
        search_view_id = self.env.ref('equip3_hr_employee_appraisals.hr_goals_child_filter').id
        goals_child = self.env['hr.goals.child'].sudo().search([('goals_id','=',self.id)])
        goals_child_ids = []
        for data in goals_child:
            goals_child_ids.append(data.id)
        if goals_child_ids:
            value = {
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'hr.goals.child',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'name': _('Goals Child'),
                'search_view_id':search_view_id,
                'domain': [('id', 'in', goals_child_ids)],
                'context': {'search_default_group_key_result_area': 1},
            }
            return value
    
    def get_parent_goal(self, goal):
        parent_goal = []
        goals = goal
        while goals.goals_parent_id:
            parent_goal.append(goals.goals_parent_id.id)
            goals = goals.goals_parent_id
        return parent_goal

    @api.depends('goal_child_ids')
    def _compute_is_childs(self):
        for rec in self:
            if rec.goal_child_ids:
                rec.is_childs = False
            else:
                rec.is_childs = True

class HrGoalsChild(models.Model):
    _name = 'hr.goals.child'
    _description = 'HR Goals Child'

    goals_id = fields.Many2one('hr.goals', string="Goals")
    goals_child_id = fields.Many2one('hr.goals', string="Goals Child")
    key_result_area_id = fields.Many2one('hr.key.result', string="Key Result Area")
    goal_types_id = fields.Many2one('hr.goal.types', string='Goal Type')
    goal_title = fields.Char('Goal Title')
    create_by = fields.Many2one('res.users', string="Create By")
    achievement_score = fields.Float('Achievement Score')
    weightage = fields.Float('Weightage')
    score = fields.Float('Score', compute="compute_score", store=True)

    @api.depends('achievement_score','weightage')
    def compute_score(self):
        for rec in self:
            goals_child = self.env['hr.goals.child'].search([('key_result_area_id','=',rec.key_result_area_id.id)])
            if goals_child:
                total_weightage = 0
                for val in goals_child:
                    total_weightage += val.weightage
            else:
                total_weightage = 1
            rec.score = (rec.achievement_score * rec.weightage) / total_weightage if total_weightage > 0 else 0