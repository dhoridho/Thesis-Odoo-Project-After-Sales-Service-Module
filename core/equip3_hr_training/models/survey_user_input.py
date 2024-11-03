from odoo import models,api,_,fields


class equip3HrTrainingSurveyUserInput(models.Model):
    _inherit = 'survey.user_input'
    is_hr_training = fields.Boolean()
    training_id = fields.Many2one('training.conduct')
    employee_id = fields.Many2one('hr.employee')
    test_type = fields.Selection([('pre_test','Pre Test'),('post_test','Post Test')],"Test Type")
    