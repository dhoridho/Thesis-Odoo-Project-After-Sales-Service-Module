from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessDenied, UserError
import logging
import numpy as np
_logger = logging.getLogger(__name__)


class TransferDocAddWizard(models.TransientModel):
    _name = 'ceisa.transfer.documents.wizard'
    _description = 'Ceisa Transfer Documents Wizard'

    name = fields.Char('Name')
    ceisa_out_document_type_id = fields.Many2one('ceisa.document.type', string='', domain="[('code', 'in', ['25','261','27','41'])]")
    ceisa_in_document_type_id = fields.Many2one('ceisa.document.type', string='', domain="[('code', 'in', ['23','40','262'])]")

    def submit_ceisa_transfer_document_wizard(self):
        models_id = self._context.get('active_id', False)
        ceisa_value = []
        data_value = {}
        data_out_value = {}
        data_in_value = {}
        product_line = []

        if not models_id:
            raise UserError(
                _("Programming error: wizard action executed without active_id in context."))
        user_partner = self.env['res.partner'].browse(self.env.user.partner_id.id)
        intransfer_obj = self.env['internal.transfer'].browse(models_id)
        partner_address = '%s, %s, %s' % (intransfer_obj.destination_warehouse_id.street, intransfer_obj.destination_warehouse_id.street2, intransfer_obj.destination_warehouse_id.city)
        owner_address = '%s, %s, %s' % (intransfer_obj.source_warehouse_id.street, intransfer_obj.source_warehouse_id.street2, intransfer_obj.source_warehouse_id.city)

        if intransfer_obj.product_line_ids:
            for prod in intransfer_obj.product_line_ids:
                prod_template = prod.product_id.product_tmpl_id
                qty = prod.qty
                product_line.append((0, 0, {
                    'product_id': prod.product_id.id,
                    'product_qty': prod.qty,
                    'origin_country': intransfer_obj.company_id.country_id.id,
                    'origin_city': intransfer_obj.company_id.city_id.id,
                    'fob_price': prod_template.list_price * qty,
                    'fob_uom_price': prod_template.list_price * qty
                }))
        data_value.update({
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
            'name_statement': user_partner.name,
            'job_statement': user_partner.function,
            'place_statement': user_partner.city,
            'date_statement': fields.Date.today(),
            'valuta_id': intransfer_obj.company_id.currency_id.id,
            # 'picking_id': intransfer_obj.id,
            'internal_transfer_id': intransfer_obj.id,
            'product_line_ids': product_line,
        })

        if self.ceisa_out_document_type_id:
            data_out_value = data_value
            if self.ceisa_out_document_type_id.code == '25':
                ceisa_obj = self.env['ceisa.documents.bc25']
                data_out_value.update({
                    'type': 'bc25',
                    # 'owner_partner_id': intransfer_obj.source_warehouse_id.id,
                    # 'owner_address': owner_address,
                    # 'owner_country': intransfer_obj.source_warehouse_id.country_id.id,
                    # 'recipient_partner_id': intransfer_obj.destination_warehouse_id.id,
                    # 'recipient_address': partner_address,
                    # 'recipient_country': intransfer_obj.destination_warehouse_id.country_id.id,
                })
            elif self.ceisa_out_document_type_id.code == '261':
                ceisa_obj = self.env['ceisa.documents.bc261']
                data_out_value.update({
                    'type': 'bc261',
                    # 'owner_partner_id': intransfer_obj.source_warehouse_id.id,
                    # 'owner_address': owner_address,
                    # 'owner_country': intransfer_obj.source_warehouse_id.country_id.id,
                    # 'recipient_partner_id': intransfer_obj.destination_warehouse_id.id,
                    # 'recipient_address': partner_address,
                    # 'recipient_country': intransfer_obj.destination_warehouse_id.country_id.id,
                })
            elif self.ceisa_out_document_type_id.code == '27':
                ceisa_obj = self.env['ceisa.documents.bc27']
                data_out_value.update({
                    'type': 'bc27',
                    # 'owner_partner_id': intransfer_obj.source_warehouse_id.id,
                    # 'owner_address': owner_address,
                    # 'owner_country': intransfer_obj.source_warehouse_id.country_id.id,
                    # 'recipient_partner_id': intransfer_obj.destination_warehouse_id.id,
                    # 'recipient_address': partner_address,
                    # 'recipient_country': intransfer_obj.destination_warehouse_id.country_id.id,
                })
            elif self.ceisa_out_document_type_id.code == '41':
                ceisa_obj = self.env['ceisa.documents.bc41']
                data_out_value.update({
                    'type': 'bc41',
                    # 'owner_partner_id': intransfer_obj.source_warehouse_id.id,
                    # 'owner_address': owner_address,
                    # 'owner_country': intransfer_obj.source_warehouse_id.country_id.id,
                    # 'recipient_partner_id': intransfer_obj.destination_warehouse_id.id,
                    # 'recipient_address': partner_address,
                    # 'recipient_country': intransfer_obj.destination_warehouse_id.country_id.id,
                })

            ceisa_value.append(data_out_value)
            search_picking_document = ceisa_obj.search([('internal_transfer_id', '=', self.id)], limit=1)
            if search_picking_document:
                ceisa_out_id = search_picking_document
            else:
                ceisa_out_id = ceisa_obj.create(ceisa_value)

        ceisa_value = []
        if self.ceisa_in_document_type_id:
            data_in_value = data_value
            if self.ceisa_in_document_type_id.code == '23':
                ceisa_obj = self.env['ceisa.documents.bc23']
                data_in_value.update({
                    'type': 'bc23',
                    # 'owner_partner_id': intransfer_obj.source_warehouse_id.id,
                    # 'owner_address': owner_address,
                    # 'owner_country': intransfer_obj.source_warehouse_id.country_id.id,
                    # 'sender_partner_id': intransfer_obj.destination_warehouse_id.id,
                    # 'sender_address': partner_address,
                    # 'sender_country': intransfer_obj.destination_warehouse_id.country_id.id,
                })
            elif self.ceisa_in_document_type_id.code == '40':
                ceisa_obj = self.env['ceisa.documents.bc40']
                data_in_value.update({
                    'type': 'bc40',
                    # 'owner_partner_id': intransfer_obj.source_warehouse_id.id,
                    # 'owner_address': owner_address,
                    # 'owner_country': intransfer_obj.source_warehouse_id.country_id.id,
                    # 'sender_partner_id': intransfer_obj.destination_warehouse_id.id,
                    # 'sender_address': partner_address,
                    # 'sender_country': intransfer_obj.destination_warehouse_id.country_id.id,
                })
            elif self.ceisa_in_document_type_id.code == '262':
                ceisa_obj = self.env['ceisa.documents.bc262']
                data_in_value.update({
                    'type': 'bc262',
                    # 'owner_partner_id': intransfer_obj.source_warehouse_id.id,
                    # 'owner_address': owner_address,
                    # 'owner_country': intransfer_obj.source_warehouse_id.country_id.id,
                    # 'sender_partner_id': intransfer_obj.destination_warehouse_id.id,
                    # 'sender_address': partner_address,
                    # 'sender_country': intransfer_obj.destination_warehouse_id.country_id.id,
                })
            ceisa_value.append(data_in_value)
            search_picking_document = ceisa_obj.search([('internal_transfer_id', '=', self.id)], limit=1)
            if search_picking_document:
                ceisa_in_id = search_picking_document
            else:
                ceisa_in_id = ceisa_obj.create(ceisa_value)

        if self.ceisa_out_document_type_id:
            if self.ceisa_out_document_type_id.code == '25':
                intransfer_obj.bc25_document_id = ceisa_out_id.id
            elif self.ceisa_out_document_type_id.code == '261':
                intransfer_obj.bc261_document_id = ceisa_out_id.id
            elif self.ceisa_out_document_type_id.code == '27':
                intransfer_obj.bc27_document_id = ceisa_out_id.id
            elif self.ceisa_out_document_type_id.code == '41':
                intransfer_obj.bc41_document_id = ceisa_out_id.id

        if self.ceisa_in_document_type_id:
            if self.ceisa_in_document_type_id.code == '23':
                intransfer_obj.bc23_document_id = ceisa_in_id.id
            if self.ceisa_in_document_type_id.code == '40':
                intransfer_obj.bc40_document_id = ceisa_in_id.id
            elif self.ceisa_in_document_type_id.code == '262':
                intransfer_obj.bc262_document_id = ceisa_in_id.id

