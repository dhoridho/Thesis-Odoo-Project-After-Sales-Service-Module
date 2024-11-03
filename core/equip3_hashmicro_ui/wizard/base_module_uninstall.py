# -*- coding: utf-8 -*-

from odoo import models
from odoo.exceptions import ValidationError


class BaseModuleUninstall(models.TransientModel):
    _inherit = "base.module.uninstall"

    def action_uninstall(self):
        modules = self.module_id
        # if modules.name == "equip3_hashmicro_ui":
        #     raise ValidationError('Cannot uninstall the module!')
        return super(BaseModuleUninstall, self).action_uninstall()
