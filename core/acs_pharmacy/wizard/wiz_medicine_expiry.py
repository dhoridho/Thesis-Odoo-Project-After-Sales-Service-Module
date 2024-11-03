# -*- coding: utf-8 -*-

from odoo import api, fields, models

class AcsMedicineExpiry(models.TransientModel):
    _name = "acs.medicine.expiry"
    _description = "Acs Medicine Expiry"

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user.id)

    def get_medicine_data(self):
        medicine_data = []
        domain = []

        if self.date_from:
            domain += [('expiration_date','>=', self.date_from)]
        if self.date_to:
            domain += [('expiration_date','<=', self.date_to)]

        madi_data = self.env['stock.production.lot'].search(domain)

        for medicine in madi_data:
            medicine_data.append({
                'name': medicine.name,
                'product_id': medicine.product_id.name,
                'quantity': medicine.product_qty,
                'expiration_date': medicine.expiration_date,
                })
        return medicine_data

    def print_pdf_report(self):
        return self.env.ref('acs_pharmacy.acs_medicine_expiry_report_action').report_action(self)

    def action_view_medicine_expiry(self):
        action = self.env["ir.actions.actions"]._for_xml_id("stock.action_production_lot_form")
        action['domain'] = [('expiration_date','>=', self.date_from),('expiration_date','<=', self.date_to)]
        return action