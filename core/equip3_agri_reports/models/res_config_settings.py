from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    agri_yield_maximum_target = fields.Float(default=100.0, config_parameter='equip3_agri_reports.agri_yield_maximum_target')
    agri_yield_minimum_target = fields.Float(config_parameter='equip3_agri_reports.agri_yield_minimum_target')

    @api.constrains('agri_yield_maximum_target', 'agri_yield_minimum_target')
    def _check_(self):
        for record in self:
            if not 0.0 <= record.agri_yield_maximum_target <= 100 or not 0.0 <= record.agri_yield_minimum_target <= 100:
                raise ValidationError(_('Maximum/Minimum Target must be between 0.0 and 100!'))
            elif record.agri_yield_minimum_target > record.agri_yield_maximum_target:
                raise ValidationError(_('Minimum Target cannot be bigger than Maximum Target!'))
    