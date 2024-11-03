from odoo import fields, models, api


class setSequenceWizard(models.TransientModel):
    _name = 'set.sequence.job.wizard'
    
    question_ids = fields.One2many('set.sequence.job.line.wizard','set_sequence_id')
    
    
    def submit(self):
        if self.question_ids:
            for data in self.question_ids:
                data.question_id.custom_seq = data.sequence
    
    
    
    
class setSequenceLineWizard(models.TransientModel):
    _name = 'set.sequence.job.line.wizard'
    
    set_sequence_id = fields.Many2one('set.sequence.job.wizard')
    sequence = fields.Integer()
    question_id = fields.Many2one('question.job.position')
    
    