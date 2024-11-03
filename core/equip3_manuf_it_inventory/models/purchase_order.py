from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def action_confirm_purchase_order(self):
        anything = super(PurchaseOrder, self).action_confirm_purchase_order()
        for record in self:
            record.picking_ids.write({
                'is_it_inventory_warehouse': record.destination_warehouse_id.is_it_inventory_warehouse
            })
        return anything

    #### For Ceisa Documents
    def action_import_document(self):
        ceisa_value = []
        entitas_line = []
        product_line = []
        user_partner = self.env['res.partner'].browse(self.env.user.partner_id.id)
        ceisa_obj = self.env['ceisa.import.documents']
        buyer_address = '%s, %s, %s' % (self.partner_id.street, self.partner_id.street2, self.partner_id.city if self.partner_id.city else '')
        owner_address = '%s, %s, %s' % (self.company_id.street, self.company_id.street2, self.company_id.city_id.name if self.company_id.city_id.name else '')
        ### User yang menandatangani document
        name_statement = user_partner.name
        job_statement = user_partner.function
        place_statement = user_partner.city
        date_statement = fields.Date.today()

        ### PPJK
        ppjk_code = self.env['ceisa.entitas.type'].search([('code', '=', '4')], limit=1).id
        entitas_line.append((0, 0, {
            'code': ppjk_code,
        }))
        ### Pemusatan
        pemusatan_code = self.env['ceisa.entitas.type'].search([('code', '=', '11')], limit=1).id
        entitas_line.append((0, 0, {
            'code': pemusatan_code,
        }))
        ### Pemilik
        owner_code = self.env['ceisa.entitas.type'].search([('code', '=', '7')], limit=1).id
        entitas_line.append((0, 0, {
            'name': self.partner_id.name,
            'code': owner_code,
            'identity_type': '',
            'number': self.partner_id.vat if self.partner_id.vat else '',
            'country_id': self.partner_id.country_id.id,
            'address': buyer_address,
        }))
        ### Pengirim
        sender_code = self.env['ceisa.entitas.type'].search([('code', '=', '9')], limit=1).id
        entitas_line.append((0, 0, {
            'name': self.partner_id.name,
            'code': sender_code,
            'identity_type': '',
            'number': self.partner_id.vat if self.partner_id.vat else '',
            'country_id': self.partner_id.country_id.id,
            'address': self.partner_id.street,
        }))
        ### Penjual
        seller_code = self.env['ceisa.entitas.type'].search([('code', '=', '10')], limit=1).id
        entitas_line.append((0, 0, {
            'name': self.company_id.name,
            'code': seller_code,
            'identity_type': '',
            'number': self.company_id.vat if self.partner_id.vat else '',
            'country_id': self.company_id.country_id.id,
            'address': owner_address,
        }))

        if self.move_ids_without_package:
            for prod in self.move_ids_without_package:
                prod_template = prod.product_id.product_tmpl_id
                qty = prod.product_uom_qty
                product_line.append((0, 0, {
                    'product_id': prod.product_id.id,
                    'product_qty': prod.product_uom_qty,
                    'origin_country': self.company_id.country_id.id,
                    'origin_city': self.company_id.city_id.id,
                    'fob_price': prod_template.list_price * qty,
                    'fob_uom_price': prod_template.list_price * qty
                }))

        ceisa_value.append({
            'type': 'import',
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
            'name_statement': name_statement,
            'job_statement': job_statement,
            'place_statement': place_statement,
            'date_statement': date_statement,
            'valuta_id': self.company_id.currency_id.id,
            'entitas_line_id': entitas_line,
            'picking_id': self.id,
            'product_line_id': product_line,
        })
        search_picking_document = ceisa_obj.search([('picking_id', '=', self.id)], limit=1)
        if search_picking_document:
            ceisa_id = search_picking_document
            if not ceisa_id.name_statement:
                ceisa_id.update({'name_statement': name_statement})
            if not ceisa_id.job_statement:
                ceisa_id.update({'job_statement': job_statement})
            if not ceisa_id.place_statement:
                ceisa_id.update({'place_statement': place_statement})
            if not ceisa_id.date_statement:
                ceisa_id.update({'date_statement': date_statement})
        else:
            ceisa_id = ceisa_obj.create(ceisa_value)
        self.exim_document_id = ceisa_id

        actions = self.env['ir.actions.act_window']._for_xml_id(
            'equip3_manuf_it_inventory.action_import_documents_view')
        actions.update({
            'context': {'default_purchase_order_id': self.id},
            'res_id': ceisa_id.id,
        })
        return actions

        # actions = self.env['ir.actions.act_window']._for_xml_id(
        #     'equip3_manuf_it_inventory.action_import_documents_view')
        # return actions