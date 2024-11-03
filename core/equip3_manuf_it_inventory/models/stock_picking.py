from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    is_it_inventory_warehouse = fields.Boolean()
    it_document_type_po = fields.Many2one(comodel_name='it.inventory.document.type', string='It Document Type', domain=[('document_type', '=', 'inbound')])
    it_document_type_so = fields.Many2one(comodel_name='it.inventory.document.type', string='It Document Type', domain=[('document_type', '=', 'outbound')])
    it_request_number = fields.Char(string='IT Request Number')
    it_registration_number = fields.Char(string='IT Registration Number')
    it_registration_date = fields.Datetime(string='IT Registration Date')
    ###For Ceisa Export Documents
    export_document_id = fields.Many2one('ceisa.export.documents', string='Export Documents')
    export_document_count = fields.Integer('Number of Export Documents', compute="_compute_export_documents_count")
    ###For Ceisa Import Documents
    import_document_id = fields.Many2one('ceisa.import.documents', string='Import Documents')
    import_document_count = fields.Integer('Number of Import Documents', compute="_compute_import_documents_count")
    check_second_picking_reserve = fields.Boolean('Picking Reserve', default=False)

    @api.depends('export_document_id')
    def _compute_export_documents_count(self):
        for exim in self:
            cnt_doc = 0
            self._cr.execute('''SELECT COUNT(*) AS picking FROM ceisa_export_documents 
                WHERE picking_id=%s 
                ''' % (self.id))
            count_documents = self._cr.dictfetchall()

            if count_documents:
                for record in count_documents:
                    cnt_doc = record.get('picking')
            exim.export_document_count = cnt_doc

    @api.depends('import_document_id')
    def _compute_import_documents_count(self):
        for exim in self:
            cnt_doc = 0
            self._cr.execute('''SELECT COUNT(*) AS picking FROM ceisa_import_documents 
                WHERE picking_id=%s 
                ''' % (self.id))
            count_documents = self._cr.dictfetchall()

            if count_documents:
                for record in count_documents:
                    cnt_doc = record.get('picking')
            exim.import_document_count = cnt_doc


    def action_export_document(self):
        ceisa_value = []
        entitas_line = []
        product_line = []
        seq_date = None
        user_partner = self.env['res.partner'].browse(self.env.user.partner_id.id)
        doc_type = self.env['ceisa.document.type'].search([('code', '=', '30')], limit=1)
        ceisa_obj = self.env['ceisa.export.documents']
        partner_street1 = self.partner_id.street if self.partner_id.street else ''
        partner_street2 = self.partner_id.street2 if self.partner_id.street2 else ''
        partner_street3 = self.partner_id.city if self.partner_id.city else ''
        buyer_address = '%s, %s, %s' % (partner_street1, partner_street2, partner_street3)
        company_street1 = self.company_id.street if self.company_id.street else ''
        company_street2 = self.company_id.street2 if self.company_id.street2 else ''
        company_street3 = self.company_id.city_id.name if self.company_id.city_id.name else ''
        owner_address = '%s, %s, %s' % (company_street1, company_street2, company_street3)
        ### User yang menandatangani document
        name_statement = user_partner.name
        job_statement = user_partner.function
        place_statement = user_partner.city
        date_statement = fields.Date.today()

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
            'type': 'export',
            'document_type_id': doc_type.id,
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
            'name_statement': name_statement,
            'job_statement': job_statement,
            'place_statement': place_statement,
            'date_statement': date_statement,
            'valuta_id': self.company_id.currency_id.id,
            # 'entitas_line_id': entitas_line,
            'picking_id': self.id,
            'product_line_ids': product_line,
            'owner_partner_id': self.company_id.id if self.company_id.id else '',
            'owner_identity_number': self.company_id.vat if self.partner_id.vat else '',
            'owner_address': owner_address,
            'owner_country': self.company_id.country_id.id,
            'buyer_partner_id': self.partner_id.id,
            'buyer_address': buyer_address,
            'buyer_country': self.partner_id.country_id.id,
            'recipient_partner_id': self.partner_id.id,
            'recipient_address': buyer_address,
            'recipient_country': self.partner_id.country_id.id,
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
        self.export_document_id = ceisa_id
        self._compute_export_documents_count()

        actions = self.env['ir.actions.act_window']._for_xml_id(
            'equip3_manuf_it_inventory.action_export_documents_view')
        actions.update({
            'context': {'default_picking_id': self.id},
            'res_id': ceisa_id.id,
        })
        return actions

    def action_import_document(self):
        ceisa_value = []
        entitas_line = []
        product_line = []
        doc_type = self.env['ceisa.document.type'].search([('code', '=', '20')], limit=1)
        user_partner = self.env['res.partner'].browse(self.env.user.partner_id.id)
        ceisa_obj = self.env['ceisa.import.documents']
        buyer_address = '%s, %s, %s' % (self.partner_id.street, self.partner_id.street2, self.partner_id.city if self.partner_id.city else '')
        owner_address = '%s, %s, %s' % (self.company_id.street, self.company_id.street2, self.company_id.city_id.name if self.company_id.city_id.name else '')
        ### User yang menandatangani document
        name_statement = user_partner.name
        job_statement = user_partner.function
        place_statement = user_partner.city
        date_statement = fields.Date.today()

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
            'document_type_id': doc_type.id,
            'user_id': self.env.user.id,
            'company_id': self.env.company.id,
            'name_statement': name_statement,
            'job_statement': job_statement,
            'place_statement': place_statement,
            'date_statement': date_statement,
            'valuta_id': self.company_id.currency_id.id,
            # 'entitas_line_id': entitas_line,
            'picking_id': self.id,
            'product_line_ids': product_line,
            'owner_partner_id': self.partner_id.id,
            'owner_identity_number': self.partner_id.vat if self.partner_id.vat else '',
            'owner_address': buyer_address,
            'owner_country': self.partner_id.country_id.id,
            'sender_partner_id': self.partner_id.id,
            'sender_address': buyer_address,
            'sender_country': self.partner_id.country_id.id,
            'seller_partner_id': self.partner_id.id,
            'seller_address': buyer_address,
            'seller_country': self.partner_id.country_id.id,
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
        self.import_document_id = ceisa_id
        self._compute_import_documents_count()

        actions = self.env['ir.actions.act_window']._for_xml_id(
            'equip3_manuf_it_inventory.action_import_documents_view')
        actions.update({
            'context': {'default_picking_id': self.id},
            'res_id': ceisa_id.id,
        })
        return actions

    def action_view_export_document(self):
        ceisa_obj = self.env['ceisa.export.documents']
        search_picking_document = ceisa_obj.search([('picking_id', '=', self.id), ('type', '=', 'export')], limit=1)
        if search_picking_document:
            ceisa_id = search_picking_document
        else:
            raise UserError('Cannot open the Documents.')
        actions = self.env['ir.actions.act_window']._for_xml_id(
            'equip3_manuf_it_inventory.action_export_documents_view')
        actions.update({
            'context': {'default_picking_id': self.id},
            'res_id': ceisa_id.id,
        })
        return actions

    def action_view_import_document(self):
        ceisa_obj = self.env['ceisa.import.documents']
        search_picking_document = ceisa_obj.search([('picking_id', '=', self.id), ('type', '=', 'import')], limit=1)
        if search_picking_document:
            ceisa_id = search_picking_document
        else:
            raise UserError('Cannot open the Documents.')
        actions = self.env['ir.actions.act_window']._for_xml_id(
            'equip3_manuf_it_inventory.action_import_documents_view')
        actions.update({
            'context': {'default_picking_id': self.id},
            'res_id': ceisa_id.id,
        })
        return actions
