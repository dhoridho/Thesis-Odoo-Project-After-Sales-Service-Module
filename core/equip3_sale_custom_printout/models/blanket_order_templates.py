
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _

class saleBlanket(models.Model):

    _inherit = 'saleblanket.saleblanket'

    name = fields.Char(string='Blanket Order Number', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))

    def action_print(self):
        return {
            'name': "Print Report",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'saleblanket.order.report.wizard',
            'target': 'new',
        }


class BlanketOrderTemplates(models.Model):
    _name = "blanket.order.templates"
    _description = "Blanket Order Templates"

    name = fields.Char(string='Name', required=True)
    blanket_order_header_ids = fields.Many2many(
            'ir.model.fields',
            'blanket_order_template_header_model_fields_rel',
            'model_id', 'order_id')
    blanket_order_table_ids = fields.Many2many(
        'ir.model.fields',
        'blanket_order_template_table_model_fields_rel',
        'model_id', 'order_line_id')
    blanket_order_footer_ids = fields.Many2many(
        'ir.model.fields',
        'blanket_order_template_footer_model_fields_rel',
        'model_id', 'order_id')
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

    blanket_order_header_sequence_ids = fields.One2many(comodel_name='blanket.order.template.header', inverse_name='template_id', string='Header')
    blanket_order_table_sequence_ids = fields.One2many(comodel_name='blanket.order.template.table', inverse_name='template_id', string='Table')
    blanket_order_footer_sequence_ids = fields.One2many(comodel_name='blanket.order.template.footer', inverse_name='template_id', string='Footer')

    @api.model
    def _create_default_template_rfq_and_bo(self):
        default_report_blanket = self.env.ref('equip3_sale_custom_printout.default_rerport_custom_print_blanket')
        if not default_report_blanket:
            default_report_blanket = self.sudo().search([('name', '=', 'Default Tempalte Blanket')], limit=1)
            if not default_report_blanket:
                default_report_blanket = self.sudo().create({
                    'name': 'Default Tempalte Blanket',
                    'orientation': 'potrait',
                    'size': 'A4',
                    })
        field_headers = [
                'name',
                'creation_date',
                'create_date',
            ]
        blanket_header_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'saleblanket.saleblanket'),
            ('name', 'in', field_headers)
        ])
        blanket_order_header_sequence_ids = [(5, 0, 0)]
        sequence = 1
        for field in field_headers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'saleblanket.saleblanket'),
                ('name', '=', field)
            ], limit=1)
            if field_id:
                blanket_order_header_sequence_ids.append((0, 0, {'field_id': field_id.id, 'sequence': sequence}))
                sequence += 1
        default_report_blanket.blanket_order_header_sequence_ids = blanket_order_header_sequence_ids
        default_report_blanket.blanket_order_header_ids = [(6, 0, blanket_header_ids.ids)]

        field_tables = [
                'sequence2',
                'image_256',
                'product_id',
                'name',
                'date_planned',
                'destination_warehouse_id',
                'product_qty',
            ]
        blanket_table_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'orderline.orderline'),
            ('name', 'in', field_tables)
        ])
        blanket_order_table_sequence_ids = [(5, 0, 0)]
        sequence = 1
        for field in field_tables:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'orderline.orderline'),
                ('name', '=', field)
            ], limit=1)
            if field_id:
                blanket_order_table_sequence_ids.append((0, 0, {'field_id': field_id.id, 'sequence': sequence}))
                sequence += 1
        default_report_blanket.blanket_order_table_sequence_ids = blanket_order_table_sequence_ids
        default_report_blanket.blanket_order_table_ids = [(6, 0, blanket_table_ids.ids)]
        field_footers = [
                'sign_on',
                'digital_sign',
                'sign_by',
                'designation',
            ]
        blanket_footer_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'saleblanket.saleblanket'),
            ('name', 'in', field_footers)
        ])
        blanket_order_footer_sequence_ids = [(5, 0, 0)]
        sequence = 1
        for field in field_footers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'saleblanket.saleblanket'),
                ('name', '=', field)
            ], limit=1)
            if field_id:
                blanket_order_footer_sequence_ids.append((0, 0, {'field_id': field_id.id, 'sequence': sequence}))
                sequence += 1
        default_report_blanket.blanket_order_footer_sequence_ids = blanket_order_footer_sequence_ids
        default_report_blanket.blanket_order_footer_ids = [(6, 0, blanket_footer_ids.ids)]

        default_report_bo = self.env.ref('equip3_sale_custom_printout.default_rerport_custom_print_bo')
        if not default_report_bo:
            default_report_bo = self.sudo().search([('name', '=', 'Default Template SO')], limit=1)
            if not default_report_bo:
                default_report_bo = self.sudo().create({
                    'name': 'Default Template SO',
                    'orientation': 'potrait',
                    'size': 'A4',
                    })

        field_headers = [
                'name',
                'date_approve',
            ]
        bo_quotation_header_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'saleblanket.saleblanket'),
            ('name', 'in', field_headers)
        ])
        blanket_order_header_sequence_ids = [(5, 0, 0)]
        sequence = 1
        for field in field_headers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'saleblanket.saleblanket'),
                ('name', '=', field)
            ],limit=1)
            if field_id:
                blanket_order_header_sequence_ids.append((0, 0, {'field_id': field_id.id, 'sequence': sequence}))
                sequence += 1
        default_report_bo.blanket_order_header_sequence_ids = blanket_order_header_sequence_ids
        default_report_bo.blanket_order_header_ids = [(6, 0, bo_quotation_header_ids.ids)]

        field_tables = [
                'sequence2',
                # 'image_256',
                'product_id',
                'name',
                # 'date_planned',
                # 'destination_warehouse_id',
                # 'product_qty',
                'price_unit',
                # 'discount_method',
                # 'discount_amount',
                'taxes_id',
                'price_subtotal',
            ]
        quotation_table_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'orderline.orderline'),
            ('name', 'in', field_tables)
        ])
        blanket_order_table_sequence_ids = [(5, 0, 0)]
        sequence = 1
        for field in field_tables:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'orderline.orderline'),
                ('name', '=', field)
            ], limit=1)
            if field_id:
                blanket_order_table_sequence_ids.append((0, 0, {'field_id': field_id.id, 'sequence': sequence}))
                sequence += 1
        default_report_bo.blanket_order_table_sequence_ids = blanket_order_table_sequence_ids
        default_report_bo.blanket_order_table_ids = [(6, 0, quotation_table_ids.ids)]

        field_footers = [
                'amount_untaxed',
                'amount_tax',
                'amount_total',
                'sign_on',
                'digital_sign',
                'sign_by',
                'designation',
            ]
        blanket_footer_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'saleblanket.saleblanket'),
            ('name', 'in', field_footers)
        ])
        blanket_order_footer_sequence_ids = [(5, 0, 0)]
        sequence = 1
        for field in field_footers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'saleblanket.saleblanket'),
                ('name', '=', field)
            ], limit=1)
            if field_id:
                blanket_order_footer_sequence_ids.append((0, 0, {'field_id': field_id.id, 'sequence': sequence}))
                sequence += 1
        default_report_bo.blanket_order_footer_sequence_ids = blanket_order_footer_sequence_ids
        default_report_bo.blanket_order_footer_ids = [(6, 0, blanket_footer_ids.ids)]


class BlanketOrderTemplateHeader(models.Model):
    _name = "blanket.order.template.header"
    _description = "Blanket Order Template Header"

    template_id = fields.Many2one(comodel_name='blanket.order.templates', string='Template', required=True, ondelete="cascade")
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='Field')
    sequence = fields.Integer(string='Sequence')

class BlanketOrderTemplateTable(models.Model):
    _name = "blanket.order.template.table"
    _description = "Blanket Order Template Table"

    template_id = fields.Many2one(comodel_name='blanket.order.templates', string='Template', required=True, ondelete="cascade")
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='Field')
    sequence = fields.Integer(string='Sequence')

class BlanketOrderTemplateFooter(models.Model):
    _name = "blanket.order.template.footer"
    _description = "Blanket Order Template Footer"

    template_id = fields.Many2one(comodel_name='blanket.order.templates', string='Template', required=True, ondelete="cascade")
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='Field')
    sequence = fields.Integer(string='Sequence')