from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from lxml import etree
import random 


class CareerSuggestion(models.Model):
    _name = 'employee.career.suggestion'

    def _domain_emp(self):
        emp_list = []
        emp = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
        for res in self.env['hr.employee'].search([('parent_id','=',emp.id),('company_id','=',self.env.company.id)]):
            emp_list.append(res.id)
        return [('id', 'in', emp_list)]

    @api.model
    def _multi_company_domain(self):
        return [('company_id','=', self.env.company.id)]

    name = fields.Many2one('hr.employee', string='Employee Name', domain=_domain_emp)
    current_job = fields.Many2one('hr.job', string='Current Job')
    department_id = fields.Many2one('hr.department', string='Department')
    evaluation_period_ids = fields.Many2many('performance.date.range', string='Performance Evaluation Period', domain=_multi_company_domain)
    show_generate = fields.Boolean()
    is_generated = fields.Boolean()
    career_suggestion_ids = fields.One2many('employee.career.suggestion.line','suggestion_id')
    suggestion_comp_match_ids = fields.One2many('career.suggestion.competencies.match','suggestion_id')
    comp_match_count = fields.Integer('Competencies Match Count', compute="_compute_comp_match_count")
    matched_based_on = fields.Selection([('by_department','By Department'),('by_job','By Job Position')], default="by_department", string="Matched Based On")
    department_ids = fields.Many2many('hr.department',string='Departments', domain=_multi_company_domain)
    job_ids = fields.Many2many('hr.job',string="Jobs", domain=_multi_company_domain)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company.id)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(CareerSuggestion, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result
    
    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(CareerSuggestion, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)
    
    @api.model
    def fields_view_get(self, view_id=None, view_type=None,
                        toolbar=True, submenu=True):
        res = super(CareerSuggestion, self).fields_view_get(
            view_id=view_id, view_type=view_type,toolbar=toolbar,submenu=submenu)
        if  self.env.user.has_group('equip3_hr_employee_appraisals.group_hr_appraisal_manager'):
            root = etree.fromstring(res['arch'])
            root.set('create', 'true')
            root.set('edit', 'true')
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
                'name': 'Career Suggestion',
                'res_model': 'employee.career.suggestion',
                'view_mode': 'tree,form',
                'domain':[('name','in',employee_ids)],
                }
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Career Suggestion',
                'res_model': 'employee.career.suggestion',
                'view_mode': 'tree,form'
                }

    @api.model
    def create(self, values):
        values['show_generate'] = True
        return super(CareerSuggestion, self).create(values)

    @api.onchange('name')
    def onchange_employee(self):
        for rec in self:
            if rec.name:
                rec.current_job = rec.name.job_id
                rec.department_id = rec.name.department_id
    
    @api.depends('suggestion_comp_match_ids')
    def _compute_comp_match_count(self):
        for rec in self:
            count = len(rec.suggestion_comp_match_ids)
            rec.comp_match_count = count
    
    def generate_suggestion_match(self):
        most_recommended_color = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_appraisal_extend.most_recommended_color')
        current_job_color = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_appraisal_extend.current_job_color')
        self_job_interest_color = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_employee_appraisal_extend.self_job_interest_color')
        for rec in self:
            if rec.suggestion_comp_match_ids:
                remove = []
                for line in rec.suggestion_comp_match_ids:
                    remove.append((2, line.id))
                rec.suggestion_comp_match_ids = remove
            evaluations = self.env['employee.performance'].search([('employee_id','=',rec.name.id),('date_range_id','in',rec.evaluation_period_ids.ids),('state','=','done')])
            evaluations_count = len(evaluations)
            # old
            # jobs = self.env['hr.job'].sudo().search([('id','!=',rec.current_job.id)])

            # new
            jobs = self.env['hr.job'].sudo().search([])
            match_line = []
            if evaluations_count > 0:
                for job in jobs:
                    if job.comp_template_id:
                        job_comp_count = len(job.comp_template_id.competencies_ids)
                        comp_match_period = 0
                        comp_match_final = 0
                        for period in rec.evaluation_period_ids:
                            comp_match = 0
                            for evaluation in evaluations:
                                if evaluation.date_range_id.id == period.id:
                                    score = 0
                                    # list1 = [1, 2,] #For debug
                                    for line in job.comp_template_id.competencies_ids:
                                        for eval_comp in evaluation.competencies_line_ids:
                                            if line.name.id == eval_comp.name.id:
                                                score += (float(eval_comp.final_assessment_id.competency_score)/float(line.target_score_id.competency_score)) * 100
                                                # score += (float(random.choice(list1))/float(random.choice(list1))) * 100 #For debug
                                    comp_match = score/job_comp_count
                            comp_match_period += comp_match
                        comp_match_final = comp_match_period/evaluations_count
                        background_color_type = 'normal'
                        if rec.current_job.id == job.id:
                            background_color_type = 'current_job_color'
                        #Find the interest job per employee
                        if rec.name and rec.name.career_plan_ids:
                            job_interest_id = self.env['employee.career.interest'].search([('job_interest','=',job.id),('employee_id','=',rec.name.id)])
                            if job_interest_id:
                                background_color_type = 'self_job_interest_color'
                        if rec.matched_based_on == 'by_department':
                            if job.department_id.id in rec.department_ids.ids:
                                match_line.append((0, 0, {'job_id': job.id,
                                                    'department_id': job.department_id.id,
                                                    'background_color_type':background_color_type,
                                                    'competency_match': comp_match_final
                                                    }))
                        else:
                            if job.id in rec.job_ids.ids:
                                match_line.append((0, 0, {'job_id': job.id,
                                                    'department_id': job.department_id.id,
                                                    'background_color_type':background_color_type,
                                                    'competency_match': comp_match_final
                                                    }))
                rec.suggestion_comp_match_ids = match_line
                if len(rec.suggestion_comp_match_ids) > 0:
                    #Find the most recommended Job
                    suggestion_comp_match_reverse_ids = rec.suggestion_comp_match_ids.sorted("competency_match", reverse=True)
                    most_recommended_id = suggestion_comp_match_reverse_ids[0]
                    most_recommended_id.write({'background_color_type':'most_recommended_color'})
            rec.is_generated = True
    
