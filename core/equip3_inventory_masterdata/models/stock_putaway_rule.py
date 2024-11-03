from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError


class StockPutawayRule(models.Model):
    _inherit = "stock.putaway.rule"

    # on_max_capacity = fields.Boolean("Max capacity")
    # is_putaway_max_capacity = fields.Boolean(compute="_compute_is_putaway_max_capacity")
    def _default_product_id(self):
        if self.env.context.get('active_model') == 'product.template' and self.env.context.get('active_id'):
            product_template = self.env['product.template'].browse(self.env.context.get('active_id'))
            product_template = product_template.exists()
            if product_template.product_variant_count == 1:
                return product_template.product_variant_id
        elif self.env.context.get('active_model') == 'product.product':
            return self.env.context.get('active_id')

    def _domain_product_id(self):
        domain = "[('type', '!=', 'service'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]"
        if self.env.context.get('active_model') == 'product.template':
            return [('product_tmpl_id', '=', self.env.context.get('active_id'))]
        return domain

    product_ids = fields.Many2many('product.product','product_putaway_ids','prod_ids','putaway_id', string='Products')
    check_product_ids = fields.Boolean(compute='check_if_product_ids')
    check_category_ids = fields.Boolean(compute='check_if_product_ids')
    category_id = fields.Many2many('product.category', 'product_categ_putaway_rel', 'product_id', 'catag_id', string='Product Category')

    @api.depends('product_ids', 'category_id')
    def check_if_product_ids(self):
        self.check_product_ids = False
        self.check_category_ids = False
        for record in self:
            if record.product_ids:
                record.check_product_ids = True
            if record.category_id:
                record.check_category_ids = True
        # if self.product_ids:
        #     print('First', self.product_ids)
        #     self.check_product_ids = True
        # if self.category_id:
        #     print('Second', self.category_id)
        #     self.check_category_ids = True


    # @api.model
    # def create(self, vals):
    #     res = super(StockPutawayRule, self).create(vals)
    #     if res.location_in_id.capacity_type != "unit":
    #         raise UserError(('The Location Capacity type is not defined.'))
    #     return res

    # def write(self, vals):
    #     res = super(StockPutawayRule, self).write(vals)
    #     if self.location_in_id.capacity_type != "unit":
    #         raise UserError(('The Location Capacity type is not defined.'))
    #     return res

    @api.constrains('product_ids', 'location_in_id', 'location_out_id')
    def check_putaway_rules_product(self):
        for record in self:
            # rule_exists = self.search([('product_ids', '=', self.product_ids.ids), ('location_in_id', '=', self.location_in_id.id), ('location_out_id', '=', self.location_out_id.id)])
            rule_exists = self.search([('location_in_id', '=', self.location_in_id.id), ('location_out_id', '=', self.location_out_id.id)])
            len = 0
            product_dup = []
            for rule in rule_exists:
                if self.location_in_id == rule.location_in_id and self.location_out_id == rule.location_out_id:
                    for product in rule.product_ids:
                        if product in product_dup:
                            raise ValidationError("There’s Putaway Rules with the same condition")
                        else:
                            product_dup.append(product)

    @api.constrains('category_id', 'location_in_id', 'location_out_id')
    def check_putaway_rules_category(self):
        for record in self:
            rule_exists = self.search([('location_in_id', '=', self.location_in_id.id), ('location_out_id', '=', self.location_out_id.id)])
            len = 0
            categ_dup = []
            for rule in rule_exists:
                if self.location_in_id == rule.location_in_id and self.location_out_id == rule.location_out_id:
                    for categ in rule.category_id:
                        if categ in categ_dup:
                            raise ValidationError("There’s Putaway Rules with the same condition")
                        else:
                            categ_dup.append(categ)

    # def _compute_is_putaway_max_capacity(self):
    #     for rec in self:
    #         rec.is_putaway_max_capacity = bool(self.env["ir.config_parameter"].sudo().get_param("putaway_max_capacity", False))

    # @api.model
    # def default_get(self, fields):
    #     res = super(StockPutawayRule, self).default_get(fields)
    #     res.update({ "is_putaway_max_capacity": bool(self.env["ir.config_parameter"].sudo().get_param("putaway_max_capacity", False))})
    #     return res

    # @api.onchange("on_max_capacity")
    # def _onchange_on_max_capacity(self):
    #     if self.on_max_capacity:
    #         self.product_id = False
    #         self.category_id = False
