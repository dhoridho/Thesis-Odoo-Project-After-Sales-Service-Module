
from odoo import api, fields, models, _

class ProductTemplate(models.Model):
    _inherit = "product.template"
    
    
    invoice_rental_count = fields.Integer(compute='_compute_invoice_rental_count')
    return_of_assets_count = fields.Integer(compute='_compute_return_of_assets_count')
    company_id = fields.Many2one(comodel_name='res.company', readonly=False, check_company=False)
    
    
    @api.onchange('rent_ok','asset_entry_perqty')
    def _rentak_onchange_rent_ok(self):
        for data in self:
            if data.rent_ok:
                data.asset_entry_perqty = True
            if not data.asset_entry_perqty and data.rent_ok:
                data.rent_ok = False
            
    
    def action_view_invoice_rental(self):
        views = [(self.env.ref('equip3_rental_operation.account_move_line_tree_rental').id,'tree')]
        product = self.env['product.product'].sudo().search([('product_tmpl_id','=',self.id)]).ids
        return {
                'type': 'ir.actions.act_window',
                'name': 'Invoice',
                'res_model': 'account.move.line',
                'view_mode': 'tree',
                'views':views,
                'domain': [('product_id', 'in', product),('move_id.is_invoice_from_rental','=',True),('exclude_from_invoice_tab','=',False)],
                'help':"""<p class="o_view_nocontent_smiling_face">Create Invoices.</p>
            """
            }
        
    def action_view_return_of_assets(self):
        # views = [(self.env.ref('equip3_rental_operation.account_move_line_tree_rental').id,'tree')]
        # product = self.env['product.product'].sudo().search([('product_tmpl_id','=',self.id)]).ids
        return {
                'type': 'ir.actions.act_window',
                'name': 'Return Of Assets',
                'res_model': 'return.of.assets',
                'view_mode': 'tree,pivot',
                # 'views':views,
                'domain': [('product_template_id', '=', self.id)],
                'help':"""<p class="o_view_nocontent_smiling_face">Create Return Of Assets.</p>
            """
            }
    
    @api.depends('rent_ok')
    def _compute_invoice_rental_count(self):
        product = self.env['product.product'].sudo().search([('product_tmpl_id','=',self.id)]).ids
        invoice_count = self.env['account.move.line'].sudo().search_count([('product_id', 'in', product),('move_id.is_invoice_from_rental','=',True),('exclude_from_invoice_tab','=',False)])
        self.invoice_rental_count = invoice_count
        
    @api.depends('rent_ok','type')
    def _compute_return_of_assets_count(self):
        assets_count = self.env['return.of.assets'].sudo().search_count([('product_template_id','=',self.id)])
        self.return_of_assets_count = assets_count
    
    

    @api.model
    def action_delete_menu_rental(self):
        try:
            menu_rental_product = self.env.ref('browseinfo_rental_management.menu_rental_product')
        except ValueError:
            menu_rental_product = False
        try:
            menu_rental_orders = self.env.ref('browseinfo_rental_management.menu_rental_orders')
        except ValueError:
            menu_rental_orders = False
        try:
            menu_rental = self.env.ref('browseinfo_rental_management.menu_rental')
        except ValueError:
            menu_rental = False
        if menu_rental_product:
            menu_rental_product.active = False
        if menu_rental_orders:
            menu_rental_orders.active = False
        if menu_rental:
            menu_rental.active = False
