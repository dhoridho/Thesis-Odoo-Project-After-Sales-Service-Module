from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class QuadrantCategory(models.Model):
    _name = "quadrant.category"
    _description = "Quadrant Category"

    name = fields.Char('Name', readonly=True)
    skill_score_from = fields.Integer('Skill Score From', required=True)
    skill_score_to = fields.Integer('Skill Score To', required=True)
    skill_score_display = fields.Char('Skill Score', compute='compute_skill_score_display')
    personality_score_from = fields.Integer('Personality Score From', required=True)
    personality_score_to = fields.Integer('Personality Score To', required=True)
    personality_score_display = fields.Char('Personality Score', compute='compute_personality_score_display')

    @api.constrains('skill_score_from', 'skill_score_to', 'personality_score_from', 'personality_score_to')
    def check_score_value(self):
        if self.skill_score_from < 0:
            raise ValidationError(_("Skill score 'From' can't less than 0!"))
        if self.skill_score_to < 0:
            raise ValidationError(_("Skill score 'From' can't less than 0!"))
        if self.skill_score_to < self.skill_score_from:
            raise ValidationError(_("Skill score 'To' must be greather than score 'From'!"))
        if self.personality_score_from < 0:
            raise ValidationError(_("Personality score 'From' can't less than 0!"))
        if self.personality_score_to < 0:
            raise ValidationError(_("Personality score 'From' can't less than 0!"))
        if self.personality_score_to < self.personality_score_from:
            raise ValidationError(_("Personality score 'To' must be greather than score 'From'!"))

    @api.depends('skill_score_from', 'skill_score_to')
    def compute_skill_score_display(self):
        for res in self:
            skill_display = str(res.skill_score_from) + ' - ' + str(res.skill_score_to)
            res.skill_score_display = skill_display

    @api.depends('personality_score_from', 'personality_score_to')
    def compute_personality_score_display(self):
        for res in self:
            personality_display = str(res.personality_score_from) + ' - ' + str(res.personality_score_to)
            res.personality_score_display = personality_display