from odoo import api, fields, models


OPERATION_TYPES = [
    ('extraction', 'Extraction'), 
    ('hauling', 'Hauling'),
    ('waste_removal', 'Waste Removal'),
    ('processing', 'Processing'),
    ('shipment', 'Shipment')
]


class MiningOperations(models.Model):
    _name = 'mining.operations.two'
    _description = 'Mining Operation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.branch.id if len(self.env.branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids)]

    @api.depends('line_ids', 'line_ids.primary')
    def _compute_next_primary(self):
        for record in self:
            record.next_primary = len(record.line_ids.filtered(lambda l: l.primary)) == 0

    @api.depends('line_ids', 'line_ids.primary', 'line_ids.update_sequence', 'line_ids.product_id', 'line_ids.uom_id',
                 'output_line_ids', 'output_line_ids.primary', 'output_line_ids.update_sequence', 'output_line_ids.product_id', 'output_line_ids.uom_id')
    def _compute_primary(self):
        for record in self:
            if record.operation_type_id == "processing":
                primary_lines = record.output_line_ids.filtered(lambda l: l.primary)
                primary_product_id = False
                primary_uom_id = False
                if primary_lines:
                    primary_line = sorted(primary_lines, key=lambda l: l.update_sequence)[-1]
                    primary_product_id = primary_line.product_id.id
                    primary_uom_id = primary_line.uom_id.id
                primary_product_id = primary_product_id
                primary_uom_id = primary_uom_id
            else:
                primary_lines = record.line_ids.filtered(lambda l: l.primary)
                primary_product_id = False
                primary_uom_id = False
                if primary_lines:
                    primary_line = sorted(primary_lines, key=lambda l: l.update_sequence)[-1]
                    primary_product_id = primary_line.product_id.id
                    primary_uom_id = primary_line.uom_id.id
                primary_product_id = primary_product_id
                primary_uom_id = primary_uom_id
            record.primary_product_id = primary_product_id
            record.primary_uom_id = primary_uom_id

    site_id = fields.Many2one('mining.site.control', stirng='Mining Site', required=True, tracking=True)
    name = fields.Char(required=True, copy=False, tracking=True)
    operation_type_id = fields.Selection(string='Operation Type', selection=OPERATION_TYPES, tracking=True, required=True)

    uom_id = fields.Many2one(comodel_name='uom.uom', string='Unit of Measure', required=True)
    uom_category_id = fields.Many2one(comodel_name='uom.category', related='uom_id.category_id')

    location_id = fields.Many2one('stock.location', string='Location', tracking=True, domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]")
    location_src_id = fields.Many2one('stock.location', string='Source Location', tracking=True, domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]")
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', tracking=True, domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]")

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=_default_branch, domain=_domain_branch)

    line_ids = fields.One2many('mining.operation.line', 'operation_id', string='Product')
    input_line_ids = fields.One2many('mining.operation.line', 'input_operation_id', string='Product')
    output_line_ids = fields.One2many('mining.operation.line', 'output_operation_id', string='Product')
    next_primary = fields.Boolean(compute=_compute_next_primary)

    # used in mining.site
    primary_product_id = fields.Many2one('product.product', string='Primary Product', compute=_compute_primary)
    primary_uom_id = fields.Many2one('uom.uom', string='Primary UoM', compute=_compute_primary)

    @api.onchange('line_ids', 'input_line_ids', 'output_line_ids')
    def _onchange_line_ids(self):
        if self.input_line_ids:
            primary_lines = self.input_line_ids.filtered(lambda l: l.primary)
        elif self.output_line_ids:
            primary_lines = self.output_line_ids.filtered(lambda l: l.primary)
        else:
            primary_lines = self.line_ids.filtered(lambda l: l.primary)
        if len(primary_lines) > 1:
            primary_line = sorted(primary_lines, key=lambda l: l.update_sequence)[-1]
            other_lines = primary_lines - primary_line
            other_lines.update({'primary': False})


class MiningOperationLine(models.Model):
    _name = 'mining.operation.line'
    _description = 'Mining Operation Line'

    operation_id = fields.Many2one('mining.operations.two', string='Operation')
    input_operation_id = fields.Many2one('mining.operations.two', string='Operation')
    output_operation_id = fields.Many2one('mining.operations.two', string='Operation')
    qty = fields.Float(string='Quantity')
    product_id = fields.Many2one('product.product', string='Product', required=True, )
    uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, )
    operation_uom_category_id = fields.Many2one('uom.category', related='operation_id.uom_category_id')
    input_operation_uom_category_id = fields.Many2one('uom.category', related='input_operation_id.uom_category_id')
    output_operation_uom_category_id = fields.Many2one('uom.category', related='output_operation_id.uom_category_id')
    
    primary = fields.Boolean(string='Primary')

    # technical fields
    update_sequence = fields.Integer()

    @api.onchange('primary')
    def _onchange_primary(self):
        if self.primary:
            if self.input_operation_id:
                 self.update_sequence = max(self.input_operation_id.input_line_ids.mapped('update_sequence')) + 1
            elif self.output_operation_id:
                self.update_sequence = max(self.output_operation_id.output_line_ids.mapped('update_sequence')) + 1
            else:
                self.update_sequence = max(self.operation_id.line_ids.mapped('update_sequence')) + 1
           
    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.uom_id = self.product_id and self.product_id.uom_id.id or False
