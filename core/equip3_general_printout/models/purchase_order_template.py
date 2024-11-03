
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _


class PurchaseOrderTemplate(models.Model):
    _name = "purchase.order.template"
    _description = "Purchase Order Template"

    name = fields.Char(string='Name', required=True)
    purchase_order_header_ids = fields.Many2many(
            'ir.model.fields',
            'purchase_order_template_header_model_fields_rel',
            'model_id', 'order_id')
    purchase_order_table_ids = fields.Many2many(
        'ir.model.fields',
        'order_line_template_model_fields_rel',
        'model_id', 'order_line_id')
    purchase_order_footer_ids = fields.Many2many(
        'ir.model.fields',
        'purchase_order_template_footer_model_fields_rel', 
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

    purchase_order_header_sequence_ids = fields.One2many(comodel_name='purchase.order.template.header', inverse_name='template_id', string='Header')
    purchase_order_table_sequence_ids = fields.One2many(comodel_name='purchase.order.template.table', inverse_name='template_id', string='Table')
    purchase_order_footer_sequence_ids = fields.One2many(comodel_name='purchase.order.template.footer', inverse_name='template_id', string='Footer')
    

    # @api.model
    # def _get_field_ids(self, vals):
    #     data = []
    #     for line in vals:
    #         data.append(line[2].get('field_id'))
    #     return data

    # @api.model
    # def create(self, vals):
    #     context = dict(self.env.context) or {}
    #     if context.get('default_po_header_ids'):
    #         vals['purchase_order_header_ids'] = [(6, 0, self._get_field_ids(context.get('default_po_header_ids')))]
    #     if context.get('default_po_table_ids'):
    #         vals['purchase_order_table_ids'] = [(6, 0, self._get_field_ids(context.get('default_po_table_ids')))]
    #     if context.get('default_po_footer_ids'):
    #         vals['purchase_order_footer_ids'] = [(6, 0, self._get_field_ids(context.get('default_po_footer_ids')))]
    #     return super(PurchaseOrderTemplate, self).create(vals)


    @api.model
    def _create_default_template_rfq_and_po(self):
        # DEFAULT TEMPLATE FOR RFQ
        default_report_rfq = self.env.ref('equip3_general_printout.default_rerport_custom_print_rfq')
        if not default_report_rfq:
            default_report_rfq = self.sudo().search([('name','=','Default Template RFQ')],limit=1)
            if not default_report_rfq:
                default_report_rfq = self.sudo().create({
                    'name':'Default Template RFQ',
                    'orientation':'potrait',
                    'size':'A4',
                    })
        
        # Auto Reset ketika upgrade
        # if not default_report_rfq.purchase_order_header_ids:
        field_headers = [
                'name',
                'date_order',
                'create_date',
            ]
        rfq_header_ids = self.env['ir.model.fields'].sudo().search([
            ('model','=','purchase.order'),
            ('name','in',field_headers)
        ])
        purchase_order_header_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_headers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model','=','purchase.order'),
                ('name','=',field)
            ],limit=1)
            if field_id:
                purchase_order_header_sequence_ids.append((0,0,{'field_id':field_id.id,'sequence':sequence}))
                sequence+=1
        default_report_rfq.purchase_order_header_sequence_ids = purchase_order_header_sequence_ids
        default_report_rfq.purchase_order_header_ids = [(6,0,rfq_header_ids.ids)]

        # Auto Reset ketika upgrade
        # if not default_report_rfq.purchase_order_table_ids:
        field_tables = [
                'sequence2',
                'image_256',
                'product_id',
                'name',
                'date_planned',
                'destination_warehouse_id',
                'product_qty',
            ]
        rfq_table_ids = self.env['ir.model.fields'].sudo().search([
            ('model','=','purchase.order.line'),
            ('name','in',field_tables)
        ])
        purchase_order_table_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_tables:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model','=','purchase.order.line'),
                ('name','=',field)
            ],limit=1)
            if field_id:
                purchase_order_table_sequence_ids.append((0,0,{'field_id':field_id.id,'sequence':sequence}))
                sequence+=1
        default_report_rfq.purchase_order_table_sequence_ids = purchase_order_table_sequence_ids
        default_report_rfq.purchase_order_table_ids = [(6,0,rfq_table_ids.ids)]

        # Auto Reset ketika upgrade
        # if not default_report_rfq.purchase_order_footer_ids:
        field_footers = [
                'sign_on',
                'digital_sign',
                'sign_by',
                'designation',
            ]
        rfq_footer_ids = self.env['ir.model.fields'].sudo().search([
            ('model','=','purchase.order'),
            ('name','in',field_footers)
        ])
        purchase_order_footer_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_footers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model','=','purchase.order'),
                ('name','=',field)
            ],limit=1)
            if field_id:
                purchase_order_footer_sequence_ids.append((0,0,{'field_id':field_id.id,'sequence':sequence}))
                sequence+=1
        default_report_rfq.purchase_order_footer_sequence_ids = purchase_order_footer_sequence_ids
        default_report_rfq.purchase_order_footer_ids = [(6,0,rfq_footer_ids.ids)]

        # DEFAULT TEMPLATE FOR PO
        default_report_po = self.env.ref('equip3_general_printout.default_rerport_custom_print_po')
        if not default_report_po:
            default_report_po = self.sudo().search([('name','=','Default Template PO')],limit=1)
            if not default_report_po:
                default_report_po = self.sudo().create({
                    'name':'Default Template PO',
                    'orientation':'potrait',
                    'size':'A4',
                    })
        
        # Auto Reset ketika upgrade
        # if not default_report_po.purchase_order_header_ids:
        field_headers = [
                'name',
                'date_approve',
            ]
        rfq_header_ids = self.env['ir.model.fields'].sudo().search([
            ('model','=','purchase.order'),
            ('name','in',field_headers)
        ])
        purchase_order_header_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_headers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model','=','purchase.order'),
                ('name','=',field)
            ],limit=1)
            if field_id:
                purchase_order_header_sequence_ids.append((0,0,{'field_id':field_id.id,'sequence':sequence}))
                sequence+=1
        default_report_po.purchase_order_header_sequence_ids = purchase_order_header_sequence_ids
        default_report_po.purchase_order_header_ids = [(6,0,rfq_header_ids.ids)]

        # Auto Reset ketika upgrade
        # if not default_report_po.purchase_order_table_ids:
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
        rfq_table_ids = self.env['ir.model.fields'].sudo().search([
            ('model','=','purchase.order.line'),
            ('name','in',field_tables)
        ])
        purchase_order_table_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_tables:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model','=','purchase.order.line'),
                ('name','=',field)
            ],limit=1)
            if field_id:
                purchase_order_table_sequence_ids.append((0,0,{'field_id':field_id.id,'sequence':sequence}))
                sequence+=1
        default_report_po.purchase_order_table_sequence_ids = purchase_order_table_sequence_ids
        default_report_po.purchase_order_table_ids = [(6,0,rfq_table_ids.ids)]

        # Auto Reset ketika upgrade
        # if not default_report_po.purchase_order_footer_ids:
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
        rfq_footer_ids = self.env['ir.model.fields'].sudo().search([
            ('model','=','purchase.order'),
            ('name','in',field_footers)
        ])
        purchase_order_footer_sequence_ids = [(5,0,0)]
        sequence = 1
        for field in field_footers:
            field_id = self.env['ir.model.fields'].sudo().search([
                ('model','=','purchase.order'),
                ('name','=',field)
            ],limit=1)
            if field_id:
                purchase_order_footer_sequence_ids.append((0,0,{'field_id':field_id.id,'sequence':sequence}))
                sequence+=1
        default_report_po.purchase_order_footer_sequence_ids = purchase_order_footer_sequence_ids
        default_report_po.purchase_order_footer_ids = [(6,0,rfq_footer_ids.ids)]
        


class PurchaseOrderTemplateHeader(models.Model):
    _name = "purchase.order.template.header"
    _description = "Purchase Order Template Header"

    template_id = fields.Many2one(comodel_name='purchase.order.template', string='Template', required=True, ondelete="cascade")
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='Field')
    sequence = fields.Integer(string='Sequence')

class PurchaseOrderTemplateTable(models.Model):
    _name = "purchase.order.template.table"
    _description = "Purchase Order Template Table"

    template_id = fields.Many2one(comodel_name='purchase.order.template', string='Template', required=True, ondelete="cascade")
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='Field')
    sequence = fields.Integer(string='Sequence')

class PurchaseOrderTemplateFooter(models.Model):
    _name = "purchase.order.template.footer"
    _description = "Purchase Order Template Footer"

    template_id = fields.Many2one(comodel_name='purchase.order.template', string='Template', required=True, ondelete="cascade")
    field_id = fields.Many2one(comodel_name='ir.model.fields', string='Field')
    sequence = fields.Integer(string='Sequence')
    
    
    