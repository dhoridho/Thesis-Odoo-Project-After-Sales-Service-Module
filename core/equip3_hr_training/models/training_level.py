from odoo import api, fields, models


class TrainingLevel(models.Model):
    _name = 'training.level'
    _description = 'Training Level'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Level Name', required=True)
    # training_course_id = fields.Many2one('training.courses', string='Training Course', tracking=True, required=True)
    final_score = fields.Char(string='Final Score', readonly=True, compute='_compute_final_Score')
    f_score_1 = fields.Integer(string='Final Score From')
    f_score_2 = fields.Integer(string='Final Score To')

    description = fields.Char(string='Description')
    target = fields.Integer(string='Target')
    create_by = fields.Many2one('res.users', 'Created by', default=lambda self: self.env.user)
    create_date = fields.Date('Created on', default=fields.date.today())
    company_id = fields.Many2one('res.company', string='Company', tracking=True, default=lambda self: self.env.company)

    def _compute_final_Score(self):
        for rec in self:
            rec.final_score = str(rec.f_score_1) + "-" + str(rec.f_score_2)
