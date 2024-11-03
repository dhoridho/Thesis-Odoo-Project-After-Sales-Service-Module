from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HRJob(models.Model):
    _inherit = 'hr.job'
    _description = 'HR Job'

    course_ids = fields.Many2many('training.courses', string='Training Required')
