# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_repr
from odoo.exceptions import ValidationError
from collections import defaultdict
from lxml import etree
from odoo.addons.base.models.ir_ui_view import (
transfer_field_to_modifiers, transfer_node_to_modifiers, transfer_modifiers_to_node,
)

def setup_modifiers(node, field=None, context=None, in_tree_view=False):
    modifiers = {}
    if field is not None:
        transfer_field_to_modifiers(field, modifiers)
    transfer_node_to_modifiers(
        node, modifiers, context=context)
    transfer_modifiers_to_node(modifiers, node)


class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    is_cost_price_per_warehouse = fields.Boolean(string="Is Cost price per warehouse?", store=True)

    @api.model
    def default_get(self, fields):
        res = super(StockWarehouse, self).default_get(fields)
        is_cost_price_per_warehouse = self.env['ir.config_parameter'].sudo().get_param('is_cost_price_per_warehouse')
        res['is_cost_price_per_warehouse'] = is_cost_price_per_warehouse
        return res

    @api.model
    def create(self,vals):
        result = super(StockWarehouse, self).create(vals)
        # products = self.env['product.product'].search([])
        # for product in products:
        #     product.generate_product_warehouse_cost()
        if result.is_cost_price_per_warehouse:
            products = self.env['product.product'].search([('type','=','product')])
            product_ids = products.ids

            new_cost_lines = []
            prod_wh_cost_lines = []
            product_id_lines = []

            for id in product_ids:
                prod_wh_cost = self.env['product.warehouse.cost'].search([('product_id','=',id)])
                if prod_wh_cost:
                    new_cost_lines.append((result.id, 0, result.company_id.id, prod_wh_cost.id))
                else:
                    prod_wh_cost_lines.append((result.id, 0, result.company_id.id))
                    product_id_lines.append(id)

            if new_cost_lines:
                sql = ('''
                    INSERT INTO product_warehouse_cost_line (warehouse_id, cost, company_id, prod_wh_cost_id)
                    VALUES %s
                ''')
                values = ','.join(self.env.cr.mogrify("(%s, %s, %s, %s)", record).decode('utf-8') for record in new_cost_lines)
                self.env.cr.execute(sql % values)

            if prod_wh_cost_lines:
                sql = ('''
                    INSERT INTO product_warehouse_cost (product_id)
                    VALUES %s
                    RETURNING id
                ''')
                values = ','.join(self.env.cr.mogrify("(%s)", record).decode('utf-8') for record in product_id_lines)
                self.env.cr.execute(sql % values)

                prod_wh_cost_id = self.env.cr.dictfetchall()[0]['id']
                prod_wh_cost_lines_updated = [data + (prod_wh_cost_id) for data in prod_wh_cost_lines]

                sql = ('''
                    INSERT INTO product_warehouse_cost_line (warehouse_id, cost, company_id, prod_wh_cost_id)
                    VALUES %s
                ''')
                values = ','.join(self.env.cr.mogrify("(%s, %s, %s, %s)", record).decode('utf-8') for record in prod_wh_cost_lines_updated)
                self.env.cr.execute(sql % values)

        return result


class ProductWarehouseCost(models.Model):
    _name = 'product.warehouse.cost'
    _description  = 'Product Warehouse Cost'
    
    
    product_id = fields.Many2one('product.product','Product', readonly=True)
    product_cost_line_ids = fields.One2many('product.warehouse.cost.line', 'prod_wh_cost_id', 'Warehouse Cost Lines', readonly=True)
    company_id = fields.Many2one('res.company')
    
    _sql_constraints = [
        ('product_id_id_uniq', 'unique (product_id,id)', 'The product of the Product Warehouse Cost must be unique !')
    ]
    
    def name_get(self):
        res = []
        for line in self:
            res.append((line.id, 'Cost Price List'))
        return res
    


class ProductWarehouseCostLine(models.Model):
    _name = 'product.warehouse.cost.line'
    _description  = 'Product Warehouse Cost'
    
    def _default_company(self):
        return self.env.company

    
    prod_wh_cost_id = fields.Many2one('product.warehouse.cost','Product Warehouse Cost')
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse')
    cost = fields.Monetary('Cost Price',
        currency_field="currency_id",)
    #cost = fields.Float('Cost Price')
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=_default_company,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency",
        readonly=True,
    )
    
    _sql_constraints = [
        ('warehouse_id_prod_wh_cost_id_uniq', 'unique (warehouse_id,prod_wh_cost_id)', 'The Warehouse of the Product Warehouse Cost Line must be unique !')
    ]
    
    @api.depends("company_id")
    def _compute_currency(self):
        for rec in self:
            rec.currency_id = rec.company_id.currency_id
            
            
    def write(self, vals):
        return super(ProductWarehouseCostLine, self).write(vals)
            
            

class ProductWarehouseCostWizard(models.TransientModel):
    _name = 'product.warehouse.cost.wizard'
    _description  = 'Product Warehouse Cost'
    
    
    def default_get(self, fields):
        res = super(ProductWarehouseCostWizard, self).default_get(fields)
        ctx = self._context
        product_warehouse_cost_id = ctx.get('product_warehouse_cost_id', False)
        product_warehouse_cost = self.env['product.warehouse.cost'].browse([product_warehouse_cost_id])
        prod_wh_cost_lines = []
        if product_warehouse_cost:
            for line in product_warehouse_cost.product_cost_line_ids:
                prod_wh_cost_lines.append((0,0,{'warehouse_id': line.warehouse_id.id, 'cost': line.cost}))

                res['product_id'] = product_warehouse_cost.product_id.id
                res['product_cost_line_ids'] = prod_wh_cost_lines
        return res
    

    product_id = fields.Many2one('product.product','Product', readonly=True)
    product_cost_line_ids = fields.One2many('product.warehouse.cost.wizard.line', 'prod_wh_cost_id', 'Warehouse Cost Lines', readonly=True)
    company_id = fields.Many2one('res.company')
    
    

class ProductWarehouseCostWizardLine(models.TransientModel):
    _name = 'product.warehouse.cost.wizard.line'
    _description  = 'Product Warehouse Cost'
    
    def _default_company(self):
        return self.env.company

    
    prod_wh_cost_id = fields.Many2one('product.warehouse.cost.wizard','Product Warehouse Cost', readonly=True)
    warehouse_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    cost = fields.Monetary('Cost Price',
        currency_field="currency_id", readonly=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=_default_company,
        readonly=True,
    )
    currency_id = fields.Many2one(
        "res.currency",
        compute="_compute_currency",
        readonly=True,
    )
    
    @api.depends("company_id")
    def _compute_currency(self):
        for rec in self:
            rec.currency_id = rec.company_id.currency_id