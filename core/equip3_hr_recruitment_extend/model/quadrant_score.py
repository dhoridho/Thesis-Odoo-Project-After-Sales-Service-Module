from odoo import api, fields, models, _

class QuadrantScore(models.Model):
    _name = "quadrant.score"
    _rec_name = "applicant_id"
    _description = "Quadrant Score"

    applicant = fields.Many2one("hr.applicant", string="Applicant")
    applicant_id = fields.Char("Applicant's ID")
    applicant_name = fields.Char("Applicant's Name")
    applicant_email = fields.Char("Email")
    job_id = fields.Many2one("hr.job", string="Applied Job")
    category_id = fields.Many2one("quadrant.category", string="Category", compute="compute_quadrant_category", store=True)
    line_ids = fields.One2many("quadrant.score.line", "quadrant_score_id")

    @api.model
    def get_all_quadrant_score(self):
        result = []
        datas = self.env['quadrant.score'].search([])
        for data in datas:
            if not data.applicant_name or not data.category_id.name:
                continue
            line = []
            for data_line in data.line_ids:
                if data_line.index and data_line.name:
                    text_line = (data_line.name or '-')+' Index : '+ str(data_line.index)
                    line.append(text_line)
            if not line:
                continue
            result.append({
                'id':data.id,
                'name':data.applicant_name,
                'category_name':data.category_id.name,
                'line':line
            })
        return result

    @api.depends('line_ids.index')
    def compute_quadrant_category(self):
        for res in self:
            skills_index = 0
            personality_index = 0
            if res.line_ids:
                for line in res.line_ids:
                    if line.name == "Skills":
                        skills_index += line.index
                    elif line.name == "Personality":
                        personality_index += line.index
            quadrant_category = self.env['quadrant.category'].sudo().search(
                [('skill_score_from', '<=', skills_index),
                ('skill_score_to', '>=', skills_index),
                ('personality_score_from', '<=', personality_index),
                ('personality_score_to', '>=', personality_index)], limit=1)
            if quadrant_category:
                res.category_id = quadrant_category.id
            else:
                res.category_id = False

class QuadrantScoreLine(models.Model):
    _name = "quadrant.score.line"

    applicant_id = fields.Many2one('hr.applicant')
    quadrant_score_id = fields.Many2one("quadrant.score")
    survey_input_id  = fields.Many2one('survey.user_input')
    name = fields.Char("Indicator")
    technical_test = fields.Integer("Technical Test")
    interview = fields.Integer("Interview")
    index = fields.Integer("index", compute="compute_index_score", store=True)

    @api.depends('technical_test', 'interview')
    def compute_index_score(self):
        for res in self:
            res.index = (res.technical_test + res.interview) / 2