class CareerSuggestionLine(models.Model):
    _name = 'employee.career.suggestion.line'

    suggestion_id = fields.Many2one('employee.career.suggestion', ondelete='cascade')
    competencies_match_id = fields.Many2one('career.suggestion.competencies.match', string='Job Suggestion')
    job_id = fields.Many2one('hr.job', string='Job Position')
    department_id = fields.Many2one('hr.department', string='Department')
    competency_match = fields.Float('Competency Match (%)')
    # task_id = fields.Many2one('survey.survey', string='Task', domain="[('state','=','open')]")
    task_ids = fields.Many2many('survey.survey', string='Task', domain="[('state','=','open')]")
    deadline = fields.Date('Deadline', required=True, default=fields.Datetime.now)

    @api.onchange('competencies_match_id')
    def onchange_employee(self):
        for rec in self:
            if rec.competencies_match_id:
                rec.job_id = rec.competencies_match_id.job_id
                rec.department_id = rec.competencies_match_id.department_id
                rec.competency_match = rec.competencies_match_id.competency_match

class CareerSuggestionCompetenciesMatch(models.Model):
    _name = 'career.suggestion.competencies.match'
    _rec_name = 'job_id'

    suggestion_id = fields.Many2one('employee.career.suggestion', ondelete='cascade')
    job_id = fields.Many2one('hr.job', string='Job Position')
    department_id = fields.Many2one('hr.department', string='Department')
    competency_match = fields.Float('Competency Match (%)')
    background_color_type = fields.Selection([('normal','Normal'),('most_recommended_color','Most Recommended Color'),('current_job_color','Current Job Color'),('self_job_interest_color','Self Job Interest Color')], default="normal", string="BG Color Type")
    color = fields.Integer('Color', compute='_get_color')
    link_task_id = fields.Many2one('survey.survey', string='Task', domain="[('state','=','open')]")
    link_deadline = fields.Date('Deadline', default=fields.Datetime.now)
    
    def _get_color(self):
        for rec in self:
            if rec.background_color_type ==  'most_recommended_color':
                rec.color = 2
            elif rec.background_color_type == 'current_job_color':
                rec.color = 3
            elif rec.background_color_type == 'self_job_interest_color':
                rec.color = 4
            else:
                rec.color = 1
