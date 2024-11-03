from odoo import api, fields, models,_
from odoo.exceptions import ValidationError


class MeetingSummaryTempalte(models.Model):
    _name = 'summary.template'
    _description = 'Meeting Summary Template'

    name = fields.Char(string='Name', required=True)
    line_ids = fields.One2many(comodel_name='summary.template.line', inverse_name='template_id', string='Details')

    @api.constrains('line_ids')
    def _constrains_line_ids(self):
        if self.line_ids and len(self.line_ids) > 10:
            raise ValidationError(_("Questions up to 10 only"))


class SummaryTemplateLine(models.Model):
    _name = 'summary.template.line'
    _description = 'Details for Meeting Summary Template'

    template_id = fields.Many2one(comodel_name='summary.template', string='Summary Template')
    name = fields.Text(string='Question', required=True)
    min_char = fields.Integer(string='Min Char', required=True)
    is_required = fields.Boolean(string='Required')
    
    
    
    

    
