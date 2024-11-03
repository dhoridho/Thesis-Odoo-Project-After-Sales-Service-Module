# -*- coding: utf-8 -*-

from odoo import api, fields, models

class PatientBarcodeWizard(models.TransientModel):
    _name = 'patient.barcode.wizard'
    _description = "Patient Barcode Print"

    @api.depends('rows', 'columns')
    def _starting_position(self):
        self.starting_position = (((self.rows-1)*2) + self.columns)

    columns = fields.Integer(string="Columns",default="1")
    rows = fields.Integer(string="Rows",default="1")
    quantity = fields.Integer(string="Quantity",default="1")
    starting_position = fields.Integer(compute=_starting_position,string="Position",readonly="True")


    def print_report(self):
        datas = {'ids': self.env.context.get('active_ids', [])}
        res = self.read([])
        res = res and res[0] or {}
        datas['form'] = res
        return self.env.ref('acs_hms_barcode.action_patient_barcode').report_action([], data=datas)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
