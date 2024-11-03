
from odoo import models, fields, api, _
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.exceptions import ValidationError
import datetime
import json
from odoo.addons.ks_dashboard_ninja.lib.ks_date_filter_selections import ks_get_date, ks_convert_into_local, \
    ks_convert_into_utc
from odoo.tools.safe_eval import safe_eval
import locale
from dateutil.parser import parse

class KsDashboardNinjaBoard(models.Model):
    _inherit = 'ks_dashboard_ninja.board'
    def ks_get_grid_config(self):
        res = super(KsDashboardNinjaBoard, self).ks_get_grid_config()
        res = res[0]
        return res

