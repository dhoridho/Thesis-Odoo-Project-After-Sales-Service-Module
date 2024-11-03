# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import json


class ShQcPoint(models.Model):
    _inherit = 'sh.qc.point'

    type_of_qc = fields.Selection([('quantitative', 'Quantitative'), ('qualitative', 'Qualitative'), (
        'both', 'Quantitative & Qualitative')], 'QC Type', default='quantitative')
    quantitative_ids = fields.One2many(
        "qp.quantitative.lines", 'qc_point_id', string="Quantitative Lines")
    qualitative_ids = fields.One2many(
        'qp.qualitative.lines', 'qc_item_dir_id', string="Qualitative Lines")
    block_failed = fields.Boolean(string='Block Failed Product', default=False)
    is_product_grade = fields.Boolean(string='Is Product Grade', default=False)
    product_grade_ids = fields.Many2many(comodel_name='product.product')
    product_grade_id_domain = fields.Char(
        compute='_compute_product_grade_id_domain')
    operation_ids_domain = fields.Char(compute='_compute_operation_ids_domain')
    branch_id = fields.Many2one(
        'res.branch',
        string='Branch',
        default=lambda self: self.env.branch.id if len(self.env.branches) == 1 else False,
        domain=lambda self: [('id', 'in', self.env.branches.ids)],
        tracking=True)

    @api.depends('branch_id')
    def _compute_operation_ids_domain(self):
        self.operation_ids_domain = json.dumps([('id', 'in', [])])
        warehouse_ids = self.env['stock.warehouse'].search([('branch_id', '=', self.branch_id.id)])
        StockPickingType = self.env['stock.picking.type']
        if warehouse_ids:
            picking_type_ids = StockPickingType.search([('warehouse_id', 'in', warehouse_ids.ids)])
            if picking_type_ids:
                self.operation_ids_domain = json.dumps(
                    [('id', 'in', picking_type_ids.ids)])


    @api.depends('product_ids')
    def _compute_product_grade_id_domain(self):
        self.product_grade_id_domain = json.dumps([])
        product_grade_ids = self.env['product.product'].search(
            [('product_tmpl_id', 'in', self.product_ids.product_tmpl_id.ids)])
        if product_grade_ids:
            self.product_grade_id_domain = json.dumps(
                [('id', 'in', product_grade_ids.ids)])

    @api.constrains('product_ids', 'operation_ids')
    def _check_duplicate(self):
        point_obj = self.search([('product_ids', 'in', self.product_ids.ids), (
            'operation_ids', 'in', self.operation_ids.ids), ('id', '!=', self.id)], limit=1)
        if point_obj:
            raise ValidationError(
                'Quality point of product and picking type already exist')

    @api.constrains('type_of_qc', 'qualitative_ids', 'quantitative_ids')
    def _check_lines(self):
        for record in self:
            if record.type_of_qc == "quantitative" and not record.quantitative_ids:
                raise ValidationError("Quantitative Lines are required!")
            elif record.type_of_qc == "qualitative" and not record.qualitative_ids:
                raise ValidationError("Qualitative Lines are required!")

    @api.constrains('name')
    def _validate_name(self):
        existing_name = self.env['sh.qc.point'].search(
            [('name', '=', self.name), ('id', '!=', self.id)], limit=1)
        if existing_name:
            raise ValidationError(
                _('Quality point name already exists: %s', existing_name.name))

    @api.onchange('product_ids', 'product_grade_ids', 'operation_ids', 'is_product_grade')
    # raise validation if product is not variant and product grade is selected
    def check_is_product_variant(self):
        if self.product_ids and self.is_product_grade:
            for product in self.product_ids:
                product_varian = len(
                    product.product_template_attribute_value_ids)
                if product_varian <= 0:
                    raise ValidationError(
                        "Grading only use for product variant")
        if self.operation_ids and self.is_product_grade:
            for operation in self.operation_ids:
                if operation.code not in ('incoming', 'internal') or operation.code == 'internal' and 'INT/IN' not in operation.sequence_code:
                    raise ValidationError(
                        "Grading only use for Receipt and Internal Operation IN")
