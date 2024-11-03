from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class MiningProductionConf(models.Model):
    _name = 'mining.production.conf'
    _description = 'Production Configuration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'operation_id'

    @api.model
    def _default_branch(self):
        default_branch_id = self.env.context.get('default_branch_id', False)
        if default_branch_id:
            return default_branch_id
        return self.env.branch.id if len(self.env.branches) == 1 else False

    @api.model
    def _domain_branch(self):
        return [('id', 'in', self.env.branches.ids)]


    site_id = fields.Many2one('mining.site.control', string='Mining Site', required=True, tracking=True)
    operation_id = fields.Many2one('mining.operations.two', string='Operation', required=True, tracking=True)

    location_id = fields.Many2one('stock.location', string='Location', tracking=True, domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]")
    location_src_id = fields.Many2one('stock.location', string='Source Location', tracking=True, domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]")
    location_dest_id = fields.Many2one('stock.location', string='Destination Location', tracking=True, domain="[('company_id', '=', company_id), ('branch_id', '=', branch_id)]")

    operation_type = fields.Selection(related='operation_id.operation_type_id')
    
    product_ids = fields.Many2many('product.product', 'product_product_mining_conf_product', string='Product', domain="[('mining_product_type', '=', 'product'), ('company_id', '=', company_id)]")
    input_ids = fields.Many2many('product.product', 'product_product_mining_conf_input', string='Input', domain="[('mining_product_type', '=', 'product')]")
    output_ids = fields.Many2many('product.product', 'product_product_mining_conf_output', string='Output', domain="[('mining_product_type', '=', 'product')]")
 
    is_subcontracting = fields.Boolean(string='Is subcontracting')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, readonly=True)
    branch_id = fields.Many2one('res.branch', string='Branch', required=True, default=_default_branch, domain=_domain_branch)
    
    @api.constrains('product_ids', 'input_ids', 'output_ids', 'operation_id')
    def _check_uom(self):
        for record in self:
            operation_id = record.operation_id
            if not operation_id:
                continue
            operation_uom_categ_id = operation_id.uom_id.category_id
            not_match = []
            for product_id in set(record.product_ids | record.input_ids | record.output_ids):
                if product_id.uom_id.category_id != operation_uom_categ_id:
                    not_match += [(product_id.display_name, product_id.uom_id.category_id.display_name)]
            if not_match:
                message = '- ' + '\n- '.join([
                    '%s (%s) have different UoM category with %s (%s)' % (product_name, category_name, operation_id.display_name, operation_uom_categ_id.display_name)
                    for product_name, category_name in not_match
                ])
                raise ValidationError(_(message))
