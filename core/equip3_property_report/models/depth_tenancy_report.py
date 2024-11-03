# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class DepthTenancyReport(models.TransientModel):
    _name = 'depth.tenancy'
    _description = "In Depth Tenancy Reporting"

    from_date = fields.Date("Start Date", required=True)
    to_date = fields.Date("End Date",  required=True)
    renter_ids = fields.Many2many('res.partner', string="Renter", domain="[('partner_type','=','renter')]")


    def get_pdf_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                    'from_date': self.from_date,
                    'to_date': self.to_date,
                    'rental_ids': self.renter_ids.ids,
                    }
                }
        return self.env.ref('equip3_property_report.in_depth_tenancy_report_print_action').report_action(self, data=data)

