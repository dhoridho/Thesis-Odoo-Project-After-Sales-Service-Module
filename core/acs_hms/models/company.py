# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class ResCompany(models.Model):
    _description = "Hospital"
    _inherit = "res.company"

    patient_registration_product_id = fields.Many2one('product.product', 
        domain=[('type','=','service')],
        string='Patient Registration Invoice Product', 
        ondelete='cascade', help='Registration Product')
    treatment_registration_product_id = fields.Many2one('product.product', 
        domain=[('type','=','service')],
        string='Treatment Registration Invoice Product', 
        ondelete='cascade', help='Registration Product')
    consultation_product_id = fields.Many2one('product.product', 
        domain=[('type','=','service')],
        string='Consultation Invoice Product', 
        ondelete='cascade', help='Consultation Product')
    auto_followup_days = fields.Float('Auto Followup on (Days)', default=10)
    followup_days = fields.Float('Followup Days', default=30)
    followup_product_id = fields.Many2one('product.product', 
        domain=[('type','=','service')],
        string='Follow-up Invoice Product', 
        ondelete='cascade', help='Followup Product')
    acs_followup_activity_type = fields.Many2one('mail.activity.type', 
        string='Follow-up Activity Type', 
        ondelete='cascade', help='Followup Activity Type')
    birthday_mail_template_id = fields.Many2one('mail.template', 'Birthday Wishes Template',
        help="This will set the default mail template for birthday wishes.")
    registration_date = fields.Char(string='Date of Registration')
    appointment_anytime_invoice = fields.Boolean("Allow Invoice Anytime in Appointment")
    appo_invoice_advance = fields.Boolean("Invoice before Confirmation in Appointment")
    acs_check_appo_payment = fields.Boolean(string="Check Appointment Payment Status before Accepting Request")
    appointment_usage_location_id = fields.Many2one('stock.location', 
        string='Usage Location for Consumed Products in Appointment')
    appointment_stock_location_id = fields.Many2one('stock.location', 
        string='Stock Location for Consumed Products in Appointment')
    acs_prescription_qrcode = fields.Boolean(string="Print Authetication QrCode on Presctiprion", default=True)
