# -*- coding: utf-8 -*-
from odoo import api, fields, models, _

class PayslipSendEmailMessage(models.TransientModel):
	_name = 'payslip.send.email.message'

	message = fields.Text(string="Message", readonly=True, default='Payslip successfully sent to email')