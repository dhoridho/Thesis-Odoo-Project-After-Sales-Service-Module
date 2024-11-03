from . import models
from odoo import api, SUPERUSER_ID


def _activate_assembly(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    company_ids = env['res.company'].search([])
    for company in company_ids:
        company.write({'assembly': True})
