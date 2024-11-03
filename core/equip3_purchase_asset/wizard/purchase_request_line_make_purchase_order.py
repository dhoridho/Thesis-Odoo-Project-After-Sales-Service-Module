
from odoo import api, fields, models, SUPERUSER_ID, tools, _


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"
    
    @api.onchange('supplier_id')
    def _onchange_supplier(self):
        domain = self._default_domain_purchase_order()
        return {'domain': {'purchase_order_id': domain}}

    @api.model
    def _default_domain_purchase_order(self):
        domain = []
        is_good_services_order = self.env['ir.config_parameter'].sudo().get_param('is_good_services_order', False)
        # is_good_services_order = self.env.company.is_good_services_order
        if self._context.get('active_model') == "purchase.request.line":
            pr_line_ids = self.env['purchase.request.line'].browse(self.env.context.get('active_ids'))
            pr_line_id = pr_line_ids and pr_line_ids[0] or False
        else:
            pr_line_ids = self.env['purchase.request'].browse(self.env.context.get('active_ids'))
            pr_line_id = pr_line_ids and pr_line_ids[0] or False
        if pr_line_id and pr_line_id.is_goods_orders and is_good_services_order:
            domain.extend([(
                'is_goods_orders', '=', True
            ),('branch_id','in',pr_line_ids.branch_id.ids)])
        elif pr_line_id and pr_line_id.is_services_orders and is_good_services_order:
            domain.extend([(
                'is_services_orders', '=', True
            ),('branch_id','in',pr_line_ids.branch_id.ids)])
        elif pr_line_id and pr_line_id.is_assets_orders and is_good_services_order:
            domain.extend([(
                'is_assets_orders', '=', True,
            ),('branch_id','in',pr_line_ids.branch_id.ids)])
        domain.extend([(
            'state', '=', 'draft'
        ), ('dp', '=', False)])
        return domain

    purchase_order_id = fields.Many2one(domain=_default_domain_purchase_order)
