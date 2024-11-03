from odoo import api, fields, models, _
import json

class MonthlyAccountBudget(models.Model):
    _name = "account.product.group"
    _description = 'Group of Product'
    
    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id',False)
        if default_branch_id:
            return default_branch_id
        return self.env.company_branches[0].id if len(self.env.company_branches) == 1 else self.env.user.branch_id.id

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids), ('company_id','=', self.env.company.id)]

    # @api.model
    # def _get_selected_products(self):
    #     # Retrieve all product IDs that have been selected in any product group
    #     self.env.cr.execute("""
    #         SELECT group_id
    #         FROM product_group_rel
    #     """)
    #     return [row[0] for row in self.env.cr.fetchall()]

    # def _get_available_products_domain(self):
    #     # Compute the domain to exclude already selected products
    #     selected_product_ids = self._get_selected_products()
    #     return [('id', 'not in', selected_product_ids)]
    
    name = fields.Char(string="Name", required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.company)
    branch_id = fields.Many2one('res.branch', check_company=True, domain=_domain_branch, default = _default_branch, readonly=False, required=True, string='Branch')
    product_ids = fields.Many2many('product.product', 'product_group_rel', 'group_id', 'product_id', string="Products")
    product_categ_id = fields.Many2one('product.category', 'Product Category')
    product_ids_domain = fields.Char(string='Products Domain', compute='_compute_product_ids_domain')
    # product_ids = fields.Many2many('product.product', 'product_group_rel', 'product_id', 'group_id', string="Products")

    @api.depends('product_categ_id')
    def _compute_product_ids_domain(self):
        for rec in self:
            if rec.product_categ_id:
                rec.product_ids_domain = json.dumps([('categ_id','=', rec.product_categ_id.id)])
            else:
                rec.product_ids_domain = json.dumps([])

    @api.onchange('product_categ_id')
    def item_delivered_ids_onchange(self):
        for rec in self:
            if rec.product_categ_id:
                return {'domain': {'product_ids': [('categ_id','=', self.product_categ_id.id)]}}
            else:
                return {'domain': {'product_ids': []}}
        

    @api.model
    def create(self, vals):
        # Create the group record
        group = super(MonthlyAccountBudget, self).create(vals)
        if vals.get('product_ids'):
            self._update_product_template_group(vals['product_ids'][0][2], group.id)
        return group

    def write(self, vals):
        # Determine changes in product_ids before updating the group
        if 'product_ids' in vals:
            if len(vals['product_ids'][0]) > 2:
                current_product_ids = self.product_ids.ids
                new_product_ids = vals['product_ids'][0][2]
                added_products = set(new_product_ids) - set(current_product_ids)
                removed_products = set(current_product_ids) - set(new_product_ids)
                result = super(MonthlyAccountBudget, self).write(vals)
                if added_products:
                    self._update_product_template_group(added_products, self.id)
                if removed_products:
                    self._update_product_template_group(removed_products, False)
                return result

        return super(MonthlyAccountBudget, self).write(vals)

    def _update_product_template_group(self, product_ids, group_id):
        # Find product.template records related to the given product.product IDs
        products = self.env['product.product'].browse(product_ids)
        for product in products:
            # Assuming there is a field named 'group_product' in product.template
            product.product_tmpl_id.write({'group_product': group_id})


    @api.onchange('product_ids')
    def _onchange_product_ids(self):
        selected_product_ids = self._get_selected_products()
        return {
            'domain': {'product_ids': [('id', 'not in', selected_product_ids)]}
        }

    @api.model
    def _get_selected_products(self):
        self.env.cr.execute("""
            SELECT product_id
            FROM product_group_rel
        """)
        selected_ids = [row[0] for row in self.env.cr.fetchall()]
        # Exclude current record's product_id to allow saving
        if self.id:
            self.env.cr.execute("""
                SELECT product_id
                FROM product_group_rel
                WHERE group_id != %s
            """, (self.id,))
            selected_ids = [row[0] for row in self.env.cr.fetchall()]
        return selected_ids

    # def crete(self):
    #     product_ids = self.env('product.template').search([('id', 'in', product_id.ids)])
    #     group_product = self.env('product.template').search([('id', 'in', product_id.ids)])

class ProductTemplate(models.Model):
    _inherit = 'product.template' 


    def _get_group_product(self):
        # Retrieve the first group that contains the current product
        group = self.env['account.product.group'].search([('product_ids', 'in', self.id)], limit=1)
        return group.id if group else False
    
    group_product = fields.Many2one('account.product.group', string='Account Group of Product', default=_get_group_product)
    is_use_purchase_budget = fields.Boolean('Is Use Purchase Budget')
    is_allow_purchase_budget = fields.Boolean(string="Allow Purchase Budget", compute="_compute_is_allow_purchase_budget")

    def _get_group_product(self):
        # Retrieve the first group that contains the current product
        group = self.env['account.product.group'].search([('product_ids', 'in', self.id)], limit=1)
        return group.id if group else False

    def write(self, vals):
        if 'group_product' in vals:
            if vals['group_product']:
                self.env['account.product.group'].browse(vals['group_product']).product_ids = [(4, self.product_variant_id.id)]
            elif not vals['group_product']:
                self.group_product.product_ids = [(3, self.product_variant_id.id)]

        return super(ProductTemplate, self).write(vals)

    def _compute_is_allow_purchase_budget(self):
        for record in self:
            IrConfigParam = self.env['ir.config_parameter'].sudo()
            record.is_allow_purchase_budget = IrConfigParam.get_param('is_allow_purchase_budget', False)

    # @api.depends('product_id')  # Assuming 'product_id' is a field that links to the actual product in ProductTemplate
    # def _compute_group_product(self):
    #     for record in self:
    #         # Initialize the group_product as False in case no group is found
    #         record.group_product = False
    #         # Search for a group in account.product.group that contains the current product
    #         group = self.env['account.product.group'].search([('product_ids', 'in', record.id)], limit=1)
    #         if group:
    #             # Assign the found group to the group_product field
    #             record.group_product = group.id
    



    