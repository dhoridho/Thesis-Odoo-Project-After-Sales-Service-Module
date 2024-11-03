from numpy import average
import werkzeug
from odoo import fields, models, api


class hashMicroInheritSurveyUserInput(models.Model):
    _inherit = 'survey.user_input'
    applicant_id = fields.Many2one('hr.applicant',"Applicant")

    applicant_name = fields.Char(related='applicant_id.partner_name',string="Applicant Name")
    job_id = fields.Many2one('hr.job','Job')
    is_use = fields.Boolean()
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, tracking=True)

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(hashMicroInheritSurveyUserInput, self).search_read(domain=domain, fields=fields, offset=offset, limit=limit, order=order)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        domain = domain or []
        domain.extend(['|',('company_id', '=', False),('company_id', 'in', self.env.companies.ids)])
        return super(hashMicroInheritSurveyUserInput, self).read_group(domain=domain, fields=fields, groupby=groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy)

    

    
    
    def write(self, vals):
        if 'disc_match_score_ids' in vals:
            score = [data[2]['match_score'] for data in vals['disc_match_score_ids']  if data[2] != False and 'match_score' in data[2] ]
            id_not_update = [data[1] for data in vals['disc_match_score_ids']  if data[2] == False]
            if id_not_update:
                 not_update_score = [data.match_score for data in self.disc_match_score_ids.filtered(lambda line:line.id in id_not_update)]
                 if not_update_score:
                     score.extend(not_update_score)
            if score:
                quadran = self.env['quadrant.score.line'].search([('survey_input_id','=',self.id)],limit=1)
                if quadran:
                    quadran.technical_test = average(score)
                    
            
        res = super(hashMicroInheritSurveyUserInput,self).write(vals)

        return res

    def next_stage_on_psy_test(self):
        for rec in self:
            setting = self.env['ir.config_parameter'].sudo().get_param('equip3_hr_recruitment_extend.is_auto_next_stage_psychological')
            if setting and rec.applicant_id and rec.score_by_amount == 0.0 and rec.survey_id.category_id.name == 'Personality & Emotional Inventory' and rec.survey_id.is_auto_next_stage:
                rec.applicant_id.pass_to_next_stage()

    def _mark_done(self):
        super(hashMicroInheritSurveyUserInput, self)._mark_done()
        # Moving applicant to next stage automatically on psychological test
        self.next_stage_on_psy_test()