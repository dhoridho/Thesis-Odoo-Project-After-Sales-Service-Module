from odoo import models,fields,api
from odoo import tools





class ReportKeyPerformance(models.Model):
    _name = "report.key.performance.appraisal"
    _description = "Performance"
    _auto = False

    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    employee_rate = fields.Float('Self Assessment')
    manager_rate = fields.Float('Final Assessment')
    target = fields.Float()
    weightage = fields.Float()
    assessment_score = fields.Float()
    weightage_score = fields.Float()
    job_id = fields.Many2one('hr.job')
    kpi_id = fields.Many2one('gamification.goal.definition')
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
   

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'report_key_performance_appraisal')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW report_key_performance_appraisal AS (
                SELECT
                    row_number() OVER () AS id,
                    line.employee_id,
                    line.employee_rate,
                    line.manager_rate,
                    line.weightage,
                    line.assessment_score,
                    line.weightage_score,
                    line.job_id,
                    line.kpi_id,
                    line.target,
                    line.company_id
                    
                     FROM (
                        SELECT
                            he.id as employee_id,
                            epl.employee_rate as employee_rate,
                            epl.manager_rate as manager_rate,
                            epl.weightage as weightage,
                            epl.achievement_score_shadow as assessment_score,
                            epl.weightage_score_shadow as weightage_score,
                            hj.id as job_id,
                            ggd.id as kpi_id,
                            epl.kpi_target as target,
                            ep.company_id as company_id
                            
                            
                            FROM employee_performances_line epl
                            LEFT JOIN employee_performance ep
                                ON epl.performance_id = ep.id
                            LEFT JOIN hr_employee  he
                                ON ep.employee_id = he.id
                            LEFT JOIN hr_job hj
                                ON he.job_id = hj.id
                            LEFT JOIN gamification_goal_definition ggd
                                ON epl.name = ggd.id
                            
                    ) as line
                   
                )""")
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain += [('company_id', 'in', self.env.context.get('allowed_company_ids'))]

        result = super(ReportKeyPerformance, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)
        return result

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        context = self.env.context
        
        if context.get('allowed_company_ids'):
            domain.extend([('company_id', 'in', self.env.context.get('allowed_company_ids'))])
        return super(ReportKeyPerformance, self).read_group(domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)