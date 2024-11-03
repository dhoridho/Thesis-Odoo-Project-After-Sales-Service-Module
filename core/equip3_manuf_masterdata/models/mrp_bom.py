import io
import base64
import xlsxwriter
import logging

from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from odoo.osv import expression
from odoo.addons.evo_bill_of_material_revised.models.bill_of_material import BillOfMaterial as EvoBillOfMaterial

_logger = logging.getLogger(__name__)

class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    @api.model
    def create(self, vals):
        records = super(MrpBom, self).create(vals)
        for record in records:
            record._check_recursion()
            record._set_operations()
        return records

    def write(self, vals):
        res = super(MrpBom, self).write(vals)
        for record in self:
            record._check_recursion()
            record._set_operations()
        return res

    def _register_hook(self):

        def make_bom_find():
            @api.model
            def _bom_find(self, product_tmpl=None, product=None, picking_type=None, company_id=False, bom_type=False):
                return super(EvoBillOfMaterial, self)._bom_find(product_tmpl=product_tmpl, product=product, picking_type=picking_type, company_id=company_id, bom_type=bom_type)
            return _bom_find

        def make_bom_find_domain():
            @api.model
            def _bom_find_domain(self, product_tmpl=None, product=None, picking_type=None, company_id=False, bom_type=False):
                domain = super(EvoBillOfMaterial, self)._bom_find_domain(product_tmpl=product_tmpl, product=product, picking_type=picking_type, company_id=company_id, bom_type=bom_type)
                domain += [('state', '=', self.env.context.get('bom_state', 'confirm'))]
                return domain
            return _bom_find_domain

        EvoBillOfMaterial._patch_method('_bom_find', make_bom_find())
        EvoBillOfMaterial._patch_method('_bom_find_domain', make_bom_find_domain())
        return super(MrpBom, self)._register_hook()

    def _check_recursion(self, bom=None):
        self.ensure_one()
        if not bom:
            bom = self
        for line in self.bom_line_ids:
            if bom.product_tmpl_id == line.product_id.product_tmpl_id:
                raise ValidationError(_('Cannot create circular BoM! (%s > %s > %s)' % (bom.product_tmpl_id.display_name, self.product_tmpl_id.display_name, line.product_id.product_tmpl_id.display_name)))
            for child_bom in line.product_id.active_bom_ids:
                child_bom._check_recursion(bom=bom)

    def _set_operations(self):
        self.ensure_one()
        if 'import_file' in self.env.context:
            return
        operations = self.operation_ids
        for field_name in ('bom_line_ids', 'tool_ids'):
            for line in self[field_name]:
                line.operation_id = operations.filtered(lambda o: o.name == line.operation_two_id.name).id

    @api.depends('operation_ids', 'operation_ids.name')
    def _compute_operation_ids(self):
        bom_operation = self.env['mrp.bom.operation']
        for record in self:
            values = []
            for operation in record.operation_ids:
                values += [{'name': operation.name}]
            operation_ids = bom_operation.create(values)
            if record.operation_two_ids:
                record.operation_two_ids.unlink()
            record.operation_two_ids = [(6, 0, operation_ids.ids)]

    @api.model
    def _product_tmpl_domain(self):
        return """[
            ('type', 'in', ('product', 'consu')),
            '|', ('company_id', '=', False), ('company_id', '=', company_id)
        ]"""

    @api.depends('equip_bom_type')
    def _compute_use_operations(self):
        operation_types = self._bom_types_with_operations()
        for bom in self:
            bom.use_operations = bom.equip_bom_type in operation_types

    @api.model
    def _bom_types_with_operations(self):
        return ['mrp']

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        if name == '' and operator == 'ilike':
            return super(MrpBom, self)._name_search(name=name, args=args, operator=operator, limit=limit, name_get_uid=name_get_uid)
        
        args = list(args or [])
        # optimize out the default criterion of ``ilike ''`` that matches everything
        if not self._rec_name:
            _logger.warning("Cannot execute name_search, no _rec_name defined on %s", self._name)
        elif not (name == '' and operator == 'ilike'):
            args = expression.AND([args, [
                '|', '|', '|',
                (self._rec_name, operator, name),
                ('code', operator, name),
                ('product_tmpl_id', operator, name),
                ('product_id.product_template_attribute_value_ids.name', operator, name)
            ]])
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)

    def name_get(self):
        result = []
        for record in self:
            product_tmpl_id = record.product_tmpl_id
            product_id = record.product_id

            name = '[%s] [%s] [%s]' % (record.code, product_tmpl_id.default_code, product_tmpl_id.name)
            if product_id:
                variant = product_id.product_template_attribute_value_ids._get_combination_name()
                if variant:
                    name += ' (%s)' % (variant,)
            result.append((record.id, name))
        return result

    @api.model
    def _search(self, args, offset=0, limit=None, order=None, count=False, access_rights_uid=None):
        if self.env.context.get('bom_state', False):
            args = expression.AND([args, [('state', '=', self.env.context.get('bom_state', False))]])
        return super(MrpBom, self)._search(args, offset=offset, limit=limit, order=order, count=count, access_rights_uid=access_rights_uid)
        
    # BoM fields 
    # just add tracking=True do not re-declare whole attributes
    code = fields.Char(tracking=True, string='BoM Name')
    type = fields.Selection(tracking=True)
    product_tmpl_id = fields.Many2one(tracking=True)
    product_id = fields.Many2one(tracking=True)
    product_qty = fields.Float(tracking=True)
    company_id = fields.Many2one(tracking=True, default=lambda self: self.env.company, readonly=True)
    product_uom_id = fields.Many2one(tracking=True)
    ready_to_produce = fields.Selection(string='Production Readiness', help='Defines when a Production Order is considered as ready to be started')
    operation_start_mode = fields.Selection(selection=[
        ('flexible', 'Flexible, allows operations to start immediately'),
        ('sequential', 'Sequential, the operations start one after another operation has finished'),
        ('adaptive', 'Adaptive, can start immediately with the partial output of the previous operation')
    ], string='Operation Start Mode', default='sequential', required=True)

    branch_id = fields.Many2one('res.branch', string='Branch', default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False, domain=lambda self: [('id', 'in', self.env.branches.ids)], tracking=True)
    create_uid = fields.Many2one('res.users', string='Create By', default=lambda self: self.env.user, tracking=True)
    
    tool_ids = fields.One2many('mrp.bom.tools', 'bom_id', string='Tools')
    bom_tools = fields.Boolean(related='company_id.bom_tools', string='Is Tools')

    operation_two_ids = fields.Many2many('mrp.bom.operation', compute=_compute_operation_ids)
    is_branch_required = fields.Boolean(related='company_id.show_branch')
    
    finished_type = fields.Selection(selection=[
        ('single', 'Single Finished Good'),
        ('multi', 'Multiple Finished Goods')
    ], string='Finished Goods Type', default='single', required=True, tracking=True)
    finished_ids = fields.One2many('mrp.bom.finished', 'bom_id', string='Finished Goods', copy=True)

    rejected_product_id = fields.Many2one('product.product', string='Rejected Goods')

    # technical field, kitchen & assembly
    equip_bom_type = fields.Selection(selection=[('mrp', 'Manufacturing')], default='mrp')
    product_tmpl_id = fields.Many2one('product.template', domain=_product_tmpl_domain)
    use_operations = fields.Boolean(compute=_compute_use_operations)

    @api.onchange('product_tmpl_id')
    def _onchage_set_rejected_product(self):
        self.rejected_product_id = self.product_tmpl_id.product_variant_id.id

    def _unique_operation_name(self):
        for bom in self:
            operations = bom.operation_ids
            operation_names = operation.mapped('name')
            if len(set(operation_names)) != len(operations):
                raise ValidationError(_('Operation name must be unique per BoM!'))

    @api.onchange('branch_id')
    def _onchange_branch(self):
        self.operation_ids.update({'branch_id': self.branch_id.id})

    def _prepare_finished_values(self):
        self.ensure_one()
        return {
            'product_tmpl_id': self.product_tmpl_id.id,
            'product_id': self.product_id.id or self.product_tmpl_id.product_variant_id.id,
            'product_qty': self.product_qty,
            'product_uom_id': self.product_uom_id.id,
            'is_mandatory': True
        }

    @api.onchange('finished_type', 'product_tmpl_id', 'product_id', 'product_qty', 'product_uom_id')
    def _set_finished_good(self):
        finished_line = self.finished_ids.filtered(lambda o: o.is_mandatory)
        finished_values = []
        if not finished_line:
            if self.product_tmpl_id:
                product_id = self.product_id.id or self.product_tmpl_id.product_variant_id.id
                if product_id:
                    values = self._prepare_finished_values()
                    finished_values = [(0, 0, values)]
        else:
            if self.product_tmpl_id:
                values = self._prepare_finished_values()
                finished_values = [(1, finished_line.id, {
                    'product_tmpl_id': values.get('product_tmpl_id', False),
                    'product_id': values.get('product_id', False),
                    'product_qty': values.get('product_qty', 0.0),
                    'product_uom_id': values.get('product_uom_id', False),
                })]
            else:
                finished_values = [(2, finished_line.id)]

        if finished_values:
            self.finished_ids = finished_values

    def _set_finished_goods(self):
        for record in self:
            record._set_finished_good()

    @api.model
    def _bom_find_domain(self, product_tmpl=None, product=None, picking_type=None, company_id=False, bom_type=False):
        domain = super(MrpBom, self)._bom_find_domain(product_tmpl=product_tmpl, product=product, picking_type=picking_type, company_id=company_id, bom_type=bom_type)
        equip_bom_type = self.env.context.get('equip_bom_type', 'mrp')
        branch_id = self.env.context.get('branch_id', self.env.branch.id)
        
        domain += [('equip_bom_type', '=', equip_bom_type)]
        domain += ['|', ('branch_id', '=', False), ('branch_id', '=', branch_id)]
        return domain

    def print_xlsx_report(self):

        def flatten_boms(bom, level=1):
            boms = [(level, bom)]
            for line in bom.bom_line_ids:
                if line.child_bom_id:
                    boms += flatten_boms(line.child_bom_id, level=level+1)
            return boms

        self.ensure_one()

        # [] bracket causing xlsx wont open
        file_name = '%s.xlsx' % self.product_tmpl_id.display_name.replace('[', '').replace(']', '').strip()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        style = {
            'header': workbook.add_format({
                'bold': 1,
                'border': 1,
                'align': 'center',
                'valign': 'vcenter',
            }),
            'bordered': workbook.add_format({
                'border': 1
            })
        }

        headers = [
            'Sequence', 
            'Reference', 
            'Product', 
            'Quantity', 
            'Unit of Measure', 
            'Company', 
            'Branch', 
            'BoM Lines/Material', 
            'BoM Lines/Quantity', 
            'BoM Lines/Unit of Measure'
        ]

        width = []
        for col, head in enumerate(headers):
            worksheet.write(0, col, head, style['header'])
            width += [len(head) + 2]

        row = 1
        for level, bom in sorted(flatten_boms(self), key=lambda b: b[0]):
            values = [
                level,
                bom.code is False and '' or bom.code,
                bom.product_tmpl_id.display_name,
                bom.product_qty,
                bom.product_uom_id.display_name,
                bom.company_id.display_name,
                bom.branch_id.display_name,
            ]

            for col, value in enumerate(values):
                worksheet.write(row, col, value, style['bordered'])
                width[col] = max([width[col], len(str(value))]) + 2

            col += 1
            if bom.bom_line_ids:
                for i, line in enumerate(bom.bom_line_ids):
                    if i > 0:
                        # in case bom bom_line_ids > 1 then just create border
                        for j in range(len(values)):
                            worksheet.write(row, j, '', style['bordered'])

                    child_values = [
                        line.product_id.display_name, 
                        line.product_qty, 
                        line.product_uom_id.display_name
                    ]

                    for j, v in enumerate(child_values):
                        worksheet.write(row, col + j, v, style['bordered'])
                        width[col + j] = max([width[col + j], len(str(v))]) + 2
                    row += 1
            else:
                # in case bom has no bom_line_ids then just create border
                for j in range(3):
                    worksheet.write(row, col + j, '', style['bordered'])
                row += 1

        for col, w in enumerate(width):
            worksheet.set_column(col, col, w)

        workbook.close()

        output.seek(0)
        result = base64.b64encode(output.read())
        attachment_id = self.env['ir.attachment'].create({'name': file_name, 'store_fname': file_name, 'datas': result})
        output.close()
        return attachment_id.id


class MrpBomOperation(models.Model):
    _name = 'mrp.bom.operation'
    _description = 'MRP BoM Operation'

    name = fields.Char(required=True)


class MrpBomLine(models.Model):
    _inherit = 'mrp.bom.line'

    branch_id = fields.Many2one(related='bom_id.branch_id')
    product_id = fields.Many2one('product.product', domain="[('type', '=', 'product'), '|', ('company_id', '=', company_id), ('company_id', '=', False)]", string='Material')
    alternative_component_ids = fields.Many2many('product.product', string='Alternative Material')

    operation_two_ids = fields.Many2many('mrp.bom.operation', related='bom_id.operation_two_ids')
    operation_two_id = fields.Many2one('mrp.bom.operation', string='Operation', domain="[('id', 'in', operation_two_ids)]")
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure')

    @api.depends('product_id', 'bom_id', 'branch_id')
    def _compute_child_bom_id(self):
        for line in self:
            if not line.product_id:
                line.child_bom_id = False
            else:
                line.child_bom_id = self.env['mrp.bom'].with_context(branch_id=line.branch_id.id)._bom_find(
                    product_tmpl=line.product_id.product_tmpl_id,
                    product=line.product_id)


class MrpBomFinished(models.Model):
    _name = 'mrp.bom.finished'
    _description = 'MRP BoM Finished'

    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', required=True, ondelete='cascade')
    product_tmpl_id = fields.Many2one('product.template', string='Product', check_company=True, index=True, required=True, domain="[('type', '=', 'product'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    product_id = fields.Many2one('product.product', string='Variant', check_company=True, index=True, required=True, domain="['&', ('product_tmpl_id', '=', product_tmpl_id), ('type', 'in', ['product', 'consu']),  '|', ('company_id', '=', False), ('company_id', '=', company_id)]",)
    product_qty = fields.Float(digits='Unit of Measure', required=True, default=1.0)
    product_uom_id = fields.Many2one('uom.uom', string='Unit of Measure', required=True, domain="[('category_id', '=', product_uom_category_id)]")

    # technical fields
    is_mandatory = fields.Boolean()
    product_uom_category_id = fields.Many2one(related='product_tmpl_id.uom_id.category_id')
    company_id = fields.Many2one(related='bom_id.company_id')

    @api.onchange('product_tmpl_id')
    def onchange_product_tmpl_id(self):
        if self.product_tmpl_id:
            self.product_uom_id = self.product_tmpl_id.uom_id.id
            product_variant_ids = self.product_tmpl_id.product_variant_ids
            if product_variant_ids:
                self.product_id = product_variant_ids[0].id
