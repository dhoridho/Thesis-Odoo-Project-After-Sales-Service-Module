# Copyright (C) Softhealer Technologies.

from . import models
from odoo import api, SUPERUSER_ID

def uninstall_hook(cr, registry):
    
    env = api.Environment(cr, SUPERUSER_ID, {})
    custom_fields = env['sh.custom.field.model'].sudo().search([])
    if custom_fields:
        custom_fields.unlink()
        
    custom_tabs = env['sh.custom.model.tab'].sudo().search([])
    if custom_tabs:
        custom_tabs.unlink()