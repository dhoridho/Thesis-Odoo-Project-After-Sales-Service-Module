from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductProduct(models.Model):
    _inherit = 'product.product'

    active_bom_ids = fields.One2many('mrp.bom', compute='_compute_boms')
    has_bom = fields.Boolean(compute='_compute_boms', search='_search_has_bom')

    def _compute_boms(self):
        company_id = self.env.context.get('company_id', self.env.company.id)
        branch_id = self.env.context.get('branch_id', self.env.branch.id)
        bom_type = self.env.context.get('equip_bom_type', 'mrp')
        include_draft = self.env.context.get('include_draft', False)

        for product in self:
            boms = (product.variant_bom_ids | product.bom_ids).filtered(lambda o: 
                o.company_id in (company_id, False) and 
                o.branch_id in (branch_id, False) and 
                o.equip_bom_type == bom_type and
                o.bom_type == 'normal')
            
            active_boms = boms.filtered(lambda o: o.state == 'confirm')

            if not include_draft:
                boms = active_boms
            
            product.active_bom_ids = [(6, 0, boms.ids)]
            product.has_bom = len(boms) > 0

    def _search_has_bom(self, operator, value):
        if operator not in ('=', '!=') or value not in (True, False):
            raise ValidationError(_('Operator/value not supported!'))
        
        company_id = self.env.context.get('company_id', self.env.company.id)
        branch_id = self.env.context.get('branch_id', self.env.branch.id)
        bom_type = self.env.context.get('equip_bom_type', 'mrp')
        include_draft = self.env.context.get('include_draft', False)

        bom_domain = [
            '|', ('company_id', '=', company_id), ('company_id', '=', False),
            '|', ('branch_id', '=', branch_id), ('branch_id', '=', False),
            ('equip_bom_type', '=', bom_type),
            ('bom_type', '=', 'normal')
        ]
        if not include_draft:
            bom_domain += [('state', '=', 'confirm')]
        
        boms = self.env['mrp.bom'].search(bom_domain, order='sequence, product_id')
        product_ids = (boms.mapped('product_id') | boms.mapped('product_tmpl_id').product_variant_ids).ids
        if (operator == '=' and value is True) or (operator == '!=' and value is False):
            print()
            print('CASE 1', [('id', 'in', product_ids)])
            print()
            return [('id', 'in', product_ids)]

        print()
        print('CASE 2', [('id', 'not in', product_ids)])
        print()
        return [('id', 'not in', product_ids)]
