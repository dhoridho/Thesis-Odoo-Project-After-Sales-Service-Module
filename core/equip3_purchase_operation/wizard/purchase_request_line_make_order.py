# Copyright 2018-2019 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).


from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        res.get("item_ids").reverse()
        return res

    @api.model
    def _check_valid_request_line(self, request_line_ids):
        picking_type = False
        company_id = False

        for line in self.env["purchase.request.line"].browse(request_line_ids):
            if line.request_id.state == "done":
                raise UserError(_("The purchase has already been completed."))
            if line.request_id.state != "purchase_request":
                raise UserError(
                    _("Purchase Request %s is not approved") % line.request_id.name
                )

            if line.purchase_state == "done":
                raise UserError(_("The purchase has already been completed."))

            line_company_id = line.company_id and line.company_id.id or False
            if company_id is not False and line_company_id != company_id:
                raise UserError(_("You have to select lines from the same company."))
            else:
                company_id = line_company_id

            line_picking_type = line.request_id.picking_type_id or False
            if not line_picking_type:
                raise UserError(_("You have to enter a Picking Type."))
            if picking_type is not False and line_picking_type != picking_type:
                raise UserError(
                    _("You have to select lines from the same Picking Type.")
                )
            else:
                picking_type = line_picking_type

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_purchase_order_line(po, item)
        res['is_goods_orders'] = po.is_goods_orders
        res['branch_id'] = item.line_id.branch_id.id
        return res

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_purchase_order(picking_type, group_id, company, origin)
        is_goods_orders = False
        if all(line.line_id.is_goods_orders for line in self.item_ids):
            is_goods_orders = True
        res['is_goods_orders'] = is_goods_orders
        context = dict(self.env.context) or {}
        if context.get('active_model') == 'purchase.request':
            purchase_request_ids = self.env['purchase.request'].browse(context.get("active_ids"))
            purchase_request_ids.write({'purchase_req_state' : 'in_progress'})
            res['analytic_account_group_ids'] = [(6, 0, purchase_request_ids.analytic_account_group_ids.ids)]
        elif context.get('active_model') == 'purchase.request.line':
            purchase_request_line_ids = self.env['purchase.request.line'].browse(context.get("active_ids"))
            purchase_request_line_ids.mapped('request_id').write({'purchase_req_state' : 'in_progress'})
            res['analytic_account_group_ids'] = [(6, 0, purchase_request_line_ids.mapped('request_id.analytic_account_group_ids').ids)]
        return res
