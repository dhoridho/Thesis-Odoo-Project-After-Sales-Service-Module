# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    wa_patient_reg_message = fields.Text("Patient Registration Message",
        default="""'Dear ' + object.name + ', Your Patient Registration No. is: ' + object.code + ' in ACS Hospital. Sent by ACS HMS'""")
    wa_appointment_reg_message = fields.Text("Appointment Registration Message",
        default="""'Dear ' + object.patient_id.name + ', Your Appointment ' + object.name + ' is confirmed at ACS Hospital on ' + object.date.strftime('''%Y-%m-%d''') + '  Sent by ACS HMS'""")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: