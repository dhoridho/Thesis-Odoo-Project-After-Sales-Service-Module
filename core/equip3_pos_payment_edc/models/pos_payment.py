# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PosPayment(models.Model):
    _inherit = "pos.payment"

    is_payment_edc = fields.Boolean('EDC')
    approval_code = fields.Char('Approval Code')
    installment_tenor = fields.Char('Installment Tenor')
    installment_amount = fields.Char('Installment Monthly Amount')


    @api.model
    def create(self, vals):
        res = super(PosPayment, self).create(vals)
        
        if vals.get('installment_tenor'):
            installment_tenor = vals['installment_tenor']
            if installment_tenor == '01':
                installment_tenor = installment_tenor + ' Month'
            else:
                installment_tenor = installment_tenor + ' Months'
            vals['installment_tenor'] = installment_tenor

        return res