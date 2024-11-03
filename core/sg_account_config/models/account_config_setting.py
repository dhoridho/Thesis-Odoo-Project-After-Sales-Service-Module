from odoo import fields, models


class HrLeaveConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_sg_bank_reconcile = fields.Boolean("Manage Bank Reconciliation and \
        Bank Statements", help="This help to Reconcile bank statement")
    module_sg_dbs_giro = fields.Boolean("Generate DBS GIRO file for Employee \
        salary payments", help="This help to generate Dbs giro file for \
        salary payment upload to bank's site.")
