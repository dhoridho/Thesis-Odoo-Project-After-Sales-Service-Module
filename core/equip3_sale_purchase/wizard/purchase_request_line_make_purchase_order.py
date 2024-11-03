from odoo import models,fields,api,_
from odoo.exceptions import UserError
from datetime import datetime

class DirectPurchase(models.Model):
    _inherit = 'purchase.order'

    branch_ids = fields.Many2many('res.branch',string="Allowed Branch")
# class PRLMakePO(models.TransientModel):
#     _inherit = 'purchase.request.line.make.purchase.order'
#
#     pr_id = fields.Many2one(comodel_name='purchase.request', string='PR')
    # OVERRIDE
    # Tujuan = meneruskan field is dropship, customer, customer location dari PR ke PO
    # Mungkin gak jalan atau ketimpa ketika install equip3_construction_purchase_operation
    # def mod_make_purchase_order(self):
    #     res = []
    #     if self.supplier_ids:
    #         for supplier in self.supplier_ids:
    #             self.supplier_id = supplier
    #             purchase_obj = self.env["purchase.order"]
    #             po_line_obj = self.env["purchase.order.line"]
    #             pr_line_obj = self.env["purchase.request.line"]
    #             purchase = False
    #             context = dict(self.env.context) or {}
    #             pr_id = self.pr_id
    #             if pr_id.is_dropship:
    #                 del context['assets_orders']
    #             IrConfigParam = self.env['ir.config_parameter'].sudo()
    #             purchase_request_ids = False
    #             if context.get('active_model') == "purchase.request.line":
    #                 purchase_order_id = self.env[context.get('active_model')].browse(context.get('active_ids'))
    #                 purchase_request_ids = purchase_order_id
    #                 is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
    #                 if is_good_services_order:
    #                     if all(line.is_goods_orders for line in purchase_order_id):
    #                         context.update({'is_goods_orders': True, 'goods_order': True, 'default_is_goods_orders': True})
    #                     elif all(line.is_services_orders for line in purchase_order_id):
    #                         context.update({'is_services_orders': True, 'services_good': True, 'default_is_services_orders': True})
    #                     if purchase_order_id and 'is_assets_orders' in purchase_order_id[0]._fields and \
    #                         all(line.is_assets_orders for line in purchase_order_id):
    #                         context.update({'is_assets_orders': True, 'assets_orders': True, 'default_is_assets_orders': True})
    #                     if purchase_order_id and 'is_rental_orders' in purchase_order_id[0]._fields and \
    #                         all(line.is_rental_orders for line in purchase_order_id):
    #                         context.update({'is_rental_orders': True, 'rentals_orders': True, 'default_is_rental_orders': True})
    #                 for line in purchase_order_id:
    #                     if not line.assigned_to:
    #                         line.assigned_to = self.env.user.id
    #             pr_qty_limit = IrConfigParam.get_param('pr_qty_limit', "no_limit")
    #             max_percentage = int(IrConfigParam.get_param('max_percentage', 0))
    #
    #             recs = {}
    #             for item in self.item_ids:
    #                 branch_ids = []
    #                 branch_ids.append(item.line_id.branch_id.id)
    #                 if self.pr_id.is_single_request_date:
    #                     product_id = item.product_id.id
    #                     if product_id in recs:
    #                         recs[product_id]['product_qty'] += item.product_qty
    #                         recs[product_id]['rem_qty'] += item.rem_qty
    #                     else:
    #                         recs[product_id] = {}
    #                         recs[product_id]['product_qty'] = item.product_qty
    #                         recs[product_id]['rem_qty'] = item.rem_qty
    #
    #             tmp_recs = {}
    #             item_ids = []
    #             for item in self.item_ids:
    #                 if self.pr_id.is_single_request_date:
    #                     product_id = item.product_id.id
    #                     if product_id in tmp_recs:
    #                         continue
    #                     else:
    #                         tmp_recs[product_id] = True
    #                         item.product_qty = recs[product_id]['product_qty']
    #                         item.rem_qty = recs[product_id]['rem_qty']
    #                 else:
    #                     if item.id not in item_ids:
    #                         res_item = self.item_ids.filtered(lambda x: x.product_id.id == item.product_id.id and x.line_id.date_required == item.line_id.date_required)
    #                         for i in res_item:
    #                             if item.id != i.id:
    #                                 item.product_qty += i.product_qty
    #                                 item.rem_qty += i.product_qty
    #                             item_ids.append(i.id)
    #                     else:
    #                         continue
    #                 filtered_product_ids = False
    #                 if item.product_qty <= 0:
    #                     continue
    #                 if pr_qty_limit == 'percent':
    #                     percentage_qty = item.line_id.product_qty + ((item.line_id.product_qty * max_percentage) / 100)
    #                     calculate_qty = percentage_qty - (item.line_id.purchased_qty + item.line_id.tender_qty)
    #                     if item.product_qty > calculate_qty:
    #                         raise UserError(_("Quantity to Purchase for %s cannot request greater than %d") % (item.product_id.display_name, calculate_qty))
    #                 elif pr_qty_limit == 'fix':
    #                     calculate_qty = item.line_id.product_qty - (item.line_id.purchased_qty + item.line_id.tender_qty)
    #                     if item.product_qty > calculate_qty:
    #                         raise UserError(_("Quantity to Purchase for %s cannot request greater than %d") % (item.product_id.display_name, calculate_qty))
    #                 line = item.line_id
    #                 if self.purchase_order_id:
    #                     purchase = self.purchase_order_id
    #                     pr_id = self.pr_id
    #                     if pr_id.is_dropship:
    #                         is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
    #                         if is_good_services_order:
    #                             if all(line.is_goods_orders for line in pr_id.line_ids):
    #                                 context.update({'is_goods_orders': True, 'goods_order': True, 'default_is_goods_orders': True})
    #                             elif all(line.is_services_orders for line in pr_id.line_ids):
    #                                 context.update({'is_services_orders': True, 'services_good': True, 'default_is_services_orders': True})
    #                             if pr_id.line_ids and 'is_assets_orders' in pr_id.line_ids[0]._fields and \
    #                                 all(line.is_assets_orders for line in pr_id.line_ids):
    #                                 context.update({'is_assets_orders': True, 'assets_orders': True, 'default_is_assets_orders': True})
    #                             if pr_id.line_ids and 'is_rental_orders' in pr_id.line_ids[0]._fields and \
    #                                 all(line.is_rental_orders for line in pr_id.line_ids):
    #                                 context.update({'is_rental_orders': True, 'rentals_orders': True, 'default_is_rental_orders': True})
    #                         purchase.update({
    #                             'customer_partner_id':pr_id.customer_partner_id.id,
    #                             'customer_location_partner_id':pr_id.customer_location_partner_id.id,
    #                             'is_dropship':pr_id.is_dropship,
    #                             'sh_sale_order_id':pr_id.so_id.id,
    #                             'is_single_delivery_destination':True,
    #                         })
    #                         for branch in branch_ids:
    #                             purchase.branch_ids [(4, branch)]
    #                     purchase._onchange_partner_invoice_id()
    #                     filtered_product_ids = purchase.order_line.filtered(lambda m: m.product_id.id == item.product_id.id and m.destination_warehouse_id.id == item.line_id.dest_loc_id.id)
    #                     purchase.analytic_account_group_ids = [(4, analytic) for analytic in line.request_id.analytic_account_group_ids.ids]
    #                     for filter_product in filtered_product_ids:
    #                         filter_product.product_qty += item.product_qty
    #                 if not purchase:
    #                     po_data = self._prepare_purchase_order(
    #                         line.request_id.picking_type_id,
    #                         line.request_id.group_id,
    #                         line.company_id,
    #                         line.origin,
    #                     )
    #                     pr_id = self.pr_id
    #                     if pr_id.is_dropship:
    #                         is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
    #                         if is_good_services_order:
    #                             if all(line.is_goods_orders for line in pr_id.line_ids):
    #                                 context.update({'is_goods_orders': True, 'goods_order': True, 'default_is_goods_orders': True})
    #                             elif all(line.is_services_orders for line in pr_id.line_ids):
    #                                 context.update({'is_services_orders': True, 'services_good': True, 'default_is_services_orders': True})
    #                             if pr_id.line_ids and 'is_assets_orders' in pr_id.line_ids[0]._fields and \
    #                                 all(line.is_assets_orders for line in pr_id.line_ids):
    #                                 context.update({'is_assets_orders': True, 'assets_orders': True, 'default_is_assets_orders': True})
    #                             if pr_id.line_ids and 'is_rental_orders' in pr_id.line_ids[0]._fields and \
    #                                 all(line.is_rental_orders for line in pr_id.line_ids):
    #                                 context.update({'is_rental_orders': True, 'rentals_orders': True, 'default_is_rental_orders': True})
    #                         po_data['customer_partner_id'] = pr_id.customer_partner_id.id
    #                         po_data['customer_location_partner_id'] = pr_id.customer_location_partner_id.id
    #                         po_data['is_dropship'] = pr_id.is_dropship
    #                         po_data['sh_sale_order_id'] = pr_id.so_id.id
    #                         po_data['is_single_delivery_destination'] = True
    #                     po_data['from_purchase_request'] = True
    #                     purchase = purchase_obj.with_context(context).create(po_data)
    #                     purchase.branch_ids = [(6, 0, branch_ids)]
    #                     purchase.branch_ids = [(4, purchase.branch_id.id)]
    #                     purchase._onchange_partner_invoice_id()
    #                 # Look for any other PO line in the selected PO with same
    #                 # product and UoM to sum quantities instead of creating a new
    #                 # po line
    #                 domain = self._get_order_line_search_domain(purchase, item)
    #                 available_po_lines = po_line_obj.search(domain)
    #                 new_pr_line = True
    #                 # If Unit of Measure is not set, update from wizard.
    #                 if not line.product_uom_id:
    #                     line.product_uom_id = item.product_uom_id
    #                 # Allocation UoM has to be the same as PR line UoM
    #                 alloc_uom = line.product_uom_id
    #                 wizard_uom = item.product_uom_id
    #                 if available_po_lines and not item.keep_description:
    #                     new_pr_line = False
    #                     po_line = available_po_lines[0]
    #                     po_line.purchase_request_lines = [(4, line.id)]
    #                     po_line.move_dest_ids |= line.move_dest_ids
    #                     if not filtered_product_ids:
    #                         po_line_product_uom_qty = po_line.product_uom._compute_quantity(
    #                             po_line.product_uom_qty, alloc_uom
    #                         )
    #                         wizard_product_uom_qty = wizard_uom._compute_quantity(
    #                             item.product_qty, alloc_uom
    #                         )
    #                         all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
    #                         self.create_allocation(po_line, line, all_qty, alloc_uom)
    #                     else:
    #                         all_qty = po_line.product_qty
    #                 else:
    #                     po_line_data = self._prepare_purchase_order_line(purchase, item)
    #                     if item.keep_description:
    #                         po_line_data["name"] = item.name
    #                     if not filtered_product_ids:
    #                         purchase_line = po_line_obj.create(po_line_data)
    #                     else:
    #                         purchase_line = po_line_obj
    #                     po_line = purchase_line
    #
    #                     if not filtered_product_ids:
    #                         po_line_product_uom_qty = po_line.product_uom._compute_quantity(
    #                             po_line.product_uom_qty, alloc_uom
    #                         )
    #                         wizard_product_uom_qty = wizard_uom._compute_quantity(
    #                             item.product_qty, alloc_uom
    #                         )
    #                         all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
    #                         self.create_allocation(po_line, line, all_qty, alloc_uom)
    #                     else:
    #                         all_qty = po_line.product_qty
    #                 new_qty = pr_line_obj._calc_new_qty(
    #                     line, po_line=po_line, new_pr_line=new_pr_line
    #                 )
    #                 if not filtered_product_ids:
    #                     po_line.product_qty = all_qty
    #                     po_line._onchange_quantity()
    #                 # The onchange quantity is altering the scheduled date of the PO
    #                 # lines. We do not want that:
    #                 date_required = item.line_id.date_required
    #                 po_line.date_planned = datetime(
    #                     date_required.year, date_required.month, date_required.day
    #                 )
    #                 res.append(purchase.id)
    #                 computerem = item.rem_qty - item.product_qty
    #
    #             if purchase_request_ids:
    #                 for pur_req_line in purchase_request_ids:
    #                     order_ids = []
    #                     if pur_req_line.purchase_lines:
    #                         for pur_line in pur_req_line.purchase_lines:
    #                             if pur_line.id not in order_ids:
    #                                 order_ids.append(pur_line.id)
    #                     if purchase:
    #                         for pur_line in purchase.order_line:
    #                             if pur_line.id not in order_ids:
    #                                 order_ids.append(pur_line.id)
    #                     if order_ids:
    #                         pur_req_line.purchase_lines = [(6, 0, order_ids)]
    #     else:
    #         raise UserError(_("Enter a supplier."))
    #     if not res:
    #         return False
    #     return {
    #         "domain": [("id", "in", res)],
    #         "name": _("RFQ"),
    #         "view_mode": "tree,form",
    #         "res_model": "purchase.order",
    #         "view_id": False,
    #         "context": context,
    #         "type": "ir.actions.act_window",
    #     }

