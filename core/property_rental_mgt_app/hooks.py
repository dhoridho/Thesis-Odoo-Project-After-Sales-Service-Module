# -*- coding : utf-8 -*-

from odoo import SUPERUSER_ID
from odoo import api


def post_init_hook(cr, registry):

    env = api.Environment(cr, SUPERUSER_ID, {})
    cr.execute("""
                update ir_model_data set noupdate=False where
                model ='ir.rule' """)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: