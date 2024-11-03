
from odoo import models,fields
from odoo.exceptions import ValidationError


class surveyDiscVariables(models.Model):
    _name = 'survey.disc.variables'
    _rec_name = 'personality'
    sequence = fields.Integer()
    code = fields.Char()
    personality = fields.Many2one('disc.personality.root')
    personality_description = fields.Text()
    personality_description_en = fields.Text()
    job_matches = fields.Text()
    job_suggestion = fields.Many2many('hr.job')
    job_suggestion_ids = fields.One2many('survey.disc.job.suggestion','disc_variable_id')
    
    def write(self, vals):
        if 'job_suggestion_ids' in vals:
            job_data = []
            data_not_update = []
            data_update = []
            for line_data in vals['job_suggestion_ids']:
                if not line_data[2]:
                    data_not_update.append(line_data[1])
                if line_data[2]:
                    if 'job_suggestion' in line_data[2]:
                        if line_data[2]['job_suggestion']:
                            data_update.append(line_data[1])
                            job_data.extend(line_data[2]['job_suggestion'][0][2])
            if job_data:
                if data_not_update:
                    for not_update in self.job_suggestion_ids.filtered(lambda line:line.id in data_not_update and line.id not in data_update):
                        job_data.extend(not_update.job_suggestion.ids)
            if len(job_data) != len(set(job_data)):
                raise ValidationError("Job suggestion must be unique !")
                
            
                
        return super(surveyDiscVariables,self).write(vals)
    


class surveyDiscVariableJobSuggestion(models.Model):
    _name = 'survey.disc.job.suggestion'
    disc_variable_id = fields.Many2one('survey.disc.variables')
    job_suggestion = fields.Many2many('hr.job')
    mask_public_self = fields.Integer()
    core_private_self = fields.Integer()
    mirror_perceived_self = fields.Integer()
