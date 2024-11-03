from datetime import datetime
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    is_engineering = fields.Boolean('Engineering', readonly=True)

    @api.onchange('supplier_id')
    def get_engineering(self):
        for res in self:
            purchase_request = self.env['purchase.request'].browse(self.env.context.get('active_id'))
            res.is_engineering = purchase_request.is_engineering

    @api.model
    def _prepare_item(self, line):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_item(line)
        res['finish_good_id'] = line.finish_good_id.id

        return res

    def _prepare_purchase_order_line(self, po, item):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_purchase_order_line(po, item)
        res['finish_good_id'] = item.line_id.finish_good_id.id
        return res

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_purchase_order(picking_type, group_id, company, origin)
        res['is_engineering'] = self.is_engineering
        return res

    @api.model
    def _get_order_line_search_domain(self, order, item):
        vals = self._prepare_purchase_order_line(order, item)
        name = self._get_purchase_line_name(order, item)
        order_line_data = [
            ("order_id", "=", order.id),
            ("name", "=", name),
            ("product_id", "=", item.product_id.id or False),
            ("product_uom", "=", vals["product_uom"]),
            ("account_analytic_id", "=", item.line_id.analytic_account_id.id or False),
            ("project_scope", "=", item.line_id.project_scope.id or False),
            ("section", "=", item.line_id.section.id or False),
            ("finish_good_id", "=", item.line_id.finish_good_id.id or False),
        ]
        if self.sync_data_planned:
            date_required = item.line_id.date_required
            order_line_data += [
                (
                    "date_planned",
                    "=",
                    datetime(
                        date_required.year, date_required.month, date_required.day
                    ),
                )
            ]
        if not item.product_id:
            order_line_data.append(("name", "=", item.name))
        return order_line_data
    
    # def _get_product_group(self, item):
    #     if item.finish_good_id:
    #         group = item.project_scope.name + item.section.name + item.finish_good_id.name + item.product_id.name
    #     else:
    #         group = item.project_scope.name + item.section.name + item.product_id.name
    #     return group
    
    def _get_product_group(self, item):
        if item.project_scope and item.section and item.finish_good_id:
            group = item.project_scope.name + item.section.name + item.finish_good_id.name + item.product_id.name
        elif item.project_scope and item.section and not item.finish_good_id:
            group = item.project_scope.name + item.section.name + item.product_id.name
        else:
            group = item.product_id.name
        return group

class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order.item"

    is_engineering = fields.Boolean(related='wiz_id.is_engineering')
    finish_good_id = fields.Many2one('product.product', 'Finished Goods')
  