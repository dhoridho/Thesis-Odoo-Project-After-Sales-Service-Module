# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class Prescription(models.Model):
    _inherit = 'prescription.order'

    invoice_id = fields.Many2one('account.move', string='Invoice', copy=False)

    def create_invoice(self):
        if not self.prescription_line_ids:
            raise UserError(_("Please add prescription lines first."))
        product_data = []
        for line in self.prescription_line_ids:
            product_data.append({
                'product_id': line.product_id,
                'quantity': line.quantity,
            })
        inv_data = {
            'physician_id': self.physician_id and self.physician_id.id or False,
            'hospital_invoice_type': 'pharmacy',
        }
        invoice = self.acs_create_invoice(partner=self.patient_id.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        invoice.write({
            'create_stock_moves': True,
            'prescription_id': self.id,
        })
        self.sudo().invoice_id = invoice.id

    def view_invoice(self):
        invoices = self.mapped('invoice_id')
        action = self.acs_action_view_invoice(invoices)
        return action


class AccountMove(models.Model):
    _inherit = "account.move"

    prescription_id = fields.Many2one('prescription.order',  string='Prescription')
