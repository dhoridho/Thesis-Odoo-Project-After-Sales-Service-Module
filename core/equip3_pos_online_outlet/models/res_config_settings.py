# -*- coding: utf-8 -*-

from odoo import api, fields, models
import pytz

# put POSIX 'Etc/*' entries at the end to avoid confusing users
_tzs = [(tz, tz) for tz in sorted(pytz.all_timezones, key=lambda tz: tz if not tz.startswith('Etc/') else '_')]
def _tz_get(self):
    return _tzs

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    
    oloutlet_timezone = fields.Selection(_tz_get, string='Timezone', 
        config_parameter='base_setup.oloutlet_timezone', 
        default='Asia/Jakarta')