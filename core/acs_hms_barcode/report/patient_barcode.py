# # -*- coding: utf-8 -*-

from odoo import api, models

class acs_hms_barcode(models.AbstractModel):
    _name = 'report.acs_hms_barcode.report_patient_barcode'
    _description = "Patient Barcode"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data if data is not None else {}
        patient = self.env['hms.patient'].browse(data.get('ids', data.get('active_ids')))
        quantity = data.get('form', {}).get('quantity', False)
        starting_position = data.get('form', {}).get('starting_position', False)
        return {
            'doc_ids': data.get('ids', data.get('active_ids')),
            'doc_model': 'hms.patient',
            'docs': patient,
            'quantity': int(quantity),
            'starting_position': int(starting_position),
            'data': dict(
                data,
            ),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: