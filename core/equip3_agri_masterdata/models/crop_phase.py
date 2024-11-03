from odoo import models, fields, api


class AgricultureCropPhase(models.Model):
    _name = 'crop.phase'
    _description = 'Crop Phase Management'

    PERIOD = [
        ('year', 'Year(s)'),
        ('month', 'Month(s)')
    ]

    name = fields.Char(string='Name', required=True)
    crop_age = fields.Integer(string='Crop Age', default=1)
    period = fields.Selection(PERIOD, string='Period')
    crop_age_str = fields.Char(string='Crop Age', compute='_get_crop_age_str')

    @api.depends('crop_age', 'period')
    def _get_crop_age_str(self):
        for crop_phase in self:
            if crop_phase.period and crop_phase.period == 'year':
                crop_phase.crop_age_str = str(crop_phase.crop_age) + " Year(s)"
            elif crop_phase.period and crop_phase.period == 'month':
                crop_phase.crop_age_str = str(crop_phase.crop_age) + " Month(s)"
            else:
                crop_phase.crop_age_str = str(crop_phase.crop_age)
