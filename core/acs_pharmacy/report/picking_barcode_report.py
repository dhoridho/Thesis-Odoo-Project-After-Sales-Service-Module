# # -*- coding: utf-8 -*-

from odoo import api, models
 
class ACSPharmacyPickingBarcode(models.AbstractModel):
    _name = 'report.acs_pharmacy.report_picking_barcode'
    _description = "ACS Picking Barcode"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data if data is not None else {}
        picking_barcode = self.env['stock.picking.barcode'].browse(data.get('ids'))
        starting_position = data.get('form', {}).get('starting_position', False)
        return {
            'doc_ids': data.get('ids', data.get('active_ids')),
            'doc_model': 'stock.picking.barcode',
            'docs': picking_barcode,
            'starting_position': int(starting_position),
            'data': dict(
                data,
            ),
        }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: