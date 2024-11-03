
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _


class BlanketPrintoutEditor(models.TransientModel):
    _name = 'blanket.printout.editor'
    _description = "Blanket Printout Editor"

    name = fields.Char(compute='_compute_blanket_order_name', store=True)
    blanket_order_ids = fields.Many2many('saleblanket.saleblanket', string='Blanket Order')
    blanket_order_header_ids = fields.Many2many('ir.model.fields', 'ir_model_fields_header_bo_rel', 'bo_editor_id', 'bo_field_id', string="Selected Fields",
                                            domain = [('model', '=', 'saleblanket.saleblanket'),
                                                    ('name', 'in', (
                                                        "name",
                                                        "state",
                                                        'partner_id',
                                                        'invoice_address',
                                                        'delivery_address',
                                                        'analytic_tag_ids',
                                                        'company_id',
                                                        'branch_id',
                                                        'creation_date',
                                                        'expiry_date',
                                                        'create_uid',
                                                        'create_date',
                                                        'pricelist_id',
                                                        'currency_id',
                                                        'payment_term_id'
                                                    ))
                                                ])
    bo_header_filter_ids = fields.One2many('blanket.printout.editor.lines', 'bo_header_print_out_id', string='Field Filter')
    
    blanket_order_table_ids = fields.Many2many('ir.model.fields', 'ir_model_fields_table_bo_rel', 'bo_editor_id', 'bo_field_id', string="Selected Fields",
                                            domain = [
                                                ('model', '=', 'orderline.orderline'),
                                                ('name', 'in', (
                                                    'name',
                                                    'quantity',
                                                    'ordered_qty',
                                                    'delivered_qty',
                                                    'undelivered_qty',
                                                    'qty_invoiced',
                                                    'remaining_qty',
                                                    'product_uom',
                                                    'price_unit',
                                                    'tax_id',
                                                    'price_subtotal',
                                                    'product_id',
                                                    'analytic_tag_ids'
                                                ))
                                            ])
    bo_table_filter_ids = fields.One2many('blanket.printout.editor.lines', 'bo_table_print_out_id', string='Field Filter')
    
    blanket_order_footer_ids = fields.Many2many('ir.model.fields', 'ir_model_fields_footer_bo_rel', 'bo_editor_id', 'bo_field_id', string="Selected Fields",
                                            domain=[
                                                ('model', '=', 'saleblanket.saleblanket'),
                                                ('name', 'in', (
                                                    'amount_untaxed',
                                                    'amount_tax',
                                                    'amount_total',
                                                ))
                                            ])
    bo_footer_filter_ids = fields.One2many('blanket.printout.editor.lines', 'bo_footer_print_out_id', string='Field Filter')
    
    template_id = fields.Many2one('blanket.order.templates', string="Template")
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
    
    @api.depends('blanket_order_ids')
    def _compute_blanket_order_name(self):
        for rec in self:
            rec.name = ','.join(rec.blanket_order_ids.mapped('name'))
            
    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res['blanket_order_ids'] = [(6, 0, self._context.get('active_ids'))]
        return res
    
    @api.onchange('blanket_order_header_ids')
    def onchange_blanket_order_header_ids(self):
        bo_header_filter_ids = self.bo_header_filter_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.bo_header_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.blanket_order_header_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.blanket_order_header_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.bo_header_filter_ids = data
        
    def update_sequence_blanket_order_header_ids(self,template):
        data = [(5,0,0)]
        for bo_header in template.blanket_order_header_sequence_ids:
            vals = {
                'field_id': bo_header.field_id.id,
                'sequence': bo_header.sequence,
            }
            data.append((0, 0, vals))
        self.bo_header_filter_ids = data
        
    @api.onchange('blanket_order_table_ids')
    def onchange_blanket_order_table_ids(self):
        blanket_order_table_ids = self.blanket_order_table_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.bo_table_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.blanket_order_table_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.blanket_order_table_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.bo_table_filter_ids = data
        
    def update_sequence_blanket_order_table_ids(self, template):
        data = [(5, 0, 0)]
        for bo_table in template.blanket_order_table_sequence_ids:
            vals = {
                'field_id': bo_table.field_id.id,
                'sequence': bo_table.sequence,
            }
            data.append((0, 0, vals))
        self.bo_table_filter_ids = data
        
    @api.onchange('blanket_order_footer_ids')
    def onchange_blanket_order_footer_ids(self):
        blanket_order_footer_ids = self.blanket_order_footer_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.bo_footer_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.blanket_order_footer_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.blanket_order_footer_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.bo_footer_filter_ids = data
        
    def update_sequence_blanket_order_footer_ids(self,template):
        data = [(5, 0, 0)]
        for bo_footer in template.blanket_order_footer_sequence_ids:
            vals = {
                'field_id': bo_footer.field_id.id,
                'sequence': bo_footer.sequence,
            }
            data.append((0, 0, vals))
        self.bo_footer_filter_ids = data
        
    @api.onchange('orientation', 'paper_size_format')
    def onchange_orientation(self):
        paperformat_id = False
        if self.orientation == "potrait" and self.paper_size_format in ('Tabloid', 'A3'):
            paperformat_id = self.env.ref('equip3_sale_custom_printout.paperformat_bo_printout_editor_potrait_tabloid')
        elif self.orientation == 'potrait' and self.paper_size_format == 'B4':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.paperformat_bo_printout_editor_potrait_b4')
        elif self.orientation == "potrait" and self.paper_size_format not in ('Tabloid', 'A3', 'B4'):
            paperformat_id = self.env.ref('equip3_sale_custom_printout.paperformat_bo_printout_editor_potrait')
        elif self.orientation == 'landscape' and self.paper_size_format not in ('Tabloid', 'Legal', 'Folio', 'A3', 'B4'):
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_bo_paperformat_printout_editor')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Tabloid':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_bo_paperformat_printout_editor_tabloid')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Legal':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_paperformat_bo_printout_editor_legal')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Folio':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_paperformat_bo_printout_editor_statement')
        elif self.orientation == 'landscape' and self.paper_size_format == 'A3':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_paperformat_bo_printout_editor_a3')
        elif self.orientation == 'landscape' and self.paper_size_format == 'B4':
            paperformat_id = self.env.ref('equip3_sale_custom_printout.landscape_paperformat_bo_printout_editor_b4')

        if self.paper_size_format and paperformat_id:
            paperformat_id.format = self.paper_size_format
            report_id = self.env.ref('equip3_sale_custom_printout.report_bo_printout_editor')
            report_id.paperformat_id = paperformat_id.id
            self.compute_preview()
    
    @api.depends(
        'bo_header_filter_ids',
        'bo_header_filter_ids.sequence',
        'bo_table_filter_ids',
        'bo_table_filter_ids.sequence',
        'bo_footer_filter_ids',
        'bo_footer_filter_ids.sequence',
        'template_id')
    def compute_preview(self):
        for record in self:
            blanket_order_id = record.blanket_order_ids and record.blanket_order_ids[0] or False
            ir_ui_view = record.env['ir.ui.view']
            record.preview = ir_ui_view._render_template('equip3_sale_custom_printout.exclusive_bo_report_printout_editor', {
                'docs': record,
            })
            
    def action_print(self):
        return self.env.ref('equip3_sale_custom_printout.report_bo_printout_editor').report_action(self)
            
    def action_print_save(self):
        if self.template_id:
            self.template_id.write({
                'blanket_order_header_ids': [(6, 0, self.bo_header_filter_ids.mapped('field_id').ids)],
                'blanket_order_table_ids': [(6, 0, self.bo_table_filter_ids.mapped('field_id').ids)],
                'blanket_order_footer_ids': [(6, 0, self.bo_footer_filter_ids.mapped('field_id').ids)],
                'orientation': self.orientation,
                'paper_size_format': self.paper_size_format,
            })
            blanket_order_header_sequence_ids = [(5, 0, 0)]
            blanket_order_table_sequence_ids = [(5, 0, 0)]
            blanket_order_footer_sequence_ids = [(5, 0, 0)]
            for bo_header in self.bo_header_filter_ids:
                vals = {
                    'field_id': bo_header.field_id.id,
                    'sequence': bo_header.sequence,
                }
                blanket_order_header_sequence_ids.append((0, 0, vals))
            for bo_table in self.bo_table_filter_ids:
                vals = {
                    'field_id': bo_table.field_id.id,
                    'sequence': bo_table.sequence,
                }
                blanket_order_table_sequence_ids.append((0, 0, vals))
            for bo_footer in self.bo_footer_filter_ids:
                vals = {
                    'field_id': bo_footer.field_id.id,
                    'sequence': bo_footer.sequence,
                }
                blanket_order_footer_sequence_ids.append((0, 0, vals))
            self.template_id.write({
                'blanket_order_header_sequence_ids': blanket_order_header_sequence_ids,
                'blanket_order_table_sequence_ids': blanket_order_table_sequence_ids,
                'blanket_order_footer_sequence_ids': blanket_order_footer_sequence_ids,
            })
        return self.action_print()
            
        
    @api.onchange('template_id')
    def onchange_template(self):
        if self.template_id and \
            (self.template_id.blanket_order_header_ids or
            self.template_id.blanket_order_table_ids or
            self.template_id.blanket_order_footer_ids):
            self.blanket_order_header_ids = [(6, 0, self.template_id.blanket_order_header_ids.ids)]
            self.blanket_order_table_ids = [(6, 0, self.template_id.blanket_order_table_ids.ids)]
            self.blanket_order_footer_ids = [(6, 0, self.template_id.blanket_order_footer_ids.ids)]
            self.orientation = self.template_id.orientation
            self.paper_size_format = self.template_id.paper_size_format
            self.onchange_orientation()
            self.update_sequence_blanket_order_header_ids(self.template_id)
            self.update_sequence_blanket_order_table_ids(self.template_id)
            self.update_sequence_blanket_order_footer_ids(self.template_id)
    

class BlanketPrintoutEditorLines(models.TransientModel):
    _name = 'blanket.printout.editor.lines'
    _description = "Blanket Printout Editor Line"
    
    sequence = fields.Integer(string='Sequence', default=10)
    field_id = fields.Many2one('ir.model.fields', string='Fields')
    field_description = fields.Char(related='field_id.field_description', store=True)
    name = fields.Char(related='field_id.name', store=True)
    ttype = fields.Selection(related='field_id.ttype', store=True)
    bo_header_print_out_id = fields.Many2one('blanket.printout.editor', string="Printout Editor")
    bo_table_print_out_id = fields.Many2one('blanket.printout.editor', string="Printout Editor")
    bo_footer_print_out_id = fields.Many2one('blanket.printout.editor', string="Printout Editor")
    header_printout_id = fields.Many2one('blanket.printout.editor', string='Printout Editor')
    table_printout_id = fields.Many2one('blanket.printout.editor', string='Printout Editor')
    footer_printout_id = fields.Many2one('blanket.printout.editor', string='Printout Editor')
    model = fields.Char(related='field_id.model_id.model', string='Model', store=True)
    
    