from typing import Sequence
from odoo import fields,models,api,_
from odoo.exceptions import UserError, ValidationError
from datetime import datetime, timedelta
from ...equip3_general_features.models.approval_matrix import approvalMatrixWizard

class equp3EmployeePerformancePopupWizard(models.TransientModel):
    _name = 'performance.approve.wizard'
    feedback = fields.Text()
    performance_id = fields.Many2one('performance.planning')
    state = fields.Char()
    
    
    def get_manager_hierarchy(self, employee_manager, data, level, manager_ids):
        if not employee_manager['parent_id']['user_id']:
            return manager_ids
        while data < int(level):
            manager_ids.append(employee_manager['parent_id']['user_id']['id'])
            data += 1
            if employee_manager['parent_id']['user_id']['id']:
                self.get_manager_hierarchy(employee_manager['parent_id'], data, level, manager_ids)
                break
        return manager_ids
    
    def submit(self):
        sequence = """record.performance_id.approval_matrix_ids"""
        sequence_apply = """record.performance_id.approval_matrix_ids.filtered(lambda  line:len(line.approver_confirm) != line.minimum_approver)"""
        approval = """record.performance_id.approval_matrix_ids.filtered(lambda  line:record.env.user.id in line.approver_id.ids and len(line.approver_confirm) != line.minimum_approver and  line.sequence == min_seq)"""
        approval_matrix_wizard = approvalMatrixWizard(self,sequence,sequence_apply,approval)
        status = approval_matrix_wizard.submit(self.performance_id,{'state':'approved'},{'state':'rejected'})
        if status:
            performances = self.env['employee.performance']
            is_self_type = False
            for employee in self.performance_id.employee_ids:
                is_manager_type = False
                is_period_performances = False
                is_period_competencies = False
                is_period_all_review = False
                is_evaluation_okr = False
                period_performance_weightage = 0
                period_competencies_weightage = 0
                period_all_review_weightage = 0

                self_type = self.performance_id.period_id.stage_line_ids.filtered(lambda line:line.evaluation_type == 'self_evaluation')
                if self_type:
                    is_self_type = True
                manager_type = self.performance_id.period_id.stage_line_ids.filtered(lambda line:line.evaluation_type == 'manager_evaluation')
                data_managers = []
                man_sequence = 0
                if manager_type:
                    is_manager_type = True
                    data = 0
                    level = manager_type[0].level
                    manager_ids = []
                    manager = self.get_manager_hierarchy(employee,data,level,manager_ids)
                    for man in manager:
                        man_sequence += 1
                        data_managers.append((0, 0, {'sequence': man_sequence, 'manager_id': man}))
                
                line_performance = self.performance_id.period_id.performance_line_ids.filtered(lambda line:line.component == 'performance')
                if line_performance:
                    is_period_performances = True
                    period_performance_weightage =  line_performance.weight
                line_competencies = self.performance_id.period_id.performance_line_ids.filtered(lambda line:line.component == 'competency')
                if line_competencies:
                    is_period_competencies = True
                    period_competencies_weightage = line_competencies.weight
                line_all_review = self.performance_id.period_id.performance_line_ids.filtered(lambda line:line.component == 'all_review')
                if line_all_review:
                    is_period_all_review = True
                    period_all_review_weightage = line_all_review.weight
                
                if not employee.job_id.template_id.id and is_period_performances and employee.job_id.performance_type == "kpi":
                    raise UserError(_("You must select Performance(s) in Job Position '%s' first.") % employee.job_id.name)

                if not employee.job_id.comp_template_id.id and is_period_competencies:
                    raise UserError(_("You must select Competencie(s) in Job Position '%s' first.") % employee.job_id.name)

                performance_lines = []
                if employee.job_id.template_id and is_period_performances and employee.job_id.performance_type == "kpi":
                    performance_ids = employee.job_id.template_id.key_performance_ids
                    for line in performance_ids:
                        performance_lines.append((0, 0, {'name': line.name.id,
                                        'kpi_comparison': line.name.condition,
                                        'description': line.description,
                                        'weightage': line.weightage,
                                        'key_id': line.key_id.id,
                                        'sequence': line.sequence,
                                        'kpi_target':line.kpi_target
                                        }))

                competencies_lines = []
                if employee.job_id.comp_template_id and is_period_competencies:
                    competencies_ids = employee.job_id.comp_template_id.competencies_ids
                    for line in competencies_ids:
                        competencies_lines.append((0, 0, {'name': line.name.id,
                                        'description': line.description,
                                        'key_id': line.key_id.id,
                                        'sequence': line.sequence,
                                        'weightage':line.weightage,
                                        'target_score_id':line.target_score_id.id,
                                        }))
                okr_lines = []
                if employee.job_id.performance_type == "okr":
                    is_evaluation_okr = True
                    my_goals = self.env.ref('equip3_hr_employee_appraisals.hr_goal_types_employee')
                    okr_ids = self.env['hr.goals'].search([('evaluation_period_id','=',self.performance_id.period_id.id),('goal_types_id','=',my_goals.id),('state','=','submitted')])
                    my_okr_ids = okr_ids.filtered(lambda r: employee.id in r.assign_employee_ids.ids)
                    okr_count = len(my_okr_ids)
                    weightage = 100 / okr_count if okr_count > 0 else 0
                    for line in my_okr_ids:
                        okr_lines.append((0, 0, {'goals_id': line.id,
                                        'goals_parent_id': line.goals_parent_id.id,
                                        'achievement_score': line.achievement_score,
                                        'weightage': weightage,
                                        }))
                res = {
                    'performance_planning_id': self.performance_id.id,
                    'employee_id': employee.id,
                    'manager_id': employee.parent_id.id or False,
                    'template_id': employee.job_id.template_id.id,
                    'comp_template_id': employee.job_id.comp_template_id.id,
                    'date_range_id': self.performance_id.period_id.id,
                    'date_start': self.performance_id.date_start,
                    'date_end': self.performance_id.date_end,
                    'deadline': self.performance_id.deadline,
                    'is_period_performances': is_period_performances,
                    'is_period_competencies': is_period_competencies,
                    'is_period_all_review': is_period_all_review,
                    'is_evaluation_okr': is_evaluation_okr,
                    'period_performance_weightage': period_performance_weightage,
                    'period_competencies_weightage': period_competencies_weightage,
                    'period_all_review_weightage': period_all_review_weightage,
                    'performances_line_ids': performance_lines,
                    'competencies_line_ids': competencies_lines,
                    'okr_line_ids': okr_lines,
                    'is_self_type': is_self_type,
                    'is_manager_type': is_manager_type,
                    'max_manager_seq': man_sequence,
                    'manager_sequence_ids': data_managers,
                    'state':'draft'
                }
                performances += self.env['employee.performance'].create(res)
            if is_self_type:
                performances.action_sent_employee()
            else:
                performances.action_sent_manager()
            self.performance_id.is_hide_task_challenge = False
            
            
            
            
    