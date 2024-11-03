from odoo import api, fields, models, _


class PosConfig(models.Model):
    _inherit = "pos.config"

    ph_machine_identification_number = fields.Char('PH Machine Identification Number')
    is_ph_enable_ptu_number = fields.Boolean('PH Enable PTU Number ?')
    ph_ptu_number = fields.Char('PH PTU Number')
    ph_ptu_issued_date = fields.Date('PTU Issued Date')
    ph_ptu_valid_date = fields.Date('PTU Valid Date')
    is_ph_training_mode = fields.Boolean('PH Training Mode')