from odoo import fields,models,api

class DiscPersonalityRoot(models.Model):
    _name = 'disc.personality.root'
    _order = 'sequence'
    _rec_name = 'personality'
    sequence = fields.Integer("Sequence")
    personality = fields.Char()
    personality_ids = fields.One2many('disc.personality.line','disc_personality_root')




class DiscPersonality(models.Model):
    _name = 'disc.personality.line'
    personality = fields.Char()
    personality_en = fields.Char()
    disc_personality_root = fields.Many2one('disc.personality.root')






