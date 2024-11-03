
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _


class InvoicePrintoutEditor(models.TransientModel):
    _name = 'invoice.printout.editor'

    name = fields.Char(compute='_compute_invoice_name', store=True)
    invoice_ids = fields.Many2many('account.move', string='Invoice')
    invoice_header_ids = fields.Many2many('ir.model.fields', 'invoice_printout_editor_header_rel', string="Selected Fields",
                                            domain = [('model', '=', 'account.move'),
                                                    ('name', 'in', (
                                                        "name",
                                                        "invoice_date",
                                                        "invoice_origin",
                                                        "invoice_date_due",
                                                    ))
                                                ])
    invoice_header_filter_ids = fields.One2many('invoice.printout.editor.lines', 'invoice_header_print_out_id', string='Field Filter')

    invoice_table_ids = fields.Many2many('ir.model.fields', 'invoice_printout_editor_table_rel', string="Selected Fields",
                                            domain = [
                                                ('model', '=', 'account.move.line'),
                                                ('name', 'in', (
                                                    'name',
                                                    'quantity',
                                                    'price_unit',
                                                    'discount',
                                                    'tax_ids',
                                                    'price_subtotal',
                                                    # 'product_id',
                                                ))
                                            ])
    invoice_table_filter_ids = fields.One2many('invoice.printout.editor.lines', 'invoice_table_print_out_id', string='Field Filter')

    invoice_footer_ids = fields.Many2many('ir.model.fields', 'invoice_printout_editor_footer_rel', string="Selected Fields",
                                            domain=[
                                                ('model', '=', 'account.move'),
                                                ('name', 'in', (
                                                    'amount_untaxed',
                                                    'amount_tax',
                                                    'amount_total',
                                                    # 'amount_residual',
                                                ))
                                            ])
    invoice_footer_filter_ids = fields.One2many('invoice.printout.editor.lines', 'invoice_footer_print_out_id', string='Field Filter')

    template_id = fields.Many2one('invoice.templates', string="Template")
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
        ], string="Size", default='Letter')
    preview = fields.Html(compute='compute_preview',
                          sanitize=False,
                          sanitize_tags=False,
                          sanitize_attributes=False,
                          sanitize_style=False,
                          sanitize_form=False,
                          strip_style=False,
                          strip_classes=False)


    @api.depends('invoice_ids')
    def _compute_invoice_name(self):
        for rec in self:
            rec.name = ','.join(rec.invoice_ids.mapped('name'))

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res['invoice_ids'] = [(6, 0, self._context.get('active_ids'))]

        invoice_temp_obj = self.env['invoice.templates'].search([('name','=','New Template')], limit=1)
        res['template_id'] = invoice_temp_obj.id

        return res

    @api.onchange('invoice_header_ids')
    def onchange_invoice_header_ids(self):
        invoice_header_filter_ids = self.invoice_header_filter_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.invoice_header_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.invoice_header_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.invoice_header_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.invoice_header_filter_ids = data

    def update_sequence_invoice_header_ids(self,template):
        data = [(5,0,0)]
        for invoice_header in template.invoice_header_sequence_ids:
            vals = {
                'field_id': invoice_header.field_id.id,
                'sequence': invoice_header.sequence,
            }
            data.append((0, 0, vals))
        self.invoice_header_filter_ids = data

    @api.onchange('invoice_table_ids')
    def onchange_invoice_table_ids(self):
        invoice_table_ids = self.invoice_table_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.invoice_table_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.invoice_table_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.invoice_table_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.invoice_table_filter_ids = data

    def update_sequence_invoice_table_ids(self, template):
        data = [(5, 0, 0)]
        for invoice_table in template.invoice_table_sequence_ids:
            vals = {
                'field_id': invoice_table.field_id.id,
                'sequence': invoice_table.sequence,
            }
            data.append((0, 0, vals))
        self.invoice_table_filter_ids = data

    @api.onchange('invoice_footer_ids')
    def onchange_invoice_footer_ids(self):
        invoice_footer_ids = self.invoice_footer_ids
        data = [(5, 0, 0)]
        fields_data = []
        sequence = 1
        for filter_line in sorted(self.invoice_footer_filter_ids, key=lambda r: r.sequence):
            if filter_line.field_id._origin.id in self.invoice_footer_ids.ids:
                data.append((0, 0, {'field_id': filter_line.field_id._origin.id, 'sequence': filter_line.sequence}))
                fields_data.append(filter_line.field_id._origin.id)
                sequence = filter_line.sequence
        for line in self.invoice_footer_ids.filtered(lambda r: r._origin.id not in fields_data):
            data.append((0, 0, {'field_id': line._origin.id, 'sequence': sequence}))
            sequence += 1
        self.invoice_footer_filter_ids = data

    def update_sequence_invoice_footer_ids(self,template):
        data = [(5, 0, 0)]
        for invoice_footer in template.invoice_footer_sequence_ids:
            vals = {
                'field_id': invoice_footer.field_id.id,
                'sequence': invoice_footer.sequence,
            }
            data.append((0, 0, vals))
        self.invoice_footer_filter_ids = data

    @api.onchange('orientation', 'paper_size_format')
    def onchange_orientation(self):
        paperformat_id = False
        if self.orientation == "potrait" and self.paper_size_format in ('Tabloid', 'A3'):
            paperformat_id = self.env.ref('equip3_accounting_operation.paperformat_invoice_printout_editor_potrait_tabloid')
        elif self.orientation == 'potrait' and self.paper_size_format == 'B4':
            paperformat_id = self.env.ref('equip3_accounting_operation.paperformat_invoice_printout_editor_potrait_b4')
        elif self.orientation == "potrait" and self.paper_size_format not in ('Tabloid', 'A3', 'B4'):
            paperformat_id = self.env.ref('equip3_accounting_operation.paperformat_invoice_printout_editor_potrait')
        elif self.orientation == 'landscape' and self.paper_size_format not in ('Tabloid', 'Legal', 'Folio', 'A3', 'B4'):
            paperformat_id = self.env.ref('equip3_accounting_operation.landscape_invoice_paperformat_printout_editor')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Tabloid':
            paperformat_id = self.env.ref('equip3_accounting_operation.landscape_invoice_paperformat_printout_editor_tabloid')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Legal':
            paperformat_id = self.env.ref('equip3_accounting_operation.landscape_paperformat_invoice_printout_editor_legal')
        elif self.orientation == 'landscape' and self.paper_size_format == 'Folio':
            paperformat_id = self.env.ref('equip3_accounting_operation.landscape_paperformat_invoice_printout_editor_statement')
        elif self.orientation == 'landscape' and self.paper_size_format == 'A3':
            paperformat_id = self.env.ref('equip3_accounting_operation.landscape_paperformat_invoice_printout_editor_a3')
        elif self.orientation == 'landscape' and self.paper_size_format == 'B4':
            paperformat_id = self.env.ref('equip3_accounting_operation.landscape_paperformat_invoice_printout_editor_b4')

        if self.paper_size_format and paperformat_id:
            paperformat_id.format = self.paper_size_format
            report_id = self.env.ref('equip3_accounting_operation.report_invoice_printout_editor')
            report_id.paperformat_id = paperformat_id.id
            self.compute_preview()

    @api.depends(
        'invoice_header_filter_ids',
        'invoice_header_filter_ids.sequence',
        'invoice_table_filter_ids',
        'invoice_table_filter_ids.sequence',
        'invoice_footer_filter_ids',
        'invoice_footer_filter_ids.sequence',
        'template_id'
        )
    def compute_preview(self):
        for record in self:
            invoice_id = record.invoice_ids and record.invoice_ids[0] or False
            ir_ui_view = record.env['ir.ui.view']
            record.preview = ir_ui_view._render_template('equip3_accounting_operation.exclusive_invoice_report_printout_editor', {
                'docs': record,
            })

    def action_print(self):
        return self.env.ref('equip3_accounting_operation.report_invoice_printout_editor').report_action(self)

    def action_print_save(self):
        # if self.template_id:
        #     self.template_id.write({
        #         'invoice_header_ids': [(6, 0, self.invoice_header_filter_ids.mapped('field_id').ids)],
        #         'invoice_table_ids': [(6, 0, self.invoice_table_filter_ids.mapped('field_id').ids)],
        #         'invoice_footer_ids': [(6, 0, self.invoice_footer_filter_ids.mapped('field_id').ids)],
        #         'orientation': self.orientation,
        #         'paper_size_format': self.paper_size_format,
        #     })
        #     invoice_header_sequence_ids = [(5, 0, 0)]
        #     invoice_table_sequence_ids = [(5, 0, 0)]
        #     invoice_footer_sequence_ids = [(5, 0, 0)]
        #     for invoice_header in self.invoice_header_filter_ids:
        #         vals = {
        #             'field_id': invoice_header.field_id.id,
        #             'sequence': invoice_header.sequence,
        #         }
        #         invoice_header_sequence_ids.append((0, 0, vals))
        #     for invoice_table in self.invoice_table_filter_ids:
        #         vals = {
        #             'field_id': invoice_table.field_id.id,
        #             'sequence': invoice_table.sequence,
        #         }
        #         invoice_table_sequence_ids.append((0, 0, vals))
        #     for invoice_footer in self.invoice_footer_filter_ids:
        #         vals = {
        #             'field_id': invoice_footer.field_id.id,
        #             'sequence': invoice_footer.sequence,
        #         }
        #         invoice_footer_sequence_ids.append((0, 0, vals))
        #     self.template_id.write({
        #         'invoice_header_sequence_ids': invoice_header_sequence_ids,
        #         'invoice_table_sequence_ids': invoice_table_sequence_ids,
        #         'invoice_footer_sequence_ids': invoice_footer_sequence_ids,
        #     })
        invoice_header_sequence_ids = [(5, 0, 0)]
        invoice_table_sequence_ids = [(5, 0, 0)]
        invoice_footer_sequence_ids = [(5, 0, 0)]
        for invoice_header in self.invoice_header_filter_ids:
            vals = {
                'field_id': invoice_header.field_id.id,
                'sequence': invoice_header.sequence,
            }
            invoice_header_sequence_ids.append((0, 0, vals))
        for invoice_table in self.invoice_table_filter_ids:
            vals = {
                'field_id': invoice_table.field_id.id,
                'sequence': invoice_table.sequence,
            }
            invoice_table_sequence_ids.append((0, 0, vals))
        for invoice_footer in self.invoice_footer_filter_ids:
            vals = {
                'field_id': invoice_footer.field_id.id,
                'sequence': invoice_footer.sequence,
            }
            invoice_footer_sequence_ids.append((0, 0, vals))

        res_vals = {
            'invoice_header_ids': [(6, 0, self.invoice_header_filter_ids.mapped('field_id').ids)],
            'invoice_table_ids': [(6, 0, self.invoice_table_filter_ids.mapped('field_id').ids)],
            'invoice_footer_ids': [(6, 0, self.invoice_footer_filter_ids.mapped('field_id').ids)],
            'orientation': self.orientation,
            'paper_size_format': self.paper_size_format,
            'invoice_header_sequence_ids': invoice_header_sequence_ids,
            'invoice_table_sequence_ids': invoice_table_sequence_ids,
            'invoice_footer_sequence_ids': invoice_footer_sequence_ids,
        }

        if self.template_id:
            self.template_id.write(res_vals)
        else:
            res_vals['name'] = 'New Template'
            rec = self.template_id.create(res_vals)
            self.template_id = rec.id

        return self.action_print()

    @api.onchange('template_id')
    def onchange_template(self):
        if self.template_id and \
            (self.template_id.invoice_header_ids or
            self.template_id.invoice_table_ids or
            self.template_id.invoice_footer_ids):
            self.invoice_header_ids = [(6, 0, self.template_id.invoice_header_ids.ids)]
            self.invoice_table_ids = [(6, 0, self.template_id.invoice_table_ids.ids)]
            self.invoice_footer_ids = [(6, 0, self.template_id.invoice_footer_ids.ids)]
            self.orientation = self.template_id.orientation
            self.paper_size_format = self.template_id.paper_size_format
            self.onchange_orientation()
            self.update_sequence_invoice_header_ids(self.template_id)
            self.update_sequence_invoice_table_ids(self.template_id)
            self.update_sequence_invoice_footer_ids(self.template_id)
            

class InvoicePrintoutEditorLines(models.TransientModel):
    _name = 'invoice.printout.editor.lines'
    
    sequence = fields.Integer(string='Sequence', default=10)
    field_id = fields.Many2one('ir.model.fields', string='Fields')
    field_description = fields.Char(related='field_id.field_description', store=True)
    name = fields.Char(related='field_id.name', store=True)
    ttype = fields.Selection(related='field_id.ttype', store=True)
    invoice_header_print_out_id = fields.Many2one('invoice.printout.editor', string="Printout Editor")
    invoice_table_print_out_id = fields.Many2one('invoice.printout.editor', string="Printout Editor")
    invoice_footer_print_out_id = fields.Many2one('invoice.printout.editor', string="Printout Editor")
    # header_printout_id = fields.Many2one('invoice.printout.editor', string='Printout Editor')
    # table_printout_id = fields.Many2one('invoice.printout.editor', string='Printout Editor')
    # footer_printout_id = fields.Many2one('invoice.printout.editor', string='Printout Editor')
    model = fields.Char(related='field_id.model_id.model', string='Model', store=True)