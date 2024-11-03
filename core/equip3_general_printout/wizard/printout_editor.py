
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _


class PrintoutEditor(models.TransientModel):
    _name = 'printout.editor'

    name = fields.Char(compute='_compute_purchase_order_name', store=True)
    purchase_order_ids = fields.Many2many('purchase.order', string='Purchase Order')
    purchase_order_header_ids = fields.Many2many(
        'ir.model.fields', 
        'ir_model_fields_header_po_rel',
        'editor_id', 'field_id', string="Selected Fields",
        domain=[
                ('model', '=', 'purchase.order'),
                ('name', 'in', (
                    'partner_id',
                    'partner_ref',
                    'visible_eval',
                    'partner_invoice_id',
                    'product_brand_ids',
                    'sh_purchase_barcode_mobile',
                    'currency_id',
                    'company_id',
                    'branch_id',
                    'analytic_account_group_ids',
                    'sh_sale_order_id',
                    'date_order',
                    'date_planned',
                    'date_approve',
                    'destination_warehouse_id',
                    'discount_type',
                    'origin',
                    'product_template_id',
                    'name',
                    "name2",
                    'create_uid',
                    'custom_checklist_template_ids',
                    'custom_checklist',
                    'remaining_progress',
                    'progress_paid',
                    'rent_duration',
                    'expected_return_date',
                    'create_date',
                    'user_id',
                    'team_id',
                    'incoterm_id',
                    'payment_term_id',
                    'fiscal_position_id',
                    'vendor_payment_terms',
                    'service_level_agreement_id',
                    
                ))
            ])
    po_header_filter_ids = fields.One2many('printout.editor.lines', 'header_filter_printout_id',
            string='Field Filter')
    purchase_order_table_ids = fields.Many2many(
        'ir.model.fields', 
        'ir_model_fields_table_po_rel',
        'editor_id', 'field_id',
        string="Selected Fields",
        domain=[
            ('model', '=', 'purchase.order.line'),
            ('name', 'in', (
                'product_id',
                'name',
                'date_received',
                'date_planned',
                'destination_warehouse_id',
                'analytic_tag_ids',
                'discount_method',
                'discount_amount',
                'agreement_id',
                'reference_purchase_price',
                'cost_saving',
                'last_purchased_price',
                'last_customer_purchase_price',
                'avg_price',
                'current_qty',
                'incoming_stock',
                'purchase_req_budget',
                'realized_amount',
                'sh_tender_note',
                'product_qty',
                'qty_invoiced',
                'qty_received',
                'product_uom',
                'price_unit',
                'taxes_id',
                'price_total',
                'date_planned',
                'delivery_ref',
                'order_id',
                'price_tax',
                'price_subtotal',
                'state_delivery',
                'state_inv',
                'status',
                'vendor_bills_ref',
                'image_256',
                'sequence2',
            ))
        ])
    purchase_order_table_filter_ids = fields.One2many(
        'printout.editor.lines', 'table_filter_printout_id',
        string='Field Filter Table')
    purchase_order_footer_ids = fields.Many2many(
        'ir.model.fields', 
        'ir_model_fields_footer_po_rel',
        'editor_id', 'field_id',
        string="Selected Fields",
        domain=[
            ('model', '=', 'purchase.order'),
            ('name', 'in', (
                'discount_method',
                'discount_amount',
                'payment_term_id',
                'term_condition',
                'amount_untaxed',
                'discount_amt',
                'amount_tax',
                'amount_total',
                'sign_on',
                'digital_sign',
                'sign_by',
                'designation',
            ))
        ])
    purchase_order_footer_filter_ids = fields.One2many(
        'printout.editor.lines', 'footer_filter_printout_id',
        string='Field Filter Footer')
    template_id = fields.Many2one('purchase.order.template', string="Template")
    orientation = fields.Selection([
        ('potrait', 'Potrait'),
        ('landscape', 'Landscape')
    ], string="Orientation", default='potrait')
    paper_size_format = fields.Selection([
        ('Letter', 'Letter : 21.59 cm X 27.94 cm'),
        ('Tabloid', 'Tabloid : 27.94 cm X 43.18 cm'),
        ('Legal', 'Legal : 21.59 cm X 35.56 cm'),
        ('Folio', 'Statement : 13.97 cm X 21.59 cm'),
        ('Executive', 'Executive : 18.42 cm X 42 cm'),
        ('A3', 'A3 : 29.7 cm X 42 cm'),
        ('A4', 'A4 : 21 cm X 29.7 cm'),
        ('A5', 'A5 : 14.8 cm X 21 cm'),
        ('B4', 'B4 (JIS) : 25.7 cm X 36.4 cm'),
        ('B5', 'B5 (JIS) : 18.2 cm X 25.7 cm'),
    ], string="Size")
    preview = fields.Html(compute='_compute_preview',
                          sanitize=False,
                          sanitize_tags=False,
                          sanitize_attributes=False,
                          sanitize_style=False,
                          sanitize_form=False,
                          strip_style=False,
                          strip_classes=False)

    @api.depends('purchase_order_ids')
    def _compute_purchase_order_name(self):
        for rec in self:
            rec.name = ','.join(rec.purchase_order_ids.mapped('name'))

    @api.onchange('purchase_order_header_ids')
    def onchange_purchase_order_header_ids(self):
        po_header_filter_ids = self.po_header_filter_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.po_header_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.purchase_order_header_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.purchase_order_header_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.po_header_filter_ids = data
    
    def update_sequence_purchase_order_header_ids(self,template):
        data = [(5,0,0)]
        for po_header in template.purchase_order_header_sequence_ids:
            vals = {
                'field_id':po_header.field_id.id,
                'sequence':po_header.sequence,
            }
            data.append((0,0,vals))
        self.po_header_filter_ids = data

    @api.onchange('purchase_order_table_ids')
    def onchange_purchase_order_table_ids(self):
        purchase_order_table_ids = self.purchase_order_table_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.purchase_order_table_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.purchase_order_table_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.purchase_order_table_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.purchase_order_table_filter_ids = data
    
    def update_sequence_purchase_order_table_ids(self,template):
        data = [(5,0,0)]
        for po_table in template.purchase_order_table_sequence_ids:
            vals = {
                'field_id':po_table.field_id.id,
                'sequence':po_table.sequence,
            }
            data.append((0,0,vals))
        self.purchase_order_table_filter_ids = data

    @api.onchange('purchase_order_footer_ids')
    def onchange_purchase_order_footer_ids(self):
        purchase_order_footer_ids = self.purchase_order_footer_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.purchase_order_footer_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.purchase_order_footer_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.purchase_order_footer_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.purchase_order_footer_filter_ids = data
    
    def update_sequence_purchase_order_footer_ids(self,template):
        data = [(5,0,0)]
        for po_footer in template.purchase_order_footer_sequence_ids:
            vals = {
                'field_id':po_footer.field_id.id,
                'sequence':po_footer.sequence,
            }
            data.append((0,0,vals))
        self.purchase_order_footer_filter_ids = data

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res['purchase_order_ids'] = [(6, 0, self._context.get('active_ids'))]
        return res

    @api.onchange('orientation', 'paper_size_format')
    def _onchange_orientation(self):
        paperformat_id = False
        if self.orientation == "potrait" and self.paper_size_format in ('Tabloid', 'A3'):
            paperformat_id = self.env.ref('equip3_general_printout.paperformat_printout_editor_potrait_tabloid')
        elif self.orientation == 'potrait' and self.paper_size_format == 'B4':
            paperformat_id = self.env.ref('equip3_general_printout.paperformat_printout_editor_potrait_b4')
        elif self.orientation == "potrait" and self.paper_size_format not in ('Tabloid', 'A3', 'B4'):
            paperformat_id = self.env.ref('equip3_general_printout.paperformat_printout_editor_potrait')
        elif self.orientation == 'landscape' and self.paper_size_format not in ('Tabloid', 'Legal', 'Folio', 'A3', 'B4'):
            paperformat_id = self.env.ref('equip3_general_printout.landscape_paperformat_printout_editor')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Tabloid':
            paperformat_id = self.env.ref('equip3_general_printout.landscape_paperformat_printout_editor_tabloid')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Legal':
            paperformat_id = self.env.ref('equip3_general_printout.landscape_paperformat_printout_editor_legal')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Folio':
            paperformat_id = self.env.ref('equip3_general_printout.landscape_paperformat_printout_editor_statement')
        elif self.orientation == 'landscape' and self.paper_size_format == 'A3':
            paperformat_id = self.env.ref('equip3_general_printout.landscape_paperformat_printout_editor_a3')
        elif self.orientation == 'landscape' and self.paper_size_format == 'B4':
            paperformat_id = self.env.ref('equip3_general_printout.landscape_paperformat_printout_editor_b4')

        if self.paper_size_format and paperformat_id:
            paperformat_id.format = self.paper_size_format
            report_id = self.env.ref('equip3_general_printout.report_printout_editor')
            report_id.paperformat_id = paperformat_id.id
            self._compute_preview()

    @api.onchange('template_id')
    def _onchange_template(self):
        if self.template_id and \
            (self.template_id.purchase_order_header_ids or 
            self.template_id.purchase_order_table_ids or 
            self.template_id.purchase_order_footer_ids):
            self.purchase_order_header_ids = [(6, 0, self.template_id.purchase_order_header_ids.ids)]
            self.purchase_order_table_ids = [(6, 0, self.template_id.purchase_order_table_ids.ids)]
            self.purchase_order_footer_ids = [(6, 0, self.template_id.purchase_order_footer_ids.ids)]
            self.orientation = self.template_id.orientation
            self.paper_size_format = self.template_id.paper_size_format
            self._onchange_orientation()
            self.update_sequence_purchase_order_header_ids(self.template_id)
            self.update_sequence_purchase_order_table_ids(self.template_id)
            self.update_sequence_purchase_order_footer_ids(self.template_id)

    @api.depends(
        'po_header_filter_ids',
        'po_header_filter_ids.sequence',
        'purchase_order_table_filter_ids',
        'purchase_order_table_filter_ids.sequence',
        'purchase_order_footer_filter_ids',
        'purchase_order_footer_filter_ids.sequence',
        'template_id')
    def _compute_preview(self):
        for record in self:
            purchase_order_id = record.purchase_order_ids and record.purchase_order_ids[0] or False
            print (">purchase_order_id", purchase_order_id, record, record.po_header_filter_ids.mapped('field_id'))
            ir_ui_view = record.env['ir.ui.view']
            record.preview = ir_ui_view._render_template('equip3_general_printout.exclusive_report_printout_editor', {
                'docs': record,
            })

    def action_print(self):
        return self.env.ref('equip3_general_printout.report_printout_editor').report_action(self)

    def action_print_save(self):
        if self.template_id:
            self.template_id.write({
                'purchase_order_header_ids': [(6, 0, self.po_header_filter_ids.mapped('field_id').ids)],
                'purchase_order_table_ids': [(6, 0, self.purchase_order_table_filter_ids.mapped('field_id').ids)],
                'purchase_order_footer_ids': [(6, 0, self.purchase_order_footer_filter_ids.mapped('field_id').ids)],
                'orientation': self.orientation,
                'paper_size_format': self.paper_size_format,
            })
            purchase_order_header_sequence_ids = [(5,0,0)]
            purchase_order_table_sequence_ids = [(5,0,0)]
            purchase_order_footer_sequence_ids = [(5,0,0)]
            for po_header in self.po_header_filter_ids:
                vals = {
                    'field_id':po_header.field_id.id,
                    'sequence':po_header.sequence,
                }
                purchase_order_header_sequence_ids.append((0,0,vals))
            for po_table in self.purchase_order_table_filter_ids:
                vals = {
                    'field_id':po_table.field_id.id,
                    'sequence':po_table.sequence,
                }
                purchase_order_table_sequence_ids.append((0,0,vals))
            for po_footer in self.purchase_order_footer_filter_ids:
                vals = {
                    'field_id':po_footer.field_id.id,
                    'sequence':po_footer.sequence,
                }
                purchase_order_footer_sequence_ids.append((0,0,vals))
            self.template_id.write({
                'purchase_order_header_sequence_ids':purchase_order_header_sequence_ids,
                'purchase_order_table_sequence_ids':purchase_order_table_sequence_ids,
                'purchase_order_footer_sequence_ids':purchase_order_footer_sequence_ids,
            })
            return self.action_print()

class PrintoutEditorLines(models.TransientModel):
    _name = 'printout.editor.lines'
    _rec_name = "field_description"

    sequence = fields.Integer(string='Sequence', default=10)
    is_field_selected = fields.Boolean(string='Is Field Selected', default=False)
    field_id = fields.Many2one('ir.model.fields', string='Fields')
    field_description = fields.Char(related='field_id.field_description', store=True)
    name = fields.Char(related='field_id.name', store=True)
    ttype = fields.Selection(related='field_id.ttype', store=True)
    header_printout_id = fields.Many2one('printout.editor', string='Printout Editor')
    header_filter_printout_id = fields.Many2one('printout.editor', string='Printout Editor')
    table_printout_id = fields.Many2one('printout.editor', string='Printout Editor')
    table_filter_printout_id = fields.Many2one('printout.editor', string='Printout Editor')
    footer_printout_id = fields.Many2one('printout.editor', string='Printout Editor')
    footer_filter_printout_id = fields.Many2one('printout.editor', string='Printout Editor')
    model = fields.Char(related='field_id.model_id.model', string='Model', store=True)
