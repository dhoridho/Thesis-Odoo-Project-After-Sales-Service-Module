# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class ContractExpired(models.TransientModel):
    _inherit = 'contract.expired'

    def get_expired_contract(self):

        expired_contract = self.env['agreement'].search([('start_date','>=',self.from_date),('expired_date','<=',self.to_date), ('property_id','!=', False)])

        if not expired_contract:
            raise UserError(_("Expired Contract is not available in this Date Range."))

        return {
            'name': 'Expire Date Contract Report',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'views': [
                (self.env.ref('equip3_property_report.agreement_expired_view_tree_report').id, 'tree'), 
                (self.env.ref('agreement_legal.partner_agreement_form_view').id, 'form')
                ],
            'res_model': 'agreement',
            'domain': [('id','in',expired_contract.ids)],
        }


        return {
        'name': _('Vehicle Request'),
        'domain': [('driver_id','=',self.id)],
        'view_type': 'form',
        'view_mode': 'tree,form',
        'res_model': 'vehicle.request',
        'view_id': False,
        'views': [(self.env.ref('abs_construction_management.view_vehicle_request_menu_tree').id, 'tree'),
                    (self.env.ref('abs_construction_management.view_vehicle_request_menu_form').id, 'form')],
        'type': 'ir.actions.act_window'
        }

    def get_xls_report(self):
        return {
        'type': 'ir.actions.act_url', 
        'url': f'/expired-contract/expired_wizard?id={self.id}&start={self.from_date}&end={self.to_date}',
        'target': 'new',
        }