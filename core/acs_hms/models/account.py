# -*- coding: utf-8 -*-

from odoo import api,fields,models,_


class AccountMove(models.Model):
    _inherit = 'account.move'

    ref_physician_id = fields.Many2one('res.partner', ondelete='restrict', string='Referring Physician', 
        index=True, help='Referring Physician', readonly=True, states={'draft': [('readonly', False)]})
    appointment_id = fields.Many2one('hms.appointment',  string='Appointment', readonly=True, states={'draft': [('readonly', False)]})
    hospital_invoice_type = fields.Selection(selection_add=[('appointment', 'Appointment'), ('treatment','Treatment')])
