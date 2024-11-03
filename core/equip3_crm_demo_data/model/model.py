import pytz
from datetime import datetime
from odoo import models, fields, api, tools, _
import base64
import requests
from odoo.exceptions import ValidationError


class CRMSalesTrackingHistory(models.Model):
    _inherit = 'crm.sales.tracking.history'

    @api.model
    def action_view_crm_sales_tracking(self):
        res = super(CRMSalesTrackingHistory, self).action_view_crm_sales_tracking()
        record = self.env['crm.sales.tracking.history'].browse(res['res_id'])
        sales_ids = self.env['res.users'].search([('name', 'in', ('Hanafi','Andecha'))])
        record.write({
            'sales_ids': [(6, 0, sales_ids.ids)],
            'date': datetime.strptime("2022-11-01", '%Y-%m-%d').date()
        })
        record._compute_histories()
        return res