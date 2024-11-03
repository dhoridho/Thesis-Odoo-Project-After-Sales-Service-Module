# -*- coding: utf-8 -*-

from odoo import api, models, _
from odoo.exceptions import ValidationError, UserError

class ACSSuregeryReport(models.AbstractModel):
    _name = 'report.acs_hms_operation_theater.report_acs_hms_surgery'
    _description = "ACS Surgery Report"

    @api.model
    def _get_report_values(self, docids, data=None):
        data = data if data is not None else {}
        start_date = data.get('form', {}).get('start_date', False)
        end_date = data.get('form', {}).get('end_date', False)
        ot_id = data.get('form', {}).get('ot_id', False)

        surgeries = self.env['hms.surgery'].search([('start_date','>=',start_date),('start_date','<=',end_date)])
        if not surgeries:
            raise UserError(_('No Surgery to print for selected criteria.'))
        return {
            'doc_ids': data.get('ids', data.get('active_ids')),
            'doc_model': 'hms.surgery',
            'docs': surgeries[0],
            'data': dict(
                data,
                start_date=start_date,
                end_date=end_date,
                ot_id=ot_id,
                surgeries=surgeries,
            ),
        }
