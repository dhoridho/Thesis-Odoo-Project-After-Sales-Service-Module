
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _


class SalePrintoutEditor(models.TransientModel):
    _name = 'sale.printout.editor'
    _description = "Sale Printout Editor"
    
    name = fields.Char(compute='_compute_sale_order_name', store=True)
    sale_order_ids = fields.Many2many('sale.order', string='Sale Order')
    sale_order_header_ids = fields.Many2many('ir.model.fields', 'ir_model_fields_header_so_rel', 'so_editor_id', 'so_field_id', string="Selected Fields",
                                            domain = [('model', '=', 'sale.order'),
                                                    ('name', 'in', (
                                                        "name",
                                                        "state",
                                                        'partner_id',
                                                        'partner_invoice_id',
                                                        'partner_shipping_id',
                                                        'account_tag_ids',
                                                        'company_id',
                                                        'branch_id',
                                                        'discount_type',
                                                        'sale_order_template_id',
                                                        'date_order',
                                                        'validity_date',
                                                        'create_uid',
                                                        'create_date',
                                                        'pricelist_id',
                                                        'currency_id',
                                                        'payment_term_id',
                                                        'commitment_date',
                                                        'warehouse_id'
                                                    ))
                                                ])
    so_header_filter_ids = fields.One2many('sale.printout.editor.lines', 'so_header_print_out_id', string='Field Filter')
    
    sale_order_table_ids = fields.Many2many('ir.model.fields', 'ir_model_fields_table_so_rel', 'so_editor_id', 'so_field_id', string="Selected Fields",
                                            domain = [
                                                ('model', '=', 'sale.order.line'),
                                                ('name', 'in', (
                                                    'sale_line_sequence',
                                                    'product_template_id',
                                                    'name',
                                                    'discount_method',
                                                    'discount_amount',
                                                    'product_uom_qty',
                                                    'product_uom',
                                                    'product_packaging',
                                                    'price_unit',
                                                    'tax_id',
                                                    'account_tag_ids',
                                                    'last_sale_price',
                                                    'last_customer_sale_price',
                                                    'price_subtotal',
                                                    'product_id',
                                                    'analytic_tag_ids',
                                                    'route_id',
                                                    'customer_lead',
                                                    'purchase_price',
                                                    'margin',
                                                    'margin_percent'
                                                ))
                                            ])
    so_table_filter_ids = fields.One2many('sale.printout.editor.lines', 'so_table_print_out_id', string='Field Filter')
    
    sale_order_footer_ids = fields.Many2many('ir.model.fields', 'ir_model_fields_footer_so_rel', 'so_editor_id', 'so_field_id', string="Selected Fields",
                                            domain=[
                                                ('model', '=', 'sale.order'),
                                                ('name', 'in', (
                                                    'discount_method',
                                                    'discount_amount',
                                                    'terms_conditions_id',
                                                    'amount_untaxed',
                                                    'discount_amt',
                                                    'amount_tax',
                                                    'amount_total',
                                                    'margin'
                                                ))
                                            ])
    so_footer_filter_ids = fields.One2many('sale.printout.editor.lines', 'so_footer_print_out_id', string='Field Filter')
    
    template_id = fields.Many2one('sale.order.templates', string="Template")
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
    preview = fields.Html(compute='compute_preview',
                          sanitize=False,
                          sanitize_tags=False,
                          sanitize_attributes=False,
                          sanitize_style=False,
                          sanitize_form=False,
                          strip_style=False,
                          strip_classes=False)
    
    @api.depends('sale_order_ids')
    def _compute_sale_order_name(self):
        for rec in self:
            rec.name = ','.join(rec.sale_order_ids.mapped('name'))
            
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res['sale_order_ids'] = [(6, 0, self._context.get('active_ids'))]
        return res
    
    @api.onchange('sale_order_header_ids')
    def onchange_sale_order_header_ids(self):
        so_header_filter_ids = self.so_header_filter_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.so_header_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.sale_order_header_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.sale_order_header_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.so_header_filter_ids = data
        
    def update_sequence_sale_order_header_ids(self,template):
        data = [(5,0,0)]
        for so_header in template.sale_order_header_sequence_ids:
            vals = {
                'field_id':so_header.field_id.id,
                'sequence':so_header.sequence,
            }
            data.append((0,0,vals))
        self.so_header_filter_ids = data
        
    @api.onchange('sale_order_table_ids')
    def onchange_sale_order_table_ids(self):
        sale_order_table_ids = self.sale_order_table_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.so_table_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.sale_order_table_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.sale_order_table_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.so_table_filter_ids = data
        
    def update_sequence_sale_order_table_ids(self,template):
        data = [(5,0,0)]
        for so_table in template.sale_order_table_sequence_ids:
            vals = {
                'field_id':so_table.field_id.id,
                'sequence':so_table.sequence,
            }
            data.append((0,0,vals))
        self.so_table_filter_ids = data
        
    @api.onchange('sale_order_footer_ids')
    def onchange_purchase_order_footer_ids(self):
        sale_order_footer_ids = self.sale_order_footer_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.so_footer_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.sale_order_footer_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.sale_order_footer_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.so_footer_filter_ids = data
        
    def update_sequence_sale_order_footer_ids(self,template):
        data = [(5,0,0)]
        for so_footer in template.sale_order_footer_sequence_ids:
            vals = {
                'field_id':so_footer.field_id.id,
                'sequence':so_footer.sequence,
            }
            data.append((0,0,vals))
        self.so_footer_filter_ids = data
        
    @api.onchange('orientation', 'paper_size_format')
    def onchange_orientation(self):
        paperformat_id = False
        if self.orientation == "potrait" and self.paper_size_format in ('Tabloid', 'A3'):
            paperformat_id = self.env.ref('equip3_sale_custom_printout.paperformat_so_printout_editor_potrait_tabloid')
        elif self.orientation == 'potrait' and self.paper_size_format == 'B4':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.paperformat_so_printout_editor_potrait_b4')
        elif self.orientation == "potrait" and self.paper_size_format not in ('Tabloid', 'A3', 'B4'):
            paperformat_id = self.env.ref('equip3_sale_custom_printout.paperformat_so_printout_editor_potrait')
        elif self.orientation == 'landscape' and self.paper_size_format not in ('Tabloid', 'Legal', 'Folio', 'A3', 'B4'):
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_so_paperformat_printout_editor')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Tabloid':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_so_paperformat_printout_editor_tabloid')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Legal':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_paperformat_so_printout_editor_legal')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Folio':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_paperformat_so_printout_editor_statement')
        elif self.orientation == 'landscape' and self.paper_size_format == 'A3':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_paperformat_so_printout_editor_a3')
        elif self.orientation == 'landscape' and self.paper_size_format == 'B4':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_paperformat_so_printout_editor_b4')

        if self.paper_size_format and paperformat_id:
            paperformat_id.format = self.paper_size_format
            report_id = self.env.ref('equip3_sale_custom_printout.report_so_printout_editor')
            report_id.paperformat_id = paperformat_id.id
            self.compute_preview()
    
    @api.depends(
        'so_header_filter_ids',
        'so_header_filter_ids.sequence',
        'so_table_filter_ids',
        'so_table_filter_ids.sequence',
        'so_footer_filter_ids',
        'so_footer_filter_ids.sequence',
        'template_id')
    def compute_preview(self):
        for record in self:
            sale_order_id = record.sale_order_ids and record.sale_order_ids[0] or False
            ir_ui_view = record.env['ir.ui.view']
            record.preview = ir_ui_view._render_template('equip3_sale_custom_printout.exclusive_so_report_printout_editor', {
                'docs': record,
            })    
            
    def action_print(self):
        return self.env.ref('equip3_sale_custom_printout.report_so_printout_editor').report_action(self)
            
    def action_print_save(self):
        if self.template_id:
            self.template_id.write({
                'sale_order_header_ids': [(6, 0, self.so_header_filter_ids.mapped('field_id').ids)],
                'sale_order_table_ids': [(6, 0, self.so_table_filter_ids.mapped('field_id').ids)],
                'sale_order_footer_ids': [(6, 0, self.so_footer_filter_ids.mapped('field_id').ids)],
                'orientation': self.orientation,
                'paper_size_format': self.paper_size_format,
            })
            sale_order_header_sequence_ids = [(5,0,0)]
            sale_order_table_sequence_ids = [(5,0,0)]
            sale_order_footer_sequence_ids = [(5,0,0)]
            for so_header in self.so_header_filter_ids:
                vals = {
                    'field_id':so_header.field_id.id,
                    'sequence':so_header.sequence,
                }
                sale_order_header_sequence_ids.append((0,0,vals))
            for so_table in self.so_table_filter_ids:
                vals = {
                    'field_id':so_table.field_id.id,
                    'sequence':so_table.sequence,
                }
                sale_order_table_sequence_ids.append((0,0,vals))
            for so_footer in self.so_footer_filter_ids:
                vals = {
                    'field_id':so_footer.field_id.id,
                    'sequence':so_footer.sequence,
                }
                sale_order_footer_sequence_ids.append((0,0,vals))
            self.template_id.write({
                'sale_order_header_sequence_ids':sale_order_header_sequence_ids,
                'sale_order_table_sequence_ids':sale_order_table_sequence_ids,
                'sale_order_footer_sequence_ids':sale_order_footer_sequence_ids,
            })
        return self.action_print()
            
        
    @api.onchange('template_id')
    def onchange_template(self):
        if self.template_id and \
            (self.template_id.sale_order_header_ids or 
            self.template_id.sale_order_table_ids or 
            self.template_id.sale_order_footer_ids):
            self.sale_order_header_ids = [(6, 0, self.template_id.sale_order_header_ids.ids)]
            self.sale_order_table_ids = [(6, 0, self.template_id.sale_order_table_ids.ids)]
            self.sale_order_footer_ids = [(6, 0, self.template_id.sale_order_footer_ids.ids)]
            self.orientation = self.template_id.orientation
            self.paper_size_format = self.template_id.paper_size_format
            self.onchange_orientation()
            self.update_sequence_sale_order_header_ids(self.template_id)
            self.update_sequence_sale_order_table_ids(self.template_id)
            self.update_sequence_sale_order_footer_ids(self.template_id)
    

class SalePrintoutEditorLines(models.TransientModel):
    _name = 'sale.printout.editor.lines'
    _description = "Sale Printout Editor Line"
    
    sequence = fields.Integer(string='Sequence', default=10)
    field_id = fields.Many2one('ir.model.fields', string='Fields')
    field_description = fields.Char(related='field_id.field_description', store=True)
    name = fields.Char(related='field_id.name', store=True)
    ttype = fields.Selection(related='field_id.ttype', store=True)
    so_header_print_out_id = fields.Many2one('sale.printout.editor', string="Printout Editor")
    so_table_print_out_id = fields.Many2one('sale.printout.editor', string="Printout Editor")
    so_footer_print_out_id = fields.Many2one('sale.printout.editor', string="Printout Editor")
    header_printout_id = fields.Many2one('sale.printout.editor', string='Printout Editor')
    table_printout_id = fields.Many2one('sale.printout.editor', string='Printout Editor')
    footer_printout_id = fields.Many2one('sale.printout.editor', string='Printout Editor')
    model = fields.Char(related='field_id.model_id.model', string='Model', store=True)
    
    