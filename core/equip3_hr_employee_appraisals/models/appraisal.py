# -*- coding: utf-8 -*-
import ast
from email.policy import default
import logging
from odoo import models, fields, api, _
from odoo import tools
from odoo.exceptions import ValidationError
from datetime import date, datetime, timedelta
from pytz import timezone
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT, DEFAULT_SERVER_DATETIME_FORMAT, float_compare
import time
from lxml import etree
from odoo.tools.safe_eval import safe_eval, time
from ...equip3_general_features.models.email_wa_parameter import EmailParam,waParam

_logger = logging.getLogger(__name__)

class EmployeePerformance(models.Model):
    _name = 'employee.performance'
    _inherit = ['employee.performance', 'mail.thread', 'mail.activity.mixin']


    _order = "create_date desc"

    is_period = fields.Boolean(string="is Period", default=False, compute='compute_is_period')
    # state = fields.Selection(
    #     [('draft', 'Draft'), ('sent_to_employee', 'Sent To Employee'), ('sent_to_manager', 'Sent To Manager'),
    #      ('done', 'Approved'), ('cancel', 'Rejected')],
    #     string='Status', track_visibility='onchange', required=True,
    #     copy=False, default='draft')

    job_id = fields.Many2one('hr.job', related='employee_id.job_id')
    department_id = fields.Many2one('hr.department', related='employee_id.department_id')
    appraisal_approver_user_ids = fields.One2many('appraisal.approver.user', 'emp_appraisal_id', string='Approver')
    approvers_ids = fields.Many2many('res.users', 'emp_appraisal_approvers_rel', string='Approvers List')
    approved_user_ids = fields.Many2many('res.users', string='Approved by User')
    is_approver = fields.Boolean(string="Is Approver", compute='_compute_can_approve')
    approved_user_text = fields.Text(string="Approved User", tracking=True)
    approved_user = fields.Text(string="Approved User", tracking=True)
    feedback_parent = fields.Text(string='Parent Feedback')
    template_id = fields.Many2one('performance.template', string='Performances')
    comp_template_id = fields.Many2one('competencies.template', string='Competencies')
    performance_planning_id = fields.Many2one('performance.planning', string='Performance Planning')
    is_employee = fields.Boolean(string="Is Employee", compute='_compute_self_employee')
    performances_line_ids = fields.One2many('employee.performances.line', 'performance_id', string='Performances')
    competencies_line_ids = fields.One2many('employee.competencies.line', 'performance_id', string='Competencies')
    total_score = fields.Integer(compute='_compute_total_score')
    total_target_score = fields.Integer(compute='_compute_total_target_score')
    total_competency_match = fields.Float(compute='_compute_total_competency_match')
    total_competency_gap = fields.Integer(compute='_compute_total_competency_gap')
    total_weightage = fields.Float(compute='_compute_total_weightage')
    total_weightage_performance = fields.Float(compute='_compute_weightage_performance')
    total_weightage_score = fields.Float(compute='_compute_total_weightage_score')
    total_weightage_score_shadow = fields.Float()
    total_weightage_score_performance = fields.Float(compute='_compute_total_weightage_score_performance')
    total_weightage_score_performance_shadow = fields.Float()
    overal_score = fields.Float(compute='_compute_overal_score')
    overal_score_shadow = fields.Float()
    n_grid_id = fields.Many2one('nine.box.matrix')
    n_grid_adjusted_id = fields.Many2one('nine.box.matrix', string="Adjusted Nine Box Grid")
    n_grid_result_id = fields.Many2one('nine.box.matrix', string="Nine Box Grid Result", compute='_compute_nine_box_grid_result', store=True)
    manager_id = fields.Many2one('hr.employee')
    job_id = fields.Many2one('hr.job',related='employee_id.job_id',store=True)
    department_id = fields.Many2one('hr.department', related='employee_id.department_id', store=True)
    is_hide_refresh = fields.Boolean(compute='_compute_is_hide_refresh')
    peer_reviews_line_ids = fields.One2many('employee.peer.reviews.line', 'performance_id', string='Peer Reviews')
    peer_reviews_total_score = fields.Float(string="Weightage Score", compute='_compute_peer_reviews_total_score', store=True)
    peer_reviews_weightage = fields.Float(string="Weightage", compute='_compute_peer_reviews_weightage', store=True)
    feedback_result_count = fields.Integer("Feedback Results", compute='_compute_feedback_result')
    is_sent_feedback = fields.Boolean(string="Is Sent Feedback", default=False)
    training_plan_line_ids = fields.One2many('employee.training.plan.line', 'performance_id', string='Training Plan')
    development_plan_line_ids = fields.One2many('employee.development.plan.line', 'performance_id', string='Development Plan')
    external_reviewer_line_ids = fields.One2many('appraisals.external.reviewer.line', 'performance_id', string='External Reviewer')
    task_challenge_line_ids = fields.One2many('employee.task.challenge.line', 'performance_id', string='Tasks / Challenges')
    task_challenge_weightage_score = fields.Float(string="Weightage Score", compute='_compute_task_challenge_weightage_score', store=True)
    task_challenge_weightage = fields.Float(string="Weightage", compute="_compute_task_challenge_weightage", store=True)
    is_period_performances = fields.Boolean()
    is_period_competencies = fields.Boolean()
    is_period_all_review = fields.Boolean()
    is_period_task_challenge = fields.Boolean()
    period_performance_weightage = fields.Float()
    period_competencies_weightage = fields.Float()
    period_all_review_weightage = fields.Float()
    period_task_challenge_weightage = fields.Float()
    is_included_external_reviewers = fields.Boolean(default=False, compute="_compute_is_included_external_reviewers", store=True)
    okr_line_ids = fields.One2many('employee.evaluation.okr.line', 'performance_id', string='OKR')
    okr_total_weightage = fields.Float(compute='_compute_okr_total_weightage')
    okr_total_score = fields.Float(compute='_compute_okr_total_score')
    is_evaluation_okr = fields.Boolean()
    is_self_type = fields.Boolean()
    is_manager_type = fields.Boolean()
    next_manager_seq = fields.Integer('Next Manager Sequence', compute='_compute_next_manager_seq', store=True)
    max_manager_seq = fields.Integer('Max Manager Sequence')
    next_manager_id = fields.Many2one('res.users', string="Next Manager Assesment", compute='_compute_next_manager', store=True)
    is_submiter = fields.Boolean(compute='_compute_is_submiter')
    is_final_assesment = fields.Boolean(compute='_compute_is_final_assesment')
    manager_sequence_ids = fields.One2many('employee.evaluation.manager.sequence', 'evaluation_id', string='OKR')

    @api.depends('manager_sequence_ids','manager_sequence_ids.is_submit')
    def _compute_next_manager_seq(self):
        for rec in self:
            if rec.manager_sequence_ids:
                next_manager_sequence = sorted(rec.manager_sequence_ids.filtered(lambda r: not r.is_submit), key=lambda r:r.sequence)
                if next_manager_sequence:
                    rec.next_manager_seq = next_manager_sequence[0].sequence
                else:
                    rec.next_manager_seq = next_manager_sequence[0].sequence + 1
            else:
                rec.next_manager_seq = 0
    
    @api.depends('manager_sequence_ids','manager_sequence_ids.manager_id','manager_sequence_ids.is_submit')
    def _compute_next_manager(self):
        for rec in self:
            if rec.manager_sequence_ids:
                next_manager_sequence = sorted(rec.manager_sequence_ids.filtered(lambda r: not r.is_submit), key=lambda r:r.sequence)
                if next_manager_sequence:
                    rec.next_manager_id = next_manager_sequence[0].manager_id
                else:
                    rec.next_manager_id = False
            else:
                rec.next_manager_id = False
    
    def action_manager_submit(self):
        for rec in self:
            for line in rec.manager_sequence_ids:
                next_manager_sequence = line.filtered(lambda r: self.env.user.id == r.manager_id.id and r.sequence == rec.next_manager_seq and not r.is_submit)
                if next_manager_sequence:
                    next_manager_sequence.date = fields.Datetime.now()
                    next_manager_sequence.is_submit = True

    @api.depends('next_manager_id')
    def _compute_is_submiter(self):
        for record in self:
            if self.env.user.id == record.next_manager_id.id:
                record.is_submiter = True
            else:
                record.is_submiter = False

    @api.depends('next_manager_id','next_manager_seq','max_manager_seq')
    def _compute_is_final_assesment(self):
        for record in self:
            if record.next_manager_seq == record.max_manager_seq and self.env.user.id == record.next_manager_id.id:
                record.is_final_assesment = True
            else:
                record.is_final_assesment = False

    @api.depends('n_grid_id','n_grid_adjusted_id')
    def _compute_nine_box_grid_result(self):
        for rec in self:
            if rec.n_grid_adjusted_id:
                rec.n_grid_result_id = rec.n_grid_adjusted_id
            else:
                rec.n_grid_result_id = rec.n_grid_id

    @api.model
    def get_all_employee_performance_analysis(self,domain=[]):
        nine_box_obj = self.env['nine.box.matrix']
        ep_obj = self.env['employee.performance']
        dataresult = {}       

        get_low_box =  nine_box_obj.search([('competency_level','=','low')],limit=3,order='number_analysis desc')
        get_medium_box =  nine_box_obj.search([('competency_level','=','medium')],limit=3,order='number_analysis desc')
        get_high_box =  nine_box_obj.search([('competency_level','=','high')],limit=3,order='number_analysis desc')

        dataresult['low'] = []
        dataresult['medium'] = []
        dataresult['high'] = []
        for low_box in get_low_box:
            check = ep_obj.search(domain+[('n_grid_result_id','=',low_box.id)])
            dataresult['low'].append({
                'id':low_box.id,
                'name':low_box.category,
                'number_analysis':low_box.number_analysis,
                'color':low_box.color or 'white',
                'count':len(check)
                })
        if len(dataresult['low']) < 3:
            re = 3-len(dataresult['low'])
            for c in range(re):
                dataresult['low'].append({
                    'id':'',
                    'name':'',
                    'color':'',
                    'count':'',
                })


        for medium_box in get_medium_box:
            check = ep_obj.search(domain+[('n_grid_result_id','=',medium_box.id)])
            dataresult['medium'].append({
                'id':medium_box.id,
                'name':medium_box.category,
                'color':medium_box.color or 'white',
                'number_analysis':medium_box.number_analysis,
                'count':len(check)
                })
        if len(dataresult['medium']) < 3:
            re = 3-len(dataresult['medium'])
            for c in range(re):
                dataresult['medium'].append({
                    'id':'',
                    'name':'',
                    'color':'',
                    'count':'',
                })


        for high_box in get_high_box:
            check = ep_obj.search(domain+[('n_grid_result_id','=',high_box.id)])
            dataresult['high'].append({
                'id':high_box.id,
                'name':high_box.category,
                'color':high_box.color or 'white',
                'number_analysis':high_box.number_analysis,
                'count':len(check)
                })
        if len(dataresult['high']) < 3:
            re = 3-len(dataresult['high'])
            for c in range(re):
                dataresult['high'].append({
                    'id':'',
                    'name':'',
                    'color':'',
                    'count':'',
                })

        return dataresult
    
    @api.model
    def perform_search(self, evaluation_period=None, department=None, employee=None, job_position=None):
        search_result = self.search([
            '|', '|', '|',
            ('date_range_id', '=', evaluation_period),
            ('department_id', '=', department),
            ('employee_id', '=', employee),
            ('job_id', '=', job_position),
            ('state', '=', 'done')
        ])

        return search_result.ids
    
    def auto_get_training_plan(self):        
        comp_gap = self.search([('competencies_line_ids.competency_gap','<',0),('competencies_line_ids.auto_training','=',False)])
        for record in comp_gap:
            for rec in comp_gap.competencies_line_ids:
                training_conduct_line = self.env['training.conduct.line'].search([('employee_id','=',rec.employee_id.id)])
                if rec.state == 'done':
                    for job_comp in rec.employee_id.job_id.competencies_detail_ids:
                        for line in rec.name:
                            for job in job_comp.name:
                                if line.name == job.name and job_comp.is_competency_gap and rec.competency_gap <= job_comp.minimum_gap:
                                    for training in job_comp.name.training_required_ids:
                                        for tcl in training_conduct_line:
                                            data = {
                                                'competencies_areas': rec.name.name,
                                                'competencies_score': rec.weightage_score,
                                                'training_course': training.name,
                                                'training_score': tcl.post_test,
                                                'status': 'New',
                                                'performance_id': record.id
                                            }
                                    self.env['employee.training.plan.line'].create(data)
                                    rec.auto_training = True

    def _query(self, with_clause='', fields={}, groupby='', from_clause=''):
        print(fields)
        return super(EmployeePerformance, self)._query(with_clause, fields, groupby, from_clause)

    
    
    # @api.model
    # def fields_get(self, allfields=None, attributes=None):
    #     res = super(EmployeePerformance, self).fields_get(allfields, attributes=attributes)
       
    #     print(res)
    #     return res

    
    
    
    
    @api.depends('state')
    def _compute_is_hide_refresh(self):
        for record in self:
            if record.state:
                if record.state in ['sent_to_employee','sent_to_manager']:
                    record.is_hide_refresh = False
                else:
                    record.is_hide_refresh = True
            else:
                record.is_hide_refresh = True
    
    
    
    def action_done(self):
        res = super(EmployeePerformance,self).action_done()
        matrix  = self.env['nine.box.matrix'].search([])
        matrix_score = matrix.filtered(lambda line: round(self.total_weightage_score_performance) >= line.min_performance_score  
                                                                                     and  round(self.total_weightage_score_performance) <= line.max_performance_score 
                                                                                     and round(self.total_weightage_score) >= line.min_competency_score
                                                                                     and round(self.total_weightage_score) <= line.max_competency_score
                                                                                     )
        if matrix_score:
            self.n_grid_id = matrix_score.id
        else:
            raise ValidationError("not matrix match with the score")
        
        self.search_cascade_manual()
       
        # if self.performances_line_ids:
        #     for record in self.performances_line_ids:
        #         if record.is_cascade and record.name.computation_mode == 'manually' and record.name.condition == 'higher':
        #             amount = self.search_cascade_manual()
        #             record.cascade_score = amount

        comp_gap = self.env['employee.competencies.line'].search([
            ('competency_gap','<',0),
            ('auto_training','=',False),
        ])

        for record in self:
            for rec in comp_gap:
                training_conduct_line = self.env['training.conduct.line'].search([('employee_id','=',rec.employee_id.id)])

                for job_comp in rec.employee_id.job_id.competencies_detail_ids:
                    if rec.name == job_comp.name and job_comp.is_competency_gap and rec.competency_gap <= job_comp.minimum_gap:
                        training_list = []
                        for training in job_comp.name.training_required_ids:
                            training_list.append(training.id)

                        data = {
                            'competencies_areas': rec.name.name,
                            'competencies_score': rec.weightage_score,
                            'competencies_gap': rec.competency_gap,
                            'course_ids': training_list,
                            'training_score': 0.0,
                            'status': 'to_do',
                            'performance_id': record.id,
                            'employee_id': rec.employee_id.id
                        }
                        
                        self.env['employee.training.plan.line'].create(data)
                        # rec.auto_training = True

                        training_todo = {
                            'employee_id': rec.employee_id.id,
                            'job_id': rec.employee_id.job_id.id,
                            'training_required': 'yes',
                            'course_ids': training_list,
                            'created_by_model': 'by_employee_competencies_line'
                        }
                        self.env['training.histories'].create(training_todo)
                        rec.auto_training = True
            
            emp_tpl = self.env['employee.training.plan.line'].search([('performance_id', '=', record.id)])
            for emp in emp_tpl:
                print("============== employee: ", str(emp.employee_id.id,), " == ", str(record.id))
        
        return res
    
    
    
    
    
    @api.onchange('employee_id')
    def _ochange_employee(self):
        for record in self:
            if record.employee_id:
                if record.employee_id.parent_id:
                    record.manager_id = record.employee_id.parent_id.id
                if not record.employee_id.user_id:
                    employee_ids = self.env['hr.employee'].search([('user_id','=',False)])
                    name_list = [data.name for data in employee_ids]
                    name_str = "\n".join(name_list)
                    if employee_ids:
                        raise ValidationError(f"The following employees do not have users: \n {name_str}")
    
    
    
    
    def line_to_update(self,line_update):
        if line_update.name.computation_mode == 'python':
            cxt = {
                'object': line_update.name.model_id.model,
                'env': self.env,
                'date': date,
                'datetime': datetime,
                'timedelta': timedelta,
                'time': time,
                }
            code = line_update.compute_code.strip()
            safe_eval(code, cxt, mode="exec", nocopy=True)
            result = cxt.get('result')
            if isinstance(result, (float, int)):
                line_update.employee_rate = result
                line_update.manager_rate = result
            else:
                _logger.error(
                            "Invalid return content '%r' from the evaluation "
                            "of code for definition %s, expected a number",
                            result, line_update.name.name)
        elif line_update.name.computation_mode in ('count', 'sum'):
            field_date_name = line_update.name.field_date_id.name if line_update.name.field_date_id else False
            Obj = self.env[line_update.name.model_id.model]
            if line_update.name.batch_mode:
                general_domain = ast.literal_eval(line_update.name.domain)
                field_name = line_update.name.batch_distinctive_field.name
                start_date =  line_update.performance_id.date_range_id.date_start or False
                end_date = line_update.performance_id.date_range_id.date_end or False
                subqueries = {}
                subqueries.setdefault((start_date, end_date), {}).update({line_update.name.id:safe_eval(line_update.name.batch_user_expression, {'user': line_update.performance_id.employee_id.user_id})})
                for (start_date, end_date), query_goals in subqueries.items():
                    subquery_domain = list(general_domain)
                    subquery_domain.append((field_name, 'in', list(set(query_goals.values()))))
                    if start_date and field_date_name:
                            subquery_domain.append((field_date_name, '>=', start_date))
                    if end_date and field_date_name:
                        subquery_domain.append((field_date_name, '<=', end_date))
                    if line_update.name.computation_mode == 'count':
                        value_field_name = field_name + '_count'
                        if field_name == 'id':
                            # grouping on id does not work and is similar to search anyway
                            users = Obj.search(subquery_domain)
                            user_values = [{'id': user.id, value_field_name: 1} for user in users]
                        else:
                            user_values = Obj.read_group(subquery_domain, fields=[field_name], groupby=[field_name])
                        new_value = user_values and user_values[0][value_field_name] or 0
                    else:  # sum
                        value_field_name = line_update.name.field_id.name
                        if field_name == 'id':
                            user_values = Obj.search_read(subquery_domain, fields=['id', value_field_name])
                        else:
                            user_values = Obj.read_group(subquery_domain, fields=[field_name, "%s:sum" % value_field_name], groupby=[field_name])
                        new_value = user_values and user_values[0][value_field_name] or 0.0                   
            else:        
                # eval the domain with user replaced by goal user object
                domain = safe_eval(line_update.name.domain, {'user': line_update.performance_id.employee_id.user_id})
                # add temporal clause(s) to the domain if fields are filled on the goal
                if line_update.performance_id.date_range_id.date_start and field_date_name:
                    domain.append((field_date_name, '>=', line_update.performance_id.date_range_id.date_start))
                if line_update.performance_id.date_range_id.date_end and field_date_name:
                    domain.append((field_date_name, '<=', line_update.performance_id.date_range_id.date_end))
                if line_update.name.computation_mode == 'sum':
                    field_name = line_update.name.field_id.name
                    res = Obj.read_group(domain, [field_name], [])
                    new_value = res and res[0][field_name] or 0.0

                else:  # computation mode = count
                    new_value = Obj.search_count(domain)
            line_update.employee_rate = new_value
            line_update.manager_rate = new_value
            if line_update.is_cascade:
                amount = self.search_cascade(line_update.cascade_line_ids)
                line_update.cascade_score = amount
                
               
    
    # def search_cascade(self,cascade_line):
    #     cascade_total =  0
    #     for data in cascade_line:
    #         performance_id =  self.search([('employee_id','=',data.employee_id.id),
    #                                         ('date_range_id','=',data.parent_id.performance_id.date_range_id.id),
    #                                         ('state','=','sent_to_manager')
    #                                         ])
    #         if performance_id:
    #             cascade_total += self.assign_weightage_score(performance_id,data)
    #     return cascade_total
    def search_cascade(self,cascade_line):
        cascade_total =  0
        for data in cascade_line:
            cascade_total += (data.assign_weightage/100) * data.weightage_score
            # performance_id =  self.search([('employee_id','=',data.employee_id.id),
            #                                 ('date_range_id','=',data.parent_id.performance_id.date_range_id.id),
            #                                 ('state','=','sent_to_manager')
            #                                 ])
            # if performance_id:
            #     cascade_total += self.assign_weightage_score(performance_id,data)
        return cascade_total
    
    
    def search_cascade_manual(self):
        evaluation_ids = self.search([('date_range_id','=',self.date_range_id.id)]).performances_line_ids.filtered(lambda line: self.employee_id.id in line.cascade_employee_ids.ids
                                                                                             and line.name.computation_mode == 'manually' 
                                                                                             and line.name.condition == 'higher'
                                                                                             
                                                                                             )
        if evaluation_ids:
            for record in evaluation_ids:
                self.assign_weightage_score_manual(record.cascade_line_ids.filtered(lambda line:line.employee_id.id == self.employee_id.id and line.parent_id.id == record.id),record)
                
    def assign_weightage_score_manual(self,cascade_line_ids,record_to_update):
        for data in cascade_line_ids:
            # record_to_update.cascade_score = record_to_update.cascade_score + ((data.assign_weightage/100) * self.total_weightage_score_performance)
            record_to_update.cascade_score = record_to_update.cascade_score + ((data.assign_weightage/100) * data.weightage_score)
        
                
                 
                 
    
      
    def assign_weightage_score(self,performance_id,data_line):
        cascade_total = 0
        for record in performance_id:
            cascade_total += (data_line.assign_weightage/100) *record.total_weightage_score_performance
            return cascade_total
              
                                
                        
    
    def refresh(self):
        for record in self.performances_line_ids:
            self.line_to_update(record)
    
    def get_line(self,employee_achievement_to_update):
        for data in employee_achievement_to_update.performances_line_ids:
            self.line_to_update(data)
        
            
    
    def update_achievement(self):
        query_statement_ep = """
                    SELECT ep.id,
                            pdr.date_start,
                            pdr.date_end
                            
                    FROM employee_performance ep 
                    LEFT JOIN performance_date_range pdr ON ep.date_range_id = pdr.id 
    
                """
        self.env.cr.execute(query_statement_ep, [])
        query_statement_ep_ids = self._cr.dictfetchall()
        ep_ids = [data['id'] for data in query_statement_ep_ids]
        employee_achievement_to_update = self.env[self._name].browse(ep_ids)
        for data in employee_achievement_to_update:
            self.get_line(data)
        
        
    
    @api.depends('is_period_performances','is_period_competencies','is_period_all_review','is_period_task_challenge','is_evaluation_okr','total_weightage_score_performance','total_weightage_score','peer_reviews_total_score','task_challenge_weightage_score','okr_total_score')
    def _compute_overal_score(self):
        for record in self:
            total_overal_score = 0
            if record.is_period_performances:
                if record.is_evaluation_okr and record.okr_total_score > 0:
                    performance_component = (record.period_performance_weightage  * record.okr_total_score) / 100
                    total_overal_score += performance_component
                elif not record.is_evaluation_okr and record.total_weightage_score_performance > 0:
                    performance_component = (record.period_performance_weightage  * record.total_weightage_score_performance) / 100
                    total_overal_score += performance_component
            if record.is_period_competencies and record.total_weightage_score > 0:
                competencies_component = (record.period_competencies_weightage  * record.total_weightage_score) / 100
                total_overal_score += competencies_component
            if record.is_period_all_review and record.peer_reviews_total_score > 0:
                competencies_component = (record.period_all_review_weightage  * record.peer_reviews_total_score) / 100
                total_overal_score += competencies_component
            if record.is_period_task_challenge and record.task_challenge_weightage_score > 0:
                competencies_component = (record.period_task_challenge_weightage  * record.task_challenge_weightage_score) / 100
                total_overal_score += competencies_component
            record.overal_score = total_overal_score
            record.overal_score_shadow = total_overal_score
    
    
    @api.depends('performances_line_ids','total_weightage_performance')
    def _compute_total_weightage_score_performance(self):
        for rec in self:
            if rec.performances_line_ids and rec.total_weightage:
                total = (sum([data.weightage_score for data in rec.performances_line_ids])/rec.total_weightage_performance ) *100 if rec.total_weightage_performance > 0 else 0
                rec.total_weightage_score_performance = total
                rec.total_weightage_score_performance_shadow = total
            else:
                rec.total_weightage_score_performance = 0
                rec.total_weightage_score_performance_shadow = 0
            
    @api.depends('competencies_line_ids','total_weightage')
    def _compute_total_weightage_score(self):
        for rec in self:
            if rec.competencies_line_ids and rec.total_weightage:
                total = (sum([data.weightage_score for data in rec.competencies_line_ids])/rec.total_weightage ) *100 if rec.total_weightage > 0 else 0
                rec.total_weightage_score = total
                rec.total_weightage_score_shadow = total
            else:
                rec.total_weightage_score = 0
                rec.total_weightage_score_shadow = 0
            
    @api.depends('performances_line_ids')
    def _compute_weightage_performance(self):
        for rec in self:
            if rec.performances_line_ids:
                total = sum([data.weightage for data in rec.performances_line_ids])
                rec.total_weightage_performance = total
            else:
                rec.total_weightage_performance = 0
            
    @api.depends('competencies_line_ids')
    def _compute_total_weightage(self):
        for rec in self:
            if rec.competencies_line_ids:
                total = sum([data.weightage for data in rec.competencies_line_ids])
                rec.total_weightage = total
            else:
                rec.total_weightage = 0
            
    @api.depends('competencies_line_ids')
    def _compute_total_competency_gap(self):
        for rec in self:
            if rec.competencies_line_ids:
                total = sum([data.competency_gap for data in rec.competencies_line_ids])
                rec.total_competency_gap = total
            else:
                rec.total_competency_gap = 0
            
    @api.depends('competencies_line_ids')
    def _compute_total_competency_match(self):
        for rec in self:
            if rec.competencies_line_ids:
                total = sum([data.competency_match for data in rec.competencies_line_ids]) / len(rec.competencies_line_ids)
                rec.total_competency_match = total
            else:
                rec.total_competency_match = 0
            
    @api.depends('competencies_line_ids')
    def _compute_total_score(self):
        for rec in self:
            if rec.competencies_line_ids:
                total = sum([data.score.competency_score for data in rec.competencies_line_ids])
                rec.total_score = total
            else:
                rec.total_score = 0
            
    @api.depends('competencies_line_ids')
    def _compute_total_target_score(self):
        for rec in self:
            if rec.competencies_line_ids:
                total = sum([data.target_score_id.competency_score for data in rec.competencies_line_ids])
                rec.total_target_score = total
            else:
                rec.total_target_score = 0

    @api.depends('okr_line_ids','okr_line_ids.weightage')
    def _compute_okr_total_weightage(self):
        for rec in self:
            if rec.okr_line_ids:
                total = sum(rec.okr_line_ids.mapped("weightage"))
                rec.okr_total_weightage = total
            else:
                rec.okr_total_weightage = 0
    
    @api.depends('okr_line_ids','okr_line_ids.score')
    def _compute_okr_total_score(self):
        for rec in self:
            if rec.okr_line_ids:
                total = sum(rec.okr_line_ids.mapped("score"))
                rec.okr_total_score = total
            else:
                rec.okr_total_score = 0

    @api.model
    def fields_view_get(self, view_id=None, view_type=None, toolbar=False, submenu=False):
        res = super(EmployeePerformance, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=True)
        
        if self.env.user.has_group('hr.group_hr_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
        else:
            root = etree.fromstring(res['arch'])
            root.set('create', 'false')
            root.set('edit', 'true')
            root.set('delete', 'true')
            res['arch'] = etree.tostring(root)
    
        return res

    @api.depends('date_range_id')
    def compute_is_period(self):
        for rec in self:
            if rec.date_range_id:
                rec.is_period = True
            else:
                rec.is_period = False

    @api.onchange('date_range_id')
    def onchange_date_range_id(self):
        for rec in self:
            if rec.date_range_id.deadline:
                rec.deadline = rec.date_range_id.deadline
            else:
                rec.deadline = False

    @api.depends('employee_id')
    def _compute_self_employee(self):
        for rec in self:
            current_user = self.env.user.id
            if current_user == rec.employee_id.user_id.id:
                rec.is_employee = True
            else:
                rec.is_employee = False
    
    @api.onchange('template_id')
    def onchange_template_id(self):
        
        # competencies_areas_list = []
        # # training_required_list = []
        # # # competencies_areas = self.search([('competencies_line_ids.'])
        # employee_performace_obj = self.env['employee.performance']
        # comp = employee_performace_obj.search([''])
        # # # comp_gap = self.search([('competency_gap','<',0),('auto_training','=',False),])
        # for ca in comp:
        #     competencies_areas_list.append(ca.competencies_areas)
        
        # # # for ca in competencies_areas.training_required_ids:
        # # #     training_required_list.append(ca.name)
        
        # print("===============: ", comp_gap)  

        # print("================: ", self.env.user)

        
        if self.template_id:
            if self.performances_line_ids:
                remove = []
                for line in self.performances_line_ids:
                    remove.append((2, line.id))
                self.performances_line_ids = remove
            key_lines = []
            performance_ids = self.template_id.key_performance_ids
            for line in performance_ids:
                key_lines.append((0, 0, {'performance_id': self.id,
                                        'name': line.name.id,
                                        'kpi_comparison': line.name.condition,
                                        'description': line.description,
                                        'weightage': line.weightage,
                                        'key_id': line.key_id.id,
                                        'sequence': line.sequence,
                                        'kpi_target':line.kpi_target
                                        }))
            self.performances_line_ids = key_lines

    @api.onchange('comp_template_id')
    def onchange_comp_template_id(self):
        if self.comp_template_id:
            if self.competencies_line_ids:
                remove = []
                for line in self.competencies_line_ids:
                    remove.append((2, line.id))
                self.competencies_line_ids = remove
            key_lines = []
            competencies_ids = self.comp_template_id.competencies_ids
            for line in competencies_ids:
                key_lines.append((0, 0, {'performance_id': self.id,
                                        'name': line.name.id,
                                        'description': line.description,
                                        'key_id': line.key_id.id,
                                        'sequence': line.sequence,
                                        'target_score_id':line.target_score_id.id,
                                        'weightage':line.weightage
                                        }))
            self.competencies_line_ids = key_lines

    @api.onchange('employee_id')
    def onchange_approver_user(self):
        for appraisal in self:
            if appraisal.appraisal_approver_user_ids:
                remove = []
                for line in appraisal.appraisal_approver_user_ids:
                    remove.append((2, line.id))
                appraisal.appraisal_approver_user_ids = remove
            setting = self.env['ir.config_parameter'].sudo().get_param(
                'equip3_hr_employee_appraisals.appraisal_type_approval')
            if setting == 'employee_hierarchy':
                appraisal.appraisal_approver_user_ids = self.appraisal_emp_by_hierarchy(appraisal)
                self.app_list_appraisal_emp_by_hierarchy()
            if setting == 'approval_matrix':
                self.appraisal_approval_by_matrix(appraisal)

    def appraisal_emp_by_hierarchy(self, appraisal):
        approval_ids = []
        seq = 1
        data = 0
        line = self.get_manager(appraisal, appraisal.employee_id, data, approval_ids, seq)
        return line

    def get_manager(self, appraisal, employee_manager, data, approval_ids, seq):
        setting_level = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_appraisals.appraisal_level')
        if not setting_level:
            raise ValidationError("Level not set")
        if not employee_manager['parent_id']['user_id']:
            return approval_ids
        while data < int(setting_level):
            approval_ids.append(
                (0, 0, {'user_ids': [(4, employee_manager['parent_id']['user_id']['id'])]}))
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager(appraisal, employee_manager['parent_id'], data, approval_ids, seq)
                break
        return approval_ids

    def get_manager_hierarchy(self, appraisal, employee_manager, data, manager_ids, seq, level):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            seq += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(appraisal, employee_manager['parent_id'], data, manager_ids, seq, level)
                break

        return manager_ids

    def app_list_appraisal_emp_by_hierarchy(self):
        for appraisal in self:
            app_list = []
            for line in appraisal.appraisal_approver_user_ids:
                app_list.append(line.user_ids.id)
            appraisal.approvers_ids = app_list

    def appraisal_approval_by_matrix(self, appraisal):
        app_list = []
        approval_matrix = self.env['hr.appraisals.approval.matrix'].search([('apply_to', '=', 'by_employee')])
        matrix = approval_matrix.filtered(lambda line: appraisal.employee_id.id in line.employee_ids.ids)
        if matrix:
            data_approvers = []
            for line in matrix[0].approval_matrix_ids:
                if line.approver_types == "specific_approver":
                    data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                  'user_ids': [(6, 0, line.approvers.ids)]}))
                    for approvers in line.approvers:
                        app_list.append(approvers.id)
                elif line.approver_types == "by_hierarchy":
                    manager_ids = []
                    seq = 1
                    data = 0
                    approvers = self.get_manager_hierarchy(appraisal, appraisal.employee_id, data, manager_ids, seq, line.minimum_approver)
                    for approver in approvers:
                        data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                        app_list.append(approver)
            appraisal.approvers_ids = app_list
            appraisal.appraisal_approver_user_ids = data_approvers

        if not matrix:
            data_approvers = []
            approval_matrix = self.env['hr.appraisals.approval.matrix'].search([('apply_to', '=', 'by_job_position')])
            matrix = approval_matrix.filtered(lambda line: appraisal.job_id.id in line.job_ids.ids)
            if matrix:
                for line in matrix[0].approval_matrix_ids:
                    if line.approver_types == "specific_approver":
                        data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                      'user_ids': [(6, 0, line.approvers.ids)]}))
                        for approvers in line.approvers:
                            app_list.append(approvers.id)
                    elif line.approver_types == "by_hierarchy":
                        manager_ids = []
                        seq = 1
                        data = 0
                        approvers = self.get_manager_hierarchy(appraisal, appraisal.employee_id, data, manager_ids, seq, line.minimum_approver)
                        for approver in approvers:
                            data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                            app_list.append(approver)
                appraisal.approvers_ids = app_list
                appraisal.appraisal_approver_user_ids = data_approvers
            if not matrix:
                data_approvers = []
                approval_matrix = self.env['hr.appraisals.approval.matrix'].search([('apply_to', '=', 'by_department')])
                matrix = approval_matrix.filtered(lambda line: appraisal.department_id.id in line.department_ids.ids)
                if matrix:
                    for line in matrix[0].approval_matrix_ids:
                        if line.approver_types == "specific_approver":
                            data_approvers.append((0, 0, {'minimum_approver': line.minimum_approver,
                                                          'user_ids': [(6, 0, line.approvers.ids)]}))
                            for approvers in line.approvers:
                                app_list.append(approvers.id)
                        elif line.approver_types == "by_hierarchy":
                            manager_ids = []
                            seq = 1
                            data = 0
                            approvers = self.get_manager_hierarchy(appraisal, appraisal.employee_id, data, manager_ids, seq, line.minimum_approver)
                            for approver in approvers:
                                data_approvers.append((0, 0, {'user_ids': [(4, approver)]}))
                                app_list.append(approver)
                    appraisal.approvers_ids = app_list
                    appraisal.appraisal_approver_user_ids = data_approvers

    @api.depends('state', 'employee_id')
    def _compute_can_approve(self):
        for appraisal in self:
            if appraisal.approvers_ids:
                setting = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_employee_appraisals.appraisal_type_approval')
                setting_level = self.env['ir.config_parameter'].sudo().get_param(
                    'equip3_hr_employee_appraisals.appraisal_level')
                app_level = int(setting_level)
                current_user = appraisal.env.user
                if setting == 'employee_hierarchy':
                    matrix_line = sorted(appraisal.appraisal_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(appraisal.appraisal_approver_user_ids)
                    if app < app_level and app < a:
                        if current_user in appraisal.appraisal_approver_user_ids[app].user_ids:
                            appraisal.is_approver = True
                        else:
                            appraisal.is_approver = False
                    else:
                        appraisal.is_approver = False
                elif setting == 'approval_matrix':
                    matrix_line = sorted(appraisal.appraisal_approver_user_ids.filtered(lambda r: r.is_approve == True))
                    app = len(matrix_line)
                    a = len(appraisal.appraisal_approver_user_ids)
                    if app < a:
                        for line in appraisal.appraisal_approver_user_ids[app]:
                            if current_user in line.user_ids:
                                appraisal.is_approver = True
                            else:
                                appraisal.is_approver = False
                    else:
                        appraisal.is_approver = False

                else:
                    appraisal.is_approver = False
            else:
                appraisal.is_approver = False

    # def action_done(self):
    #     for record in self:
    #         current_user = self.env.uid
    #         setting = self.env['ir.config_parameter'].sudo().get_param(
    #             'equip3_hr_employee_appraisals.appraisal_type_approval')
    #         now = datetime.now(timezone(self.env.user.tz))
    #         dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
    #         date_approved = time.strftime(DEFAULT_SERVER_DATE_FORMAT)
    #         date_approved_obj = datetime.strptime(date_approved, DEFAULT_SERVER_DATE_FORMAT)
    #         if setting == 'employee_hierarchy':
    #             if self.env.user not in record.approved_user_ids:
    #                 if record.is_approver:
    #                     for user in record.appraisal_approver_user_ids:
    #                         if current_user == user.user_ids.id:
    #                             user.is_approve = True
    #                             user.timestamp = fields.Datetime.now()
    #                             user.approver_state = 'approved'
    #                             string_approval = []
    #                             if user.approval_status:
    #                                 string_approval.append(f"{self.env.user.name}:Approved")
    #                                 user.approval_status = "\n".join(string_approval)
    #                                 string_timestammp = [user.approved_time]
    #                                 string_timestammp.append(f"{self.env.user.name}:{dateformat}")
    #                                 user.approved_time = "\n".join(string_timestammp)
    #                                 if record.feedback_parent:
    #                                     feedback_list = [user.feedback,
    #                                                      f"{self.env.user.name}:{record.feedback_parent}"]
    #                                     final_feedback = "\n".join(feedback_list)
    #                                     user.feedback = f"{final_feedback}"
    #                                 elif user.feedback and not record.feedback_parent:
    #                                     user.feedback = user.feedback
    #                                 else:
    #                                     user.feedback = ""
    #                             else:
    #                                 user.approval_status = f"{self.env.user.name}:Approved"
    #                                 user.approved_time = f"{self.env.user.name}:{dateformat}"
    #                                 if record.feedback_parent:
    #                                     user.feedback = f"{self.env.user.name}:{record.feedback_parent}"
    #                                 else:
    #                                     user.feedback = ""
    #                             record.approved_user_ids = [(4, current_user)]
    #                     matrix_line = sorted(record.appraisal_approver_user_ids.filtered(lambda r: r.is_approve == False))
    #                     if len(matrix_line) == 0:
    #                         record.write({'state': 'done'})
    #                     else:
    #                         record.approved_user = self.env.user.name + ' ' + 'has been approved the Request!'
    #                 else:
    #                     raise ValidationError(_(
    #                         'You are not allowed to perform this action!'
    #                     ))
    #             else:
    #                 raise ValidationError(_(
    #                     'Already approved'
    #                 ))
    #         elif setting == 'approval_matrix':
    #             if self.env.user not in record.approved_user_ids:
    #                 if record.is_approver:
    #                     for line in record.appraisal_approver_user_ids:
    #                         for user in line.user_ids:
    #                             if current_user == user.user_ids.id:
    #                                 line.timestamp = fields.Datetime.now()
    #                                 record.approved_user_ids = [(4, current_user)]
    #                                 var = len(line.approved_employee_ids) + 1
    #                                 if line.minimum_approver <= var:
    #                                     line.approver_state = 'approved'
    #                                     string_approval = []
    #                                     string_approval.append(line.approval_status)
    #                                     if line.approval_status:
    #                                         string_approval.append(f"{self.env.user.name}:Approved")
    #                                         line.approval_status = "\n".join(string_approval)
    #                                         string_timestammp = [line.approved_time]
    #                                         string_timestammp.append(f"{self.env.user.name}:{dateformat}")
    #                                         line.approved_time = "\n".join(string_timestammp)
    #                                         if record.feedback_parent:
    #                                             feedback_list = [line.feedback,
    #                                                              f"{self.env.user.name}:{record.feedback_parent}"]
    #                                             final_feedback = "\n".join(feedback_list)
    #                                             line.feedback = f"{final_feedback}"
    #                                         elif line.feedback and not record.feedback_parent:
    #                                             line.feedback = line.feedback
    #                                         else:
    #                                             line.feedback = ""
    #                                     else:
    #                                         line.approval_status = f"{self.env.user.name}:Approved"
    #                                         line.approved_time = f"{self.env.user.name}:{dateformat}"
    #                                         if record.feedback_parent:
    #                                             line.feedback = f"{self.env.user.name}:{record.feedback_parent}"
    #                                         else:
    #                                             line.feedback = ""
    #                                     line.is_approve = True
    #                                 else:
    #                                     line.approver_state = 'pending'
    #                                     if line.approval_status:
    #                                         string_approval.append(f"{self.env.user.name}:Approved")
    #                                         line.approval_status = "\n".join(string_approval)
    #                                         string_timestammp = [line.approved_time]
    #                                         string_timestammp.append(f"{self.env.user.name}:{dateformat}")
    #                                         line.approved_time = "\n".join(string_timestammp)
    #                                         if record.feedback_parent:
    #                                             feedback_list = [line.feedback,
    #                                                              f"{self.env.user.name}:{record.feedback_parent}"]
    #                                             final_feedback = "\n".join(feedback_list)
    #                                             line.feedback = f"{final_feedback}"
    #                                         elif line.feedback and not record.feedback_parent:
    #                                             line.feedback = line.feedback
    #                                         else:
    #                                             line.feedback = ""
    #                                     else:
    #                                         line.approval_status = f"{self.env.user.name}:Approved"
    #                                         line.approved_time = f"{self.env.user.name}:{dateformat}"
    #                                         if record.feedback_parent:
    #                                             line.feedback = f"{self.env.user.name}:{record.feedback_parent}"
    #                                         else:
    #                                             line.feedback = ""
    #                                 line.approved_employee_ids = [(4, current_user)]

    #                     matrix_line = sorted(record.appraisal_approver_user_ids.filtered(lambda r: r.is_approve == False))
    #                     if len(matrix_line) == 0:
    #                         record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
    #                         record.write({'state': 'done'})
    #                     else:
    #                         record.approved_user = self.env.user.name + ' ' + 'has approved the Request!'
    #                 else:
    #                     raise ValidationError(_(
    #                         'You are not allowed to perform this action!'
    #                     ))
    #             else:
    #                 raise ValidationError(_(
    #                     'Already approved!'
    #                 ))
    #         else:
    #             raise ValidationError(_(
    #                 'Already approved!'
    #             ))

    # def action_cancel(self):
    #     for record in self:
    #         for user in record.appraisal_approver_user_ids:
    #             for check_user in user.user_ids:
    #                 now = datetime.now(timezone(self.env.user.tz))
    #                 dateformat = f"{now.day}/{now.month}/{now.year} {now.hour}:{now.minute}:{now.second}"
    #                 if self.env.uid == check_user.id:
    #                     user.timestamp = fields.Datetime.now()
    #                     user.approver_state = 'refuse'
    #                     string_approval = []
    #                     string_approval.append(user.approval_status)
    #                     if user.approval_status:
    #                         string_approval.append(f"{self.env.user.name}:Refused")
    #                         user.approval_status = "\n".join(string_approval)
    #                         string_timestammp = [user.approved_time]
    #                         string_timestammp.append(f"{self.env.user.name}:{dateformat}")
    #                         user.approved_time = "\n".join(string_timestammp)
    #                     else:
    #                         user.approval_status = f"{self.env.user.name}:Refused"
    #                         user.approved_time = f"{self.env.user.name}:{dateformat}"
    #         record.approved_user = self.env.user.name + ' ' + 'has been Rejected!'
    #         record.write({'state': 'cancel'})

    def wizard_approve(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'hr.appraisal.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Confirmation Message",
            'target': 'new',
        }

    def send_feedbacks_wa_notification(self, reviewer, survey_url):
        send_by_wa = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_appraisals.send_by_wa')
        wa_sender = waParam()
        wa_template_id = self.env.ref('equip3_hr_employee_appraisals.wa_template_peer_reviews', raise_if_not_found=False)
        for rec in self:
            if send_by_wa:
                wa_sender = waParam()
                wa_template_id = self.env.ref('equip3_hr_employee_appraisals.wa_template_peer_reviews', raise_if_not_found=False)
                wa_string = str(wa_template_id.message)
                phone_num = str(reviewer.mobile_phone)

                if "${reviewer_name}" in wa_string:
                    wa_string = wa_string.replace("${reviewer_name}", reviewer.name)
                if "${employee_name}" in wa_string:
                    wa_string = wa_string.replace("${employee_name}", rec.employee_id.name)
                if "${job_position}" in wa_string:
                    wa_string = wa_string.replace("${job_position}", rec.employee_id.job_id.name)
                if "${url_review}" in wa_string:
                    wa_string = wa_string.replace("${url_review}", survey_url)
                if "+" in phone_num:
                    phone_num = int(phone_num.replace("+", ""))
                
                wa_sender.set_wa_string(wa_string,wa_template_id._name,template_id=wa_template_id)
                wa_sender.send_wa(phone_num)

    def action_sent_feedback(self):
        for rec in self:
            if rec.employee_id.job_id:
                if rec.employee_id.job_id.performance_all_review_id:
                    peer_review = rec.employee_id.job_id.performance_all_review_id
                    peer_reviews_line = []
                    if peer_review.is_included_manager:
                        manager_target_score = 0
                        for question in peer_review.manager_feedback_template_id.question_and_page_ids:
                            higher_score = max(question.suggested_answer_ids.mapped("answer_score"))
                            manager_target_score += higher_score
                        peer_reviews_line.append((0, 0, {'role': 'manager','weightage':peer_review.manager_weightage,'target_score':manager_target_score}))
                        template_id = self.env.ref('equip3_hr_employee_appraisals.mail_template_peer_reviews', raise_if_not_found=False)
                        manager_ids = []
                        employee = rec.employee_id
                        seq = 1
                        data = 0
                        max_reviewer = peer_review.manager_max_reviewer
                        manager_hierarchy = self.get_manager_hierarchy(rec, rec.employee_id, data, manager_ids, seq, max_reviewer)
                        manager_list = []
                        for manager in manager_hierarchy:
                            manager_list.append(manager)
                        managers = self.env['hr.employee'].search([('user_id','in',manager_list)])
                        if managers:
                            for manager in managers:
                                survey_review = self.env['survey.invite'].create(
                                    {'survey_id': peer_review.manager_feedback_template_id.id,
                                    'emails': str(manager.work_email), 'template_id': template_id.id})
                                context = self.env.context = dict(self.env.context)
                                survey_url = survey_review.survey_start_url + f"?surveyId={peer_review.manager_feedback_template_id.id}&performanceId={rec.id}&reviewerRole=manager&companyName=none&reviewerName={manager.name}&reviewerEmail={manager.work_email}"
                                context.update({
                                    'email_to': manager.work_email,
                                    'reviewer_name': manager.name,
                                    'employee_name': rec.employee_id.name,
                                    'url_review': survey_url,
                                    'title': peer_review.manager_feedback_template_id.title,
                                    'job_position': rec.employee_id.job_id.name

                                })
                                template_id.send_mail(rec.id, force_send=False)
                                template_id.with_context(context)
                                self.send_feedbacks_wa_notification(manager, survey_url)

                    if peer_review.is_included_subordinate:
                        subordinate_target_score = 0
                        for question in peer_review.subordinate_feedback_template_id.question_and_page_ids:
                            higher_score = max(question.suggested_answer_ids.mapped("answer_score"))
                            subordinate_target_score += higher_score
                        peer_reviews_line.append((0, 0, {'role': 'subordinate','weightage':peer_review.subordinate_weightage,'target_score':subordinate_target_score}))
                        template_id = self.env.ref('equip3_hr_employee_appraisals.mail_template_peer_reviews', raise_if_not_found=False)
                        subordinates = self.env['hr.employee'].search([('parent_id','=',rec.employee_id.id)])
                        if subordinates:
                            for subordinate in subordinates:
                                survey_review = self.env['survey.invite'].create(
                                    {'survey_id': peer_review.subordinate_feedback_template_id.id,
                                    'emails': str(subordinate.work_email), 'template_id': template_id.id})
                                context = self.env.context = dict(self.env.context)
                                survey_url = survey_review.survey_start_url + f"?surveyId={peer_review.subordinate_feedback_template_id.id}&performanceId={rec.id}&reviewerRole=subordinate&companyName=none&reviewerName={subordinate.name}&reviewerEmail={subordinate.work_email}"
                                context.update({
                                    'email_to': subordinate.work_email,
                                    'reviewer_name': subordinate.name,
                                    'employee_name': rec.employee_id.name,
                                    'url_review': survey_url,
                                    'title': peer_review.subordinate_feedback_template_id.title,
                                    'job_position': rec.employee_id.job_id.name

                                })
                                template_id.send_mail(rec.id, force_send=False)
                                template_id.with_context(context)
                                self.send_feedbacks_wa_notification(subordinate, survey_url)

                    if peer_review.is_included_peer:
                        peer_target_score = 0
                        for line in peer_review.peer_reviewer_position_ids:
                            for question in line.feedback_template_id.question_and_page_ids:
                                higher_score = max(question.suggested_answer_ids.mapped("answer_score"))
                                peer_target_score += higher_score
                        peer_reviews_line.append((0, 0, {'role': 'peer','weightage':peer_review.peer_weightage,'target_score':peer_target_score}))
                        template_id = self.env.ref('equip3_hr_employee_appraisals.mail_template_peer_reviews', raise_if_not_found=False)
                        if peer_review.peer_reviewer_position_ids:
                            for position in peer_review.peer_reviewer_position_ids:
                                for job in position.job_position_ids:
                                    other_peers = self.env['hr.employee'].search([('id','!=',rec.employee_id.id),('job_id','=',job.id)])
                                    if rec.employee_id.peer_feedback_ids:
                                        for var in rec.employee_id.peer_feedback_ids:
                                            if var.job_id.id == job.id and var.employee_ids:
                                                other_peers = self.env['hr.employee'].search([('id','in',var.employee_ids.ids)])
                                    if other_peers:
                                        for peer in other_peers:
                                            survey_review = self.env['survey.invite'].create(
                                                {'survey_id': position.feedback_template_id.id,
                                                'emails': str(peer.work_email), 'template_id': template_id.id})
                                            context = self.env.context = dict(self.env.context)
                                            survey_url = survey_review.survey_start_url + f"?surveyId={position.feedback_template_id.id}&performanceId={rec.id}&reviewerRole=peer&companyName=none&reviewerName={peer.name}&reviewerEmail={peer.work_email}"
                                            context.update({
                                                'email_to': peer.work_email,
                                                'reviewer_name': peer.name,
                                                'employee_name': rec.employee_id.name,
                                                'url_review': survey_url,
                                                'title': position.feedback_template_id.title,
                                                'job_position': rec.employee_id.job_id.name

                                            })
                                            template_id.send_mail(rec.id, force_send=False)
                                            template_id.with_context(context)
                                            self.send_feedbacks_wa_notification(peer, survey_url)
                                            
                    rec.peer_reviews_line_ids = peer_reviews_line
                    rec.is_sent_feedback = True
            return True
    
    def action_sent_external_feedback(self):
        for rec in self:
            if rec.employee_id.job_id:
                if rec.employee_id.job_id.performance_all_review_id:
                    peer_review = rec.employee_id.job_id.performance_all_review_id
                    if peer_review.is_included_external:
                        local_context = dict(
                            self.env.context,
                            default_appraisal_id=rec.id,
                            default_performance_review_id=rec.employee_id.job_id.performance_all_review_id.id,
                            default_survey_id=peer_review.external_feedback_template_id.id,
                        )
                        return {
                            'type': 'ir.actions.act_window',
                            'view_mode': 'form',
                            'res_model': 'hr.appraisal.external.reviewer.wizard',
                            'target': 'new',
                            'name': _('External Feedback Subject Configuration'),
                            'context': local_context,
                        }
            return True
    
    @api.depends('employee_id.job_id')
    def _compute_is_included_external_reviewers(self):
        for rec in self:
            if rec.employee_id.job_id:
                if rec.employee_id.job_id.performance_all_review_id:
                    external_review = rec.employee_id.job_id.performance_all_review_id
                    if external_review.is_included_external:
                        self.is_included_external_reviewers = True
                    else:
                        self.is_included_external_reviewers = False

    @api.depends('peer_reviews_line_ids','peer_reviews_line_ids.final_score')
    def _compute_peer_reviews_total_score(self):
        for rec in self:
            if rec.peer_reviews_line_ids:
                total = sum([data.final_score for data in rec.peer_reviews_line_ids])
                rec.peer_reviews_total_score = total
            else:
                rec.peer_reviews_total_score = 0
    
    @api.depends('peer_reviews_line_ids','peer_reviews_line_ids.weightage')
    def _compute_peer_reviews_weightage(self):
        for rec in self:
            if rec.peer_reviews_line_ids:
                total = sum([data.weightage for data in rec.peer_reviews_line_ids])
                rec.peer_reviews_weightage = total
            else:
                rec.peer_reviews_weightage = 0
    
    def _compute_feedback_result(self):
        for rec in self:
            feedback_result = self.env['survey.user_input'].sudo().search([('employee_performance_id','=',rec.id),('survey_type','=','PEER_REVIEW'),('state','=','done')])
            if feedback_result:
                rec.feedback_result_count = len(feedback_result)
    
    def action_feedback_result(self):
        feedback_result = self.env['survey.user_input'].sudo().search([('employee_performance_id','=',self.id),('survey_type','=','PEER_REVIEW'),('state','=','done')])
        feedback_ids = []
        for data in feedback_result:
            feedback_ids.append(data.id)
        view_id = self.env.ref('survey.survey_user_input_view_form').id
        if feedback_ids:
            if len(feedback_ids) > 1:
                value = {
                    'domain': [('id', 'in', feedback_ids)],
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'survey.user_input',
                    'view_id': False,
                    'type': 'ir.actions.act_window',
                    'name': _('Feedback Results'),
                    # 'res_id': feedback_ids
                }
            else:
                value = {
                    'view_mode': 'form',
                    'res_model': 'survey.user_input',
                    'view_id': view_id,
                    'type': 'ir.actions.act_window',
                    'name': _('Feedback Results'),
                    'res_id': feedback_ids and feedback_ids[0]
                }
            return value
    
    def action_external_parties(self):
        external_ids = []
        if self.external_reviewer_line_ids:
            for data in self.external_reviewer_line_ids:
                external_ids.append(data.id)
        if external_ids:
            value = {
                'domain': [('id', 'in', external_ids)],
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'appraisals.external.reviewer.line',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'name': _('External Parties'),
            }
            return value
    
    def auto_send_email_appraisals_feedback(self):        
        mail_feedback = self.env['mail.mail'].sudo().search([('message_type','=','email'),('model','=','employee.performance'),('state','=','outgoing')])
        if mail_feedback:
            for mail in mail_feedback:
                mail.send(auto_commit=True)

    @api.depends('task_challenge_line_ids','task_challenge_line_ids.final_score')
    def _compute_task_challenge_weightage_score(self):
        for rec in self:
            if rec.task_challenge_line_ids:
                total = sum([data.final_score for data in rec.task_challenge_line_ids])
                rec.task_challenge_weightage_score = total
            else:
                rec.task_challenge_weightage_score = 0
    
    @api.depends('task_challenge_line_ids','task_challenge_line_ids.weightage')
    def _compute_task_challenge_weightage(self):
        for rec in self:
            if rec.task_challenge_line_ids:
                total = sum([data.weightage for data in rec.task_challenge_line_ids])
                rec.task_challenge_weightage = total
            else:
                rec.task_challenge_weightage = 0
    
    def action_tasks_result(self):
        tasks_result = self.env['survey.user_input'].sudo().search([('employee_performance_id','=',self.id),('survey_type','=','TASKS'),('state','=','done')])
        tasks_ids = []
        for data in tasks_result:
            tasks_ids.append(data.id)
        view_id = self.env.ref('survey.survey_user_input_view_form').id
        if tasks_ids:
            if len(tasks_ids) > 1:
                value = {
                    'domain': [('id', 'in', tasks_ids)],
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
                    'res_id': tasks_ids and tasks_ids[0]
                }
            return value
    
    def action_return_to_employee(self):
        self.write({'state':'sent_to_employee'})
    
    def action_return_to_manager(self):
        self.write({'state':'sent_to_manager'})

class AppraisalApproverUser(models.Model):
    _name = 'appraisal.approver.user'

    emp_appraisal_id = fields.Many2one('employee.performance', string="Employee appraisal Id")
    name = fields.Integer('Sequence', compute="fetch_sl_no")
    user_ids = fields.Many2many('res.users', string="Approvers")
    approved_employee_ids = fields.Many2many('res.users', 'emp_appraisal_user_ids', string="Approved user")
    minimum_approver = fields.Integer(string="Minimum Approver", default=1)
    timestamp = fields.Datetime(string="Timestamp")
    approved_time = fields.Text(string="Timestamp")
    feedback = fields.Text()
    approver_state = fields.Selection([('draft', 'Draft'), ('pending', 'Pending'), ('approved', 'Approved'),
                                       ('refuse', 'Refused')], default='draft', string="State")
    approval_status = fields.Text()
    is_approve = fields.Boolean(string="Is Approve", default=False)
    #parent status
    state = fields.Selection(string='Parent Status', related='emp_appraisal_id.state')

    @api.depends('emp_appraisal_id')
    def fetch_sl_no(self):
        sl = 0
        for line in self.emp_appraisal_id.appraisal_approver_user_ids:
            sl = sl + 1
            line.name = sl

class HrAppraisalAnalysis(models.Model):
    _name = "hr.appraisal.analysis"
    _description = "Appraisal Report"
    _auto = False

    
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    performance_weight_score = fields.Float()
    competency_weight_score = fields.Float()
    overal_score = fields.Float()
    company_id = fields.Many2one('res.company', 'Company', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'hr_appraisal_analysis')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW hr_appraisal_analysis AS (
                SELECT
                    row_number() OVER () AS id,
                    line.employee_id,
                    line.performance_weight_score,
                    line.competency_weight_score,
                    line.overal_score,
                    line.company_id
                     FROM (
                        SELECT
                            he.id as employee_id,
                            ep.total_weightage_score_performance_shadow as performance_weight_score,
                            ep.total_weightage_score_shadow as competency_weight_score,
                            ep.overal_score_shadow as overal_score,
                            ep.company_id as company_id
                            
                            FROM employee_performance ep
                            LEFT JOIN hr_employee he
                            ON ep.employee_id = he.id
                            
                            
                    ) as line
                   
                )""")

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(HrAppraisalAnalysis, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(HrAppraisalAnalysis, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

class PerformanceDateRange(models.Model):
    _inherit = "performance.date.range"

    deadline = fields.Date(string='Deadline', required=True)
    performance_line_ids = fields.One2many('performance.date.range.line','performance_date_id')
    state = fields.Selection([('draft','Draft'),('running','Running'),('expire','Expire')],default="draft")
    is_hide_running = fields.Boolean()
    stage_line_ids = fields.One2many('performance.date.range.stage','evaluation_period_id')
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(PerformanceDateRange, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(PerformanceDateRange, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def action_to_running(self):
        for record in self:
            record.state = "running"
            record.is_hide_running = True
    
    
    @api.constrains('name','performance_line_ids')
    def _constrains_name(self):
        for record in self:
            if len(record.performance_line_ids) <1:
                raise ValidationError("Evaluation Component must be filled")
    
    
    @api.onchange('performance_line_ids')
    def _onchange_performance_line_ids(self):
        for record in self:
            if record.performance_line_ids:
                total = sum([line.weight for line in record.performance_line_ids])
                if total > 100:
                    raise ValidationError("Total weightage cannot greater than 100 !")
    
    @api.onchange('name')
    def _onchange_name(self):
        for rec in self:
            if not rec.stage_line_ids:
                line_list = []
                line_list.append((0,0,{'evaluation_type':"self_evaluation",
                                'level':""
                                    }))
                line_list.append((0,0,{'evaluation_type':"manager_evaluation",
                                'level':"1"
                                    }))
                rec.stage_line_ids = line_list
    
class PerformanceDateRangeLine(models.Model):
    _name = "performance.date.range.line"
    
    performance_date_id = fields.Many2one('performance.date.range')
    component = fields.Selection([('performance','Performances'),
                                  ('competency','Competency'),
                                  ('all_review',"All Review"),('task_challenges','Tasks / Challenges')])
    weight = fields.Float()
    
    @api.constrains('component')
    def _constrains_component(self):
        for record in self:
            unique_check = self.search([('id','!=',record.id),('component','=',record.component),('performance_date_id','=',record.performance_date_id.id)])
            if unique_check:
                raise ValidationError("Component must be unique !")
        
class PerformanceDateRangeStage(models.Model):
    _name = "performance.date.range.stage"
    _description = 'Evaluation Period Stages'

    evaluation_period_id = fields.Many2one('performance.date.range', ondelete='cascade')
    evaluation_type = fields.Selection([('self_evaluation','Self Evaluation'),
                                        ('manager_evaluation','Manager Evaluation')], string="Evaluation Type")
    level = fields.Selection([('1','1'),('2','2'),('3','3'),('4','4'),
                              ('5','5')], string="Level")
    
    @api.constrains('evaluation_type','level')
    def _constrains_evaluation_type(self):
        for record in self:
            type_check = self.search([('id','!=',record.id),('evaluation_type','=','self_evaluation'),('level','=',record.level),('evaluation_period_id','=',record.evaluation_period_id.id)])
            if type_check:
                raise ValidationError("Cannot select multiple Self Evaluation Evaluation Type!")
            man_level_check = self.search([('evaluation_type','=','manager_evaluation'),('evaluation_period_id','=',record.evaluation_period_id.id)])
            if not man_level_check:
                raise ValidationError("Manager Evaluation Type must be select!")
            level_check = self.search([('id','!=',record.id),('evaluation_type','=','manager_evaluation'),('level','=',record.level),('evaluation_period_id','=',record.evaluation_period_id.id)])
            if level_check:
                raise ValidationError("Level must be different!")

    


class EmployeePerformancesLine(models.Model):
    _name = 'employee.performances.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Employee Performances Line'

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    company_id = fields.Many2one(string="Current Company", comodel_name='res.company', default=_get_current_company)
    cascade_employee_ids = fields.Many2many('hr.employee')
    is_cascade = fields.Boolean(default=False)
    cascade_score = fields.Float()
    name = fields.Many2one('gamification.goal.definition', string="KPI")
    description = fields.Text('Description')
    weightage = fields.Float('WEIGHTAGE')
    key_id = fields.Many2one('performance.template', 'Template',  copy=False)
    employee_rate = fields.Float('Self-Assessment')
    employee_remark = fields.Text('Employee Remarks')
    manager_rate_1 = fields.Float('Manager Assessment 1')
    manager_remark_1 = fields.Text('Manager Remarks 1')
    manager_rate_2 = fields.Float('Manager Assessment 2')
    manager_remark_2 = fields.Text('Manager Remarks 2')
    manager_rate_3 = fields.Float('Manager Assessment 3')
    manager_remark_3 = fields.Text('Manager Remarks 3')
    manager_rate_4 = fields.Float('Manager Assessment 4')
    manager_remark_4 = fields.Text('Manager Remarks 4')
    manager_rate = fields.Float('Final Assessment')
    manager_remark = fields.Text('Final Remarks')
    performance_id = fields.Many2one('employee.performance', 'Performance Evaluation', ondelete="cascade")
    sequence = fields.Integer(string='Sequence', default=10)
    state = fields.Selection(string='Status', tracking=True, copy=False, related='performance_id.state')
    employee_id = fields.Many2one('hr.employee', 'Employee', related='performance_id.employee_id')
    date_range_id = fields.Many2one('performance.date.range',related='performance_id.date_range_id')
    kpi_target = fields.Float()
    weightage_score = fields.Float(compute='_compute_weightage_score')
    weightage_score_shadow = fields.Float()
    # achievement = fields.Float()
    achievement_score = fields.Float(compute='_compute_achievement_score')
    achievement_score_shadow = fields.Float()
    attatchment = fields.Binary()
    file_name = fields.Char()
    is_readonly = fields.Boolean(compute='_compute_is_readonly')
    cascade_line_ids = fields.One2many('employee.performances.line.cascade','parent_id')
    is_not_manager = fields.Boolean(compute='_compute_is_not_manager')
    is_submiter = fields.Boolean(compute='_compute_is_submiter')
    is_final_assesment = fields.Boolean(compute='_compute_is_final_assesment')
    kpi_comparison = fields.Selection([
        ('higher', "The higher the better"),
        ('lower', "The lower the better")
    ], default='', string="KPI Comparison")
    
    def _compute_is_not_manager(self):
        for record in self:
            if self.env.user.employee_id.id != record.performance_id.manager_id.id:
                record.is_not_manager = True
            else:
                record.is_not_manager = False
    
    @api.depends('performance_id','performance_id.next_manager_id')
    def _compute_is_submiter(self):
        for record in self:
            if self.env.user.id == record.performance_id.next_manager_id.id:
                record.is_submiter = True
            else:
                record.is_submiter = False
    
    @api.depends('performance_id','performance_id.next_manager_seq','performance_id.max_manager_seq','performance_id.next_manager_id')
    def _compute_is_final_assesment(self):
        for record in self:
            if record.performance_id.next_manager_seq == record.performance_id.max_manager_seq and self.env.user.id == record.performance_id.next_manager_id.id:
                record.is_final_assesment = True
            else:
                record.is_final_assesment = False
    
    def name_get(self):
        res = []
        for record in self:
            name = f"{record.name.name} - {record.performance_id.name} - {record.performance_id.date_range_id.name}"
            res.append((record.id, name))
        return res
    
    def cascade_line(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'performance.cascade.wizard',
            'view_type': 'form',
            'view_mode': 'form',
            'name': "Cascade KPI",
            'target': 'new',
            'context':{'default_performance_line_id':self.id,'default_date_range_id':self.date_range_id.id,'kpi_id':self.name.id}
            
        }
       
    
    
    @api.onchange('employee_rate','name')
    def _onchange_employee_rate(self):
        for record in self:
            if record.employee_rate and record.name.computation_mode != 'manually':
                record.manager_rate = record.employee_rate
    
    
    @api.depends('manager_rate','kpi_target')
    def _compute_achievement_score(self):
        for record in self:
            if record.name.condition == 'higher':
                if record.manager_rate and record.kpi_target and not record.is_cascade:
                    record.achievement_score = (record.manager_rate / record.kpi_target) * 100
                    record.achievement_score_shadow = record.achievement_score
                elif record.manager_rate and record.kpi_target and record.is_cascade:
                    record.achievement_score = ((record.manager_rate / record.kpi_target) * 100) + record.cascade_score
                    record.achievement_score_shadow = record.achievement_score
                else:
                    record.achievement_score = 0
            else:
                if record.manager_rate <= record.kpi_target:
                    record.achievement_score = 100
                else:
                    record.achievement_score = (record.kpi_target/record.manager_rate ) * 100
                    record.achievement_score_shadow = record.achievement_score
                    
                
    
    
    @api.depends('weightage','achievement_score')
    def _compute_weightage_score(self):
        for record in self:
            if record.weightage and record.achievement_score:
                final_weightage_score = (record.weightage * record.achievement_score) /100
                record.weightage_score = final_weightage_score if final_weightage_score <= record.weightage else record.weightage
                record.weightage_score_shadow = record.weightage_score
            else:
                record.weightage_score = 0
                
            
    
    @api.depends('name')
    def _compute_is_readonly(self):
        for record in self:
            if record.name:
                if record.name.computation_mode == 'manually':
                    if record.performance_id.employee_id.id == self.env.user.employee_id.id:
                        record.is_readonly = False
                    else:
                        record.is_readonly = True
                else:
                    record.is_readonly = True
            else:
                record.is_readonly = True
    
    
    
    # @api.depends('weightage','competency_match')
    # def _compute_weightage_score(self):
    #     for record in self:
    #         if record.weightage and record.competency_match:
    #             record.weightage_score = ( record.weightage * record.competency_match )/ 100
    #         else:
    #             record.weightage_score = 0
    
    


class employeeCascadeLine(models.Model):
    _name = 'employee.performances.line.cascade'
    
    
    parent_id = fields.Many2one('employee.performances.line')
    employee_id = fields.Many2one('hr.employee')
    performance_id = fields.Many2one('employee.performances.line')
    weightage_score = fields.Float(related='performance_id.achievement_score')
    assign_weightage = fields.Integer()
    
   

class EmployeeCompetenciesLine(models.Model):
    _name = 'employee.competencies.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Employee  Competencies Line'

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    company_id = fields.Many2one(string="Current Company", comodel_name='res.company', default=_get_current_company)
    name = fields.Many2one('competencies.level',string="Competency Areas")
    description = fields.Char('Description')
    key_id = fields.Many2one('competencies.template', 'Template Name', copy=False)
    performance_id = fields.Many2one('employee.performance', 'Performance Evaluation', ondelete="cascade")
    sequence = fields.Integer(string='Sequence', default=10)
    score = fields.Many2one('competencies.level.line',string="Score", domain="[('competencies_id','=',name)]")
    comment = fields.Text(string="Comment")
    manager_assessment_id_1 = fields.Many2one('competencies.level.line', domain="[('competencies_id','=',name)]", string="Manager Assessment 1")
    manager_remark_1 = fields.Text(string="Manager Remarks 1")
    manager_assessment_id_2 = fields.Many2one('competencies.level.line', domain="[('competencies_id','=',name)]", string="Manager Assessment 2")
    manager_remark_2 = fields.Text(string="Manager Remarks 2")
    manager_assessment_id_3 = fields.Many2one('competencies.level.line', domain="[('competencies_id','=',name)]", string="Manager Assessment 3")
    manager_remark_3 = fields.Text(string="Manager Remarks 3")
    manager_assessment_id_4 = fields.Many2one('competencies.level.line', domain="[('competencies_id','=',name)]", string="Manager Assessment 4")
    manager_remark_4 = fields.Text(string="Manager Remarks 4")
    final_assessment_id = fields.Many2one('competencies.level.line', domain="[('competencies_id','=',name)]")
    final_remark = fields.Text(string="Final Remarks")
    target_score_id = fields.Many2one('competencies.level.line',string="Score", domain="[('competencies_id','=',name)]")
    competency_match = fields.Float(compute='_compute_competency_match') 
    competency_match_shadow = fields.Float() 
    competency_gap = fields.Float(compute='_compute_competency_gap') 
    competency_gap_shadow = fields.Float() 
    employee_id = fields.Many2one('hr.employee', 'Employee', related='performance_id.employee_id')
    state = fields.Selection(string='Status', tracking=True, copy=False, related='performance_id.state')
    description_replace = fields.Text(string='Description', compute="compute_description")
    weightage = fields.Float()
    weightage_score = fields.Float(compute='_compute_weightage_score')
    weightage_score_shadow = fields.Float()
    is_not_manager = fields.Boolean(compute='_compute_is_not_manager')
    auto_training = fields.Boolean('Auto Training')
    is_submiter = fields.Boolean(compute='_compute_is_submiter')
    is_final_assesment = fields.Boolean(compute='_compute_is_final_assesment')
    
    def _compute_is_not_manager(self):
        for record in self:
            if self.env.user.employee_id.id != record.performance_id.manager_id.id:
                record.is_not_manager = True
            else:
                record.is_not_manager = False
    
    @api.depends('performance_id','performance_id.next_manager_id')
    def _compute_is_submiter(self):
        for record in self:
            if self.env.user.id == record.performance_id.next_manager_id.id:
                record.is_submiter = True
            else:
                record.is_submiter = False
    
    @api.depends('performance_id','performance_id.next_manager_seq','performance_id.max_manager_seq','performance_id.next_manager_id')
    def _compute_is_final_assesment(self):
        for record in self:
            if record.performance_id.next_manager_seq == record.performance_id.max_manager_seq and self.env.user.id == record.performance_id.next_manager_id.id:
                record.is_final_assesment = True
            else:
                record.is_final_assesment = False
    
    @api.depends('weightage','competency_match')
    def _compute_weightage_score(self):
        for record in self:
            if record.weightage and record.competency_match:
                record.weightage_score = ( record.weightage * record.competency_match )/ 100
                record.weightage_score_shadow = record.weightage_score
                
            else:
                record.weightage_score = 0
    
    
    @api.depends('final_assessment_id','target_score_id')
    def _compute_competency_match(self):
        for record in self:
            if record.final_assessment_id and record.target_score_id:
                record.competency_match = (record.final_assessment_id.competency_score / record.target_score_id.competency_score) * 100
                record.competency_match_shadow = record.competency_match
            else:
                record.competency_match = 0
                
    @api.depends('final_assessment_id','target_score_id')
    def _compute_competency_gap(self):
        for record in self:
            if record.final_assessment_id and record.target_score_id:
                record.competency_gap = record.final_assessment_id.competency_score - record.target_score_id.competency_score
                record.competency_gap_shadow = record.competency_gap
            else:
                record.competency_gap = 0

    @api.depends('description')
    def compute_description(self):
        for rec in self:
            rec.description_replace = rec.description
    
    def cron_auto_training(self):
        comp_gap = self.search([('competency_gap','<',0),('auto_training','=',False),])
        for rec in comp_gap:
            if rec.performance_id.state == 'done':
                for job_comp in rec.employee_id.job_id.competencies_detail_ids:
                    if rec.name == job_comp.name and job_comp.is_competency_gap and rec.competency_gap <= job_comp.minimum_gap:
                        training_list = []
                        for training in job_comp.name.training_required_ids:
                            training_list.append(training.id)
                        data = {
                            'employee_id': rec.employee_id.id,
                            'job_id': rec.employee_id.job_id.id,
                            'training_required': 'yes',
                            'course_ids': training_list,
                            'created_by_model': 'by_employee_competencies_line'
                        }
                        self.env['training.histories'].create(data)
                        rec.auto_training = True

class EmployeePeerReviewsLine(models.Model):
    _name = 'employee.peer.reviews.line'
    _description = 'Employee Peer Reviews Line'

    performance_id = fields.Many2one('employee.performance', 'Performance Evaluation', ondelete="cascade")
    role = fields.Selection([('manager', 'Manager'), ('subordinate', 'Subordinate'),
                            ('peer', 'Peer'), ('external', 'External')], string='Role')
    target_score = fields.Float(string="Target Score")
    score = fields.Float(string="Score")
    achivement_score = fields.Float(string="Achivement Score", compute="_compute_achivement_score", store=True)
    weightage = fields.Float(string="Weightage")
    final_score = fields.Float(string="Final Score", compute="_compute_final_score", store=True)

    @api.depends('score','target_score')
    def _compute_achivement_score(self):
        for rec in self:
            achivement_score = (rec.score / rec.target_score) * 100 if rec.target_score > 0 else 0
            rec.achivement_score = achivement_score

    @api.depends('achivement_score','weightage')
    def _compute_final_score(self):
        for rec in self:
            final_score = (rec.achivement_score * rec.weightage) / 100
            rec.final_score = final_score

class EmployeeTaskChallengeLine(models.Model):
    _name = 'employee.task.challenge.line'
    _description = 'Employee Task/Challenge Line'

    performance_id = fields.Many2one('employee.performance', 'Performance Evaluation', ondelete="cascade")
    task_challenge_id = fields.Many2one('survey.survey', string="Tasks/Challenges")
    target_score = fields.Float(string="Target Score")
    target_score_survey = fields.Float(string="Target Score Survey", compute="_compute_target_score_survey", store=True)
    score_survey = fields.Float(string="Score Survey")
    achivement_score = fields.Float(string="Achivement Score", compute="_compute_achivement_score", store=True)
    weightage = fields.Float(string="Weightage")
    final_score = fields.Float(string="Final Score", compute="_compute_final_score", store=True)

    @api.depends('task_challenge_id')
    def _compute_target_score_survey(self):
        for rec in self:
            target_score_survey = 0
            if rec.task_challenge_id:
                for question in rec.task_challenge_id.question_and_page_ids:
                    scores = question.suggested_answer_ids.mapped("answer_score")
                    if not scores:
                        raise ValidationError("There is no Score founded on Question : '%s' . Please verify the Survey Data!" % question.title)
                    higher_score = max(scores)
                    target_score_survey += higher_score
            rec.target_score_survey = target_score_survey
            
    @api.depends('score_survey','target_score_survey')
    def _compute_achivement_score(self):
        for rec in self:
            achivement_score = (rec.score_survey / rec.target_score_survey) * 100 if rec.target_score_survey > 0 else 0
            rec.achivement_score = achivement_score

    @api.depends('target_score','achivement_score','weightage')
    def _compute_final_score(self):
        for rec in self:
            final_score = (rec.achivement_score / rec.target_score) * rec.weightage if rec.target_score > 0 else 0
            rec.final_score = final_score

class EmployeeTrainingPlanLine(models.Model):
    _name = 'employee.training.plan.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Employee Training Plan'

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    company_id = fields.Many2one(
        string='Current Company', 
        comodel_name='res.company', 
        default=_get_current_company
    )
    competencies_areas = fields.Char()
    competencies_score = fields.Float()
    competencies_gap = fields.Float()
    course_ids = fields.Many2many('training.courses', string='Training Course')
    training_score = fields.Float()
    status = fields.Selection(selection=[
        ('to_do', 'To Do'),
        ('on_progress', 'Progress'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
        ('not_attended', 'Not Attended'),
    ], string='Status')
    performance_id = fields.Many2one('employee.performance', 'Performance Evaluation', ondelete="cascade")
    employee_id = fields.Many2one('hr.employee', 'Employee', related='performance_id.employee_id', store=True)


    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeTrainingPlanLine, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeTrainingPlanLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def custom_menu(self):
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(my_employee.id)
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Training Plan',
                'res_model': 'employee.training.plan.line',
                'view_mode': 'tree',
                'domain':[('employee_id','in',employee_ids)],
                'context':{'search_default_group_employee_id':1}
                }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Training Plan',
                'res_model': 'employee.training.plan.line',
                'view_mode': 'tree',
                'context':{'search_default_group_employee_id':1}
                }

class EmployeeDevelopmentPlanLine(models.Model):
    _name = 'employee.development.plan.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Employee Training Plan'

    def _get_current_company(self):
        return self.env['res.company']._company_default_get()

    company_id = fields.Many2one(string='Current Company', comodel_name='res.company', default=_get_current_company)
    development_method= fields.Many2one('development.method.master', string='Development Method')
    performance_id = fields.Many2one('employee.performance', 'Performance Evaluation', ondelete="cascade")
    description = fields.Char(string='Description')
    due_date = fields.Date(string='Due Date')
    pic = fields.Many2one(comodel_name='res.users', string='PIC')
    status = fields.Selection(selection=[('new', 'New'), ('in_progress', 'In Progess'),
                                        ('completed', 'Completed'),('canceled', 'Canceled')],
                                        string='Status')
    employee_id = fields.Many2one('hr.employee', 'Employee', related='performance_id.employee_id', store=True)
    
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(EmployeeDevelopmentPlanLine, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(EmployeeDevelopmentPlanLine, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    def custom_menu(self):
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager') and not self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_administrator'):
            employee_ids = []
            my_employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id),('company_id','in',self.env.company.ids)])
            if my_employee:
                    for child_record in my_employee.child_ids:
                        employee_ids.append(my_employee.id)
                        employee_ids.append(child_record.id)
                        child_record._get_amployee_hierarchy(employee_ids, child_record.child_ids, my_employee.id)
            return {
                'type': 'ir.actions.act_window',
                'name': 'Development Plan',
                'res_model': 'employee.development.plan.line',
                'view_mode': 'tree',
                'domain':[('employee_id','in',employee_ids)],
                'context':{'search_default_group_employee_id':1}
                }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Development Plan',
                'res_model': 'employee.development.plan.line',
                'view_mode': 'tree',
                'context':{'search_default_group_employee_id':1}
                }
    
    
    

class AppraisalExternalReviewerLine(models.Model):
    _name = 'appraisals.external.reviewer.line'

    performance_id = fields.Many2one('employee.performance', 'Performance Evaluation', ondelete="cascade")
    company_name = fields.Char('Company Name')
    reviewer_name = fields.Char('Reviewer Name')
    email = fields.Char('Email')
    work_phone = fields.Char('Work Phone')
    relation = fields.Char('Relation')

class EmployeeEvaluationOkrLine(models.Model):
    _name = 'employee.evaluation.okr.line'
    _description = 'Employee Evaluation OKR Line'

    performance_id = fields.Many2one('employee.performance', 'Performance Evaluation', ondelete="cascade")
    goals_id = fields.Many2one('hr.goals', string="Goal Title")
    goals_parent_id = fields.Many2one(related='goals_id.goals_parent_id', string="Goals Parents")
    weightage = fields.Float('Weightage')
    achievement_score = fields.Float('Achievement Score')
    score = fields.Float('Score', compute="compute_score", store=True)
    is_not_manager = fields.Boolean(compute='_compute_is_not_manager')
    
    def _compute_is_not_manager(self):
        for record in self:
            if self.env.user.employee_id.id != record.performance_id.manager_id.id:
                record.is_not_manager = True
            else:
                record.is_not_manager = False

    @api.depends('achievement_score','weightage')
    def compute_score(self):
        for rec in self:
            rec.score = (rec.achievement_score * rec.weightage) / 100
    
    def action_see_details(self):
        view_id = self.env.ref('equip3_hr_employee_appraisals.hr_goals_form_view').id
        value = {
            'view_mode': 'form',
            'res_model': 'hr.goals',
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'name': _('Goals'),
            'res_id': self.goals_id.id,
            'target': 'current',
        }
        return value

class EmployeeEvaluationManagerSequence(models.Model):
    _name = 'employee.evaluation.manager.sequence'
    _description="Performance Manager Sequence"

    evaluation_id = fields.Many2one('employee.performance', ondelete='cascade')
    sequence = fields.Integer()
    manager_id = fields.Many2one('res.users', string="Manager")
    is_submit = fields.Boolean(string="Is Submit")
    date = fields.Datetime('Timestamp')

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    peer_feedback_ids = fields.One2many('employee.peer.feedback', 'employee_id')

class EmployeePeerFeedback(models.Model):
    _name = 'employee.peer.feedback'

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]
    
    employee_id = fields.Many2one('hr.employee', string="Employee", ondelete="cascade")
    job_id = fields.Many2one('hr.job', string="Job Position",domain=_multi_company_domain)
    employee_ids = fields.Many2many('hr.employee', string="Employees", domain="[('job_id','=',job_id)]")

    @api.onchange('job_id')
    def onchange_job(self):
        for rec in self:
            rec.employee_ids = [(5,0,0)]