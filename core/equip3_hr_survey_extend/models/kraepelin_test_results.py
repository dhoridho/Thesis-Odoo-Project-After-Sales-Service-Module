from odoo import fields, models


class KraepelinTestResult(models.Model):
    _name = "kraepelin.test.result"
    _description = "Kraepelin Test Result"

    name = fields.Char(string='Parameter')
    means = fields.Char(string='Means')
    score = fields.Float(string='Score')
    label = fields.Char(string='Label')
    description = fields.Text(string="Description")
    results = fields.Char(string='Results')
    survey_user_input = fields.Many2one(
        comodel_name='survey.user_input',
        ondelete='cascade',
        string="User Input"
    )
