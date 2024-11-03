from odoo import fields,api,models

class DiscScoringMatrix(models.Model):
    _name = 'disc.scoring.matrix'
    name = fields.Char()
    disc_matrix_line_ids = fields.One2many('disc.scoring.matrix.line','disc_matrix_id')



class DiscScoringMatrixline(models.Model):
    _name = 'disc.scoring.matrix.line'
    disc_matrix_id = fields.Many2one('disc.scoring.matrix')
    score = fields.Integer()
    d_field = fields.Float(string="D")
    i_field = fields.Float(string="I")
    s_field = fields.Float(string="S")
    c_field = fields.Float(string="C")
    is_line_1 = fields.Boolean()
    is_line_2 = fields.Boolean()
    is_line_3 = fields.Boolean()
