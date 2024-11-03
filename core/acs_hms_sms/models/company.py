# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    patient_registartion_sms = fields.Text("Patient Registartion SMS",
        default="""'Dear ' + object.name + ', Your Patient Registartion No. is: ' + object.code + ' in ACS Hospital. Sent by ACS HMS'""")
    appointment_registartion_sms = fields.Text("Appointment Registartion SMS",
        default="""'Dear ' + object.patient_id.name + ', Your Appointment ' + object.name + ' is confirmed at ACS Hospital on ' + object.date.strftime('''%Y-%m-%d''') + '  Sent by ACS HMS'""")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: