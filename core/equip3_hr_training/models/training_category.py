from odoo import api, fields, models
from odoo.exceptions import ValidationError


class TrainingCategory(models.Model):
    _name = 'training.category'
    _description = 'Training Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Category Name', tracking=True, required=True)
    parent_category_id = fields.Many2one('parent.category', string='Parent Category')
    # evaluation_type = fields.Selection(
    #     [('questionnaire', 'Questionnaire'), ('pretest', 'Pretest'), ('postest', 'Postest')], string='Evaluation Type',
    #     tracking=True, default='questionnaire', required=True)
    create_by = fields.Many2one('res.users', 'Created by', default=lambda self: self.env.user)
    create_date = fields.Date('Created on', default=fields.date.today())
    company_id = fields.Many2one('res.company', string='Company', tracking=True, default=lambda self: self.env.company)
