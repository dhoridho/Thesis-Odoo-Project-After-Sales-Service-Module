# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError
from odoo.addons.izi_data.models.common.izi_tools import IZITools

class IZITools(models.TransientModel):
    _inherit = 'izi.tools'

    def check_su(self):
        if not (self.user_has_groups('base.group_system') or self.env.su):
            raise UserError('Access Restricted Only For Hashmicro Administrator!')

    IZITools.check_su = check_su