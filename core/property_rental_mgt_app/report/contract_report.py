# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class ContractExpired(models.TransientModel):
    _name = 'contract.expired'
    _description = "Expired Contrcat Report"

    from_date = fields.Date("From Date", required=True)
    to_date = fields.Date("To Date",  required=True)

    def get_expired_contract(self):
        contract_id = self.env['contract.details'].search([],limit=1)
        expired_contract = self.env['contract.details'].search([('to_date','>=',self.from_date),('to_date','<=',self.to_date)])

        if not expired_contract:
            raise UserError(_("Expired Contract is not available in this Date Range."))

        return {
            'name': 'Expire Date Contract Report',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_id':contract_id.id,
            'views': [(self.env.ref('property_rental_mgt_app.contract_details_tree').id, 'tree')],
            'res_model': 'contract.details',
            'domain': [('to_date','>=',self.from_date),('to_date','<=',self.to_date),('to_date','<',fields.Date.today())],
        }

    def get_pdf_report(self):
        data = {
            'ids': self.ids,
            'model': self._name,
            'form': {
                    'from_date': self.from_date,
                    'to_date': self.to_date,
                    }
                }
        return self.env.ref('property_rental_mgt_app.contract_report_action').report_action(self, data=data)

