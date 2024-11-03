# -*- coding: utf-8 -*-

from odoo import models
from odoo.http import request

class IrHttp(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super(IrHttp, self).session_info()
        config_parameter = request.env['ir.config_parameter'].sudo()
        # 默认没取到就是 False
        result['app_default_superbar_lazy_search'] = config_parameter.get_param('app_default_superbar_lazy_search')
        return result
