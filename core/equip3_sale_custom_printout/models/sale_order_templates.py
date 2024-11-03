
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _


class SaleOrderTemplates(models.Model):
    _name = "sale.order.templates"
    _description = "Sale Order Templates"

    name = fields.Char(string='Name', required=True)
    sale_order_header_ids = fields.Many2many(
            'ir.model.fields',
            'sale_order_template_header_model_fields_rel',
            'model_id', 'order_id')
    sale_order_table_ids = fields.Many2many(
        'ir.model.fields',
        'sale_order_template_table_model_fields_rel',
        'model_id', 'order_line_id')
    sale_order_footer_ids = fields.Many2many(
        'ir.model.fields',
        'sale_order_template_footer_model_fields_rel', 
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

    sale_order_header_sequence_ids = fields.One2many(comodel_name='sale.order.template.header', inverse_name='template_id', string='Header')
    sale_order_table_sequence_ids = fields.One2many(comodel_name='sale.order.template.table', inverse_name='template_id', string='Table')
    sale_order_footer_sequence_ids = fields.One2many(comodel_name='sale.order.template.footer', inverse_name='template_id', string='Footer')
    
    @api.model
    def _create_default_template_rfq_and_so(self):
        default_report_quotation = self.env.ref('equip3_sale_custom_printout.default_rerport_custom_print_quotations')
        if not default_report_quotation:
            default_report_quotation = self.sudo().search([('name', '=', 'Default Template Quotation')],limit=1)
            if not default_report_quotation:
                default_report_quotation = self.sudo().create({
                    'name':'Default Template Quotation',
                    'orientation':'potrait',
                    'size':'A4',
                    })
        field_headers = [
                'name',
                'date_order',
                'create_date',
            ]
        quotation_header_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'sale.order'),
            ('name', 'in', field_headers)
        ])
        sale_order_header_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_headers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'sale.order'),
                ('name', '=', field)
            ],limit=1)
            if field_id:
                sale_order_header_sequence_ids.append((0,0,{'field_id':field_id.id, 'sequence':sequence}))
                sequence+=1
        default_report_quotation.sale_order_header_sequence_ids = sale_order_header_sequence_ids
        default_report_quotation.sale_order_header_ids = [(6, 0, quotation_header_ids.ids)]

        field_tables = [
                'sequence2',
                'image_256',
                'product_id',
                'name',
                'date_planned',
                'destination_warehouse_id',
                'product_qty',
            ]
        quotation_table_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'sale.order.line'),
            ('name', 'in', field_tables)
        ])
        sale_order_table_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_tables:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'sale.order.line'),
                ('name', '=', field)
            ],limit=1)
            if field_id:
                sale_order_table_sequence_ids.append((0,0,{'field_id':field_id.id, 'sequence':sequence}))
                sequence+=1
        default_report_quotation.sale_order_table_sequence_ids = sale_order_table_sequence_ids
        default_report_quotation.sale_order_table_ids = [(6, 0, quotation_table_ids.ids)]
        field_footers = [
                'sign_on',
                'digital_sign',
                'sign_by',
                'designation',
            ]
        quotation_footer_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'sale.order'),
            ('name', 'in', field_footers)
        ])
        sale_order_footer_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_footers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'sale.order'),
                ('name', '=', field)
            ],limit=1)
            if field_id:
                sale_order_footer_sequence_ids.append((0,0,{'field_id':field_id.id, 'sequence':sequence}))
                sequence+=1
        default_report_quotation.sale_order_footer_sequence_ids = sale_order_footer_sequence_ids
        default_report_quotation.sale_order_footer_ids = [(6, 0, quotation_footer_ids.ids)]
        
        default_report_so = self.env.ref('equip3_sale_custom_printout.default_rerport_custom_print_so')
        if not default_report_so:
            default_report_so = self.sudo().search([('name', '=', 'Default Template SO')], limit=1)
            if not default_report_so:
                default_report_so = self.sudo().create({
                    'name':'Default Template SO',
                    'orientation':'potrait',
                    'size':'A4',
                    })
    
        field_headers = [
                'name',
                'date_approve',
            ]
        so_quotation_header_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=' ,'sale.order'),
            ('name', 'in', field_headers)
        ])
        sale_order_header_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_headers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'sale.order'),
                ('name', '=', field)
            ],limit=1)
            if field_id:
                sale_order_header_sequence_ids.append((0,0,{'field_id':field_id.id, 'sequence':sequence}))
                sequence+=1
        default_report_so.sale_order_header_sequence_ids = sale_order_header_sequence_ids
        default_report_so.sale_order_header_ids = [(6, 0, so_quotation_header_ids.ids)]

        field_tables = [
                'sequence2',
                'image_256',
                'product_id',
                'name',
                'date_planned',
                'destination_warehouse_id',
                'product_qty',
                'price_unit',
                'discount_method',
                'discount_amount',
                'taxes_id',
                'price_subtotal',
            ]
        quotation_table_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=' ,'sale.order.line'),
            ('name', 'in' ,field_tables)
        ])
        sale_order_table_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_tables:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'sale.order.line'),
                ('name', '=', field)
            ],limit=1)
            if field_id:
                sale_order_table_sequence_ids.append((0,0,{'field_id':field_id.id, 'sequence':sequence}))
                sequence+=1
        default_report_so.sale_order_table_sequence_ids = sale_order_table_sequence_ids
        default_report_so.sale_order_table_ids = [(6, 0, quotation_table_ids.ids)]

        field_footers = [
                'amount_untaxed',
                'discount_amt',
                'amount_tax',
                'amount_total',
                'sign_on',
                'digital_sign',
                'sign_by',
                'designation',
            ]
        quotation_footer_ids = self.env['ir.model.fields'].sudo().search([
            ('model', '=', 'sale.order'),
            ('name', 'in', field_footers)
        ])
        sale_order_footer_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_footers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model', '=', 'sale.order'),
                ('name', '=', field)
            ],limit=1)
            if field_id:
                sale_order_footer_sequence_ids.append((0,0,{'field_id':field_id.id, 'sequence':sequence}))
                sequence+=1
        default_report_so.sale_order_footer_sequence_ids = sale_order_footer_sequence_ids
        default_report_so.sale_order_footer_ids = [(6, 0, quotation_footer_ids.ids)]
    
    
class SaleOrderTemplateHeader(models.Model):
    _name = "sale.order.template.header"
    _description = "Sale Order Template Header"

    template_id = fields.Many2one(comodel_name='sale.order.templates', string='Template', required=True, ondelete="cascade")
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='Field')
    sequence = fields.Integer(string='Sequence')

class SaleOrderTemplateTable(models.Model):
    _name = "sale.order.template.table"
    _description = "Sale Order Template Table"

    template_id = fields.Many2one(comodel_name='sale.order.templates', string='Template', required=True, ondelete="cascade")
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='Field')
    sequence = fields.Integer(string='Sequence')

class SaleOrderTemplateFooter(models.Model):
    _name = "sale.order.template.footer"
    _description = "Sale Order Template Footer"

    template_id = fields.Many2one(comodel_name='sale.order.templates', string='Template', required=True, ondelete="cascade")
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='Field')
    sequence = fields.Integer(string='Sequence')