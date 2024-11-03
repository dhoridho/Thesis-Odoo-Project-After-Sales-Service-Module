# -*- coding: utf-8 -*-
# Part of AppJetty. See LICENSE file for full copyright and licensing details.
from . import models

from odoo import api, SUPERUSER_ID

def assign_template(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env['res.company']._assign_templates()
