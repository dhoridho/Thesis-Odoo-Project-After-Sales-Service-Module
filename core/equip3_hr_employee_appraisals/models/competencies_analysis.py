from odoo import models,fields,api
from odoo import tools





class ReportKeyPerformance(models.Model):
    _name = "report.competencies.appraisal"
    _description = "Competency"
    _auto = False

    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    score = fields.Float()
    target = fields.Float()
    final_assessment = fields.Float()
    competency_match = fields.Float()
    competency_gap = fields.Float()
    weightage_score = fields.Float()
    weightage = fields.Float()
    competency_areas = fields.Many2one('competencies.level')
    company_id = fields.Many2one('res.company', 'Company', readonly=True)
   

    def init(self):
        tools.drop_view_if_exists(self.env.cr, 'report_competencies_appraisal')
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW report_competencies_appraisal AS (
                SELECT
                    row_number() OVER () AS id,
                    line.employee_id,
                    line.score,
                    line.final_assessment,
                    line.weightage,
                    line.competency_match,
                    line.competency_gap,
                    line.weightage_score,
                    line.competency_areas,
                    line.target,
                    line.company_id
                    
                     FROM (
                        SELECT
                            he.id as employee_id,
                            cll.competency_score as score,
                            final_cll.competency_score as final_assessment,
                            target_cll.competency_score as target,
                            ecl.weightage as weightage,
                            ecl.competency_match_shadow as competency_match,
                            ecl.competency_gap_shadow as competency_gap,
                            ecl.weightage_score_shadow as weightage_score,
                            cl.id as competency_areas,
                            ep.company_id as company_id
                            
                            
                            
                            FROM employee_competencies_line ecl
                            LEFT JOIN employee_performance ep
                                ON ecl.performance_id = ep.id
                            LEFT JOIN hr_employee  he
                                ON ep.employee_id = he.id
                            LEFT JOIN competencies_level_line cll
                                ON ecl.score = cll.id
                            LEFT JOIN competencies_level_line final_cll
                                ON ecl.final_assessment_id = final_cll.id
                            LEFT JOIN competencies_level_line target_cll
                                ON ecl.target_score_id = target_cll.id
                            LEFT JOIN competencies_level cl
                                ON ecl.name = cl.id
                            
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