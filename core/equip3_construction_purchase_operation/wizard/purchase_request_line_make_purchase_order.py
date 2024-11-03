from datetime import datetime
from odoo import _, api, fields, models
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)


class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order"

    project = fields.Many2one('project.project', 'Project')
    cost_sheet = fields.Many2one('job.cost.sheet', string='Cost Sheet')
    project_budget = fields.Many2one('project.budget', string='Project Budget')
    is_orders = fields.Boolean('Is Orders', default=False)

    @api.model
    def get_items(self, request_line_ids):
        request_line_obj = self.env["purchase.request.line"]
        items = []
        request_lines = request_line_obj.browse(request_line_ids).filtered(lambda x: x.purchase_state != 'cancel')
        self._check_valid_request_line(request_line_ids)
        self.check_group(request_lines)
        for line in request_lines:
            items.append([0, 0, self._prepare_item(line)])
        return items

    @api.onchange('supplier_id')
    def get_project_sheet(self):
        for res in self:
            purchase_request = self.env['purchase.request'].browse(self.env.context.get('active_id'))
            res.project = purchase_request.project.id
            res.cost_sheet = purchase_request.cost_sheet.id
            res.project_budget = purchase_request.project_budget.id
            res.is_orders = purchase_request.is_orders

    @api.model
    def _prepare_item(self, line):
        res = super()._prepare_item(line)
        res['date_required'] = line.date_required
        res['dest_loc_id'] = line.dest_loc_id.id
        res['product_qty'] = 0 if line.remaning_qty < 0 else line.remaning_qty
        res['type'] = line.type
        res['project_scope'] = line.project_scope.id
        res['section'] = line.section.id
        res['variable'] = line.variable.id
        res['group_of_product'] = line.group_of_product.id
        res['line_id'] = line.id
        res['request_id'] = line.request_id.id
        res['product_id'] = line.product_id.id
        res['name'] = line.name or line.product_id.name,
        res['product_uom_id'] = line.product_uom_id.id
        res['cs_material_id'] = line.cs_material_id.id
        res['cs_labour_id'] = line.cs_labour_id.id
        res['cs_overhead_id'] = line.cs_overhead_id.id
        res['cs_equipment_id'] = line.cs_equipment_id.id
        res['cs_material_gop_id'] = line.cs_material_gop_id.id
        res['cs_labour_gop_id'] = line.cs_labour_gop_id.id
        res['cs_overhead_gop_id'] = line.cs_overhead_gop_id.id
        res['cs_equipment_gop_id'] = line.cs_equipment_gop_id.id
        res['bd_material_id'] = line.bd_material_id.id
        res['bd_labour_id'] = line.bd_labour_id.id
        res['bd_overhead_id'] = line.bd_overhead_id.id
        res['bd_equipment_id'] = line.bd_equipment_id.id
        res['bd_material_gop_id'] = line.bd_material_gop_id.id
        res['bd_labour_gop_id'] = line.bd_labour_gop_id.id
        res['bd_overhead_gop_id'] = line.bd_overhead_gop_id.id
        res['bd_equipment_gop_id'] = line.bd_equipment_gop_id.id
        res['dest_loc_id'] = line.dest_loc_id.id
        return res

    def _prepare_purchase_order_line(self, po, item):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_purchase_order_line(po, item)
        res['analytic_tag_ids'] = [(6, 0, po.analytic_account_group_ids.ids)]

        budget_price = 0.00
        budget_amount = 0.00
        if item.line_id.type == 'material':
            if item.line_id.bd_material_id:
                budget_price = item.line_id.bd_material_id.amount
                budget_amount = item.line_id.bd_material_id.amt_left
            else:
                budget_price = item.line_id.cs_material_id.price_unit
                budget_amount = item.line_id.cs_material_id.budgeted_amt_left
        elif item.line_id.type == 'labour':
            if item.line_id.bd_labour_id:
                budget_price = item.line_id.bd_labour_id.amount
                budget_amount = item.line_id.bd_labour_id.amt_left
            else:
                budget_price = item.line_id.cs_labour_id.price_unit
                budget_amount = item.line_id.cs_labour_id.budgeted_amt_left
        elif item.line_id.type == 'overhead':
            if item.line_id.bd_overhead_id:
                budget_price = item.line_id.bd_overhead_id.amount
                budget_amount = item.line_id.bd_overhead_id.amt_left
            else:
                budget_price = item.line_id.cs_overhead_id.price_unit
                budget_amount = item.line_id.cs_overhead_id.budgeted_amt_left
        elif item.line_id.type == 'equipment':
            if item.line_id.bd_equipment_id:
                budget_price = item.line_id.bd_equipment_id.amount
                budget_amount = item.line_id.bd_equipment_id.amt_left
            else:
                budget_price = item.line_id.cs_equipment_id.price_unit
                budget_amount = item.line_id.cs_equipment_id.budgeted_amt_left

        res['cs_material_id'] = item.cs_material_id.id
        res['cs_labour_id'] = item.cs_labour_id.id
        res['cs_overhead_id'] = item.cs_overhead_id.id
        res['cs_equipment_id'] = item.cs_equipment_id.id

        res['cs_material_gop_id'] = item.cs_material_gop_id.id
        res['cs_labour_gop_id'] = item.cs_labour_gop_id.id
        res['cs_overhead_gop_id'] = item.cs_overhead_gop_id.id
        res['cs_equipment_gop_id'] = item.cs_equipment_gop_id.id

        res['bd_material_id'] = item.bd_material_id.id
        res['bd_labour_id'] = item.bd_labour_id.id
        res['bd_overhead_id'] = item.bd_overhead_id.id
        res['bd_equipment_id'] = item.bd_equipment_id.id

        res['bd_material_gop_id'] = item.bd_material_gop_id.id
        res['bd_labour_gop_id'] = item.bd_labour_gop_id.id
        res['bd_overhead_gop_id'] = item.bd_overhead_gop_id.id
        res['bd_equipment_gop_id'] = item.bd_equipment_gop_id.id
        
        res['type'] = item.type
        res['project_scope'] = item.project_scope.id
        res['section'] = item.section.id
        res['variable'] = item.variable.id
        res['group_of_product'] = item.group_of_product.id
        res['budget_quantity'] = item.product_qty
        res['price_unit'] = budget_price
        res['budget_unit_price'] = budget_price
        res['remining_budget_amount'] = budget_amount
        # workaround since somehow we can't get the destination warehouse from the purchase request line
        res['destination_warehouse_id'] = item.request_id.project.warehouse_address.id
        res['picking_type_id'] = item.request_id.picking_type_id.id
        return res

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_purchase_order(picking_type, group_id, company, origin)
        context = dict(self.env.context) or {}
        active_model = context.get('active_model')
        request_id = self.env[active_model].browse(context.get('active_ids'))
        res['project'] = request_id.project.id
        res['cost_sheet'] = request_id.cost_sheet.id
        res['project_budget'] = request_id.project_budget.id
        res['is_orders'] = request_id.is_orders
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
            ("destination_warehouse_id", "=", item.line_id.dest_loc_id.id or False)
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

    def _get_product_group(self, item):
        if item.project_scope and item.section:
            group = item.project_scope.name + item.section.name + item.product_id.name
        else:
            group = item.product_id.name
        return group

    def mod_make_purchase_order(self):
        res = []
        rfq = []
        context = dict(self.env.context) or {}
        context['is_new_from_purchase_request'] = True
        if self.supplier_ids:
            for supplier in self.supplier_ids:
                self.supplier_id = supplier
                purchase_obj = self.env["purchase.order"]
                po_line_obj = self.env["purchase.order.line"]
                pr_line_obj = self.env["purchase.request.line"]
                purchase = False

                IrConfigParam = self.env['ir.config_parameter'].sudo()
                if context.get('active_model') == "purchase.request.line":
                    purchase_order_id = self.env[context.get('active_model')].browse(context.get('active_ids'))
                    is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
                    if is_good_services_order:
                        if all(line.is_goods_orders for line in purchase_order_id):
                            context.update({'is_goods_orders': True, 'goods_order': True, 'default_is_goods_orders': True})
                        
                        elif all(line.is_services_orders for line in purchase_order_id):
                            context.update({
                                'is_services_orders': True, 
                                'services_good': True, 
                                'default_is_services_orders': True,
                                'is_subcontracting': True, 
                                'services_good': True, 
                                'default_is_subcontracting': True,
                                })

                        if purchase_order_id and 'is_assets_orders' in purchase_order_id[0]._fields and \
                            all(line.is_assets_orders for line in purchase_order_id):
                            context.update({'is_assets_orders': True, 'assets_orders': True, 'default_is_assets_orders': True})
                        
                        if purchase_order_id and 'is_rental_orders' in purchase_order_id[0]._fields and \
                            all(line.is_rental_orders for line in purchase_order_id):
                            context.update({'is_rental_orders': True, 'rentals_orders': True, 'default_is_rental_orders': True})

                    for line in purchase_order_id:
                        if not line.assigned_to:
                            line.assigned_to = self.env.user.id

                if context.get('active_model') == "purchase.request":
                    purchase_request_id = self.env[context.get('active_model')].browse(context.get('active_ids'))
                    is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
                    if is_good_services_order:
                        if all(line.is_goods_orders for line in purchase_request_id):
                            context.update({'is_goods_orders': True, 'goods_order': True, 'default_is_goods_orders': True})

                        if all(line.is_services_orders for line in purchase_request_id):
                            context.update({
                                'is_services_orders': True, 
                                'services_good': True, 
                                'default_is_services_orders': True,
                                'is_subcontracting': True, 
                                'services_good': True, 
                                'default_is_subcontracting': True,
                                })

                        if all(line.is_subcontracting for line in purchase_request_id):
                            context.update({
                                'is_services_orders': True, 
                                'services_good': True, 
                                'default_is_services_orders': True,
                                'is_subcontracting': True, 
                                'services_good': True, 
                                'default_is_subcontracting': True,
                                })

                        if purchase_request_id and 'is_assets_orders' in purchase_request_id[0]._fields and \
                            all(line.is_assets_orders for line in purchase_request_id):
                            context.update({'is_assets_orders': True, 'assets_orders': True, 'default_is_assets_orders': True})
                        
                        if purchase_request_id and 'is_rental_orders' in purchase_request_id[0]._fields and \
                            all(line.is_rental_orders for line in purchase_request_id):
                            context.update({
                                'is_rental_orders': True, 
                                'rentals_orders': True, 
                                'default_is_rental_orders': True,
                                'default_rent_duration': purchase_request_id[0].rent_duration,
                                'default_rent_duration_unit': purchase_request_id[0].rent_duration_unit,
                                })
                    
                pr_qty_limit = IrConfigParam.get_param('pr_qty_limit', "no_limit")
                max_percentage = int(IrConfigParam.get_param('max_percentage', 0))

                recs = {}
                for item in self.item_ids:
                    # product_id = item.product_id.id
                    product_group = self._get_product_group(item)
                    if product_group in recs:
                        recs[product_group]['product_qty'] += item.product_qty
                        recs[product_group]['rem_qty'] += item.rem_qty
                    else:
                        recs[product_group] = {}
                        recs[product_group]['product_qty'] = item.product_qty
                        recs[product_group]['rem_qty'] = item.rem_qty

                tmp_recs = {}
                for item in self.item_ids:
                    # product_id = item.product_id.id
                    product_group = self._get_product_group(item)
                    if product_group in tmp_recs:
                        continue
                    else:
                        tmp_recs[product_group] = True
                        item.product_qty = recs[product_group]['product_qty']
                        item.rem_qty = recs[product_group]['rem_qty']

                    filtered_product_ids = False
                    if item.product_qty <= 0:
                        continue
                    if pr_qty_limit == 'percent':
                        percentage_qty = item.line_id.product_qty + ((item.line_id.product_qty * max_percentage) / 100)
                        calculate_qty = percentage_qty - (item.line_id.purchased_qty + item.line_id.tender_qty)
                        if item.product_qty > calculate_qty:
                            raise UserError(_("Quantity to Purchase for %s cannot request greater than %d") % (item.product_id.display_name, calculate_qty))
                    elif pr_qty_limit == 'fix':
                        calculate_qty = item.line_id.product_qty - (item.line_id.purchased_qty + item.line_id.tender_qty)
                        if item.product_qty > calculate_qty:
                            raise UserError(_("Quantity to Purchase for %s cannot request greater than %d") % (item.product_id.display_name, calculate_qty))
                    line = item.line_id
                    if self.purchase_order_id:
                        purchase = self.purchase_order_id
                        purchase._onchange_partner_invoice_id()
                        filtered_product_ids = purchase.order_line.filtered(lambda m: m.product_id.id == item.product_id.id and m.destination_warehouse_id.id == item.line_id.dest_loc_id.id and m.project_scope.id == item.project_scope.id and m.section.id == item.section.id)
                        purchase.analytic_account_group_ids = [(4, analytic) for analytic in line.request_id.analytic_account_group_ids.ids]
                        for filter_product in filtered_product_ids:
                            filter_product.product_qty += item.product_qty
                    if not purchase:
                        pr_id = self.pr_id or self.env['purchase.request.line'].browse(
                            self.env.context['active_ids']).request_id
                        origins = []
                        picking_type_id = False
                        group_id = False
                        company_id = False
                        is_single_request_date = False
                        request_date = False
                        for pr in pr_id:
                            picking_type_id = pr.picking_type_id
                            group_id = pr.group_id
                            company_id = pr.company_id
                            origins.append(pr.origin or '')
                            is_single_request_date = pr.is_single_request_date
                            if not request_date:
                                request_date = pr.request_date
                            else:
                                if request_date < pr.request_date:
                                    request_date = pr.request_date
                        po_data = self._prepare_purchase_order(
                            line.request_id.picking_type_id,
                            line.request_id.group_id,
                            line.company_id,
                            line.origin,
                        )
                        po_data['from_purchase_request'] = True
                        po_data['partner_id'] = supplier.id
                        po_data['is_delivery_receipt'] = is_single_request_date
                        po_data['is_single_delivery_destination'] = True
                        po_data['date_planned'] = request_date
                        purchase = purchase_obj.with_context(context).create(po_data)
                        purchase._onchange_partner_invoice_id()

                    # Look for any other PO line in the selected PO with same
                    # product and UoM to sum quantities instead of creating a new
                    # po line
                    domain = self._get_order_line_search_domain(purchase, item)
                    available_po_lines = po_line_obj.search(domain)
                    new_pr_line = True
                    # If Unit of Measure is not set, update from wizard.
                    if not line.product_uom_id:
                        line.product_uom_id = item.product_uom_id
                    # Allocation UoM has to be the same as PR line UoM
                    alloc_uom = line.product_uom_id
                    wizard_uom = item.product_uom_id
                    if available_po_lines and not item.keep_description:
                        new_pr_line = False
                        po_line = available_po_lines[0]
                        po_line.purchase_request_lines = [(4, line.id)]
                        po_line.move_dest_ids |= line.move_dest_ids
                        if not filtered_product_ids:
                            po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                                po_line.product_uom_qty, alloc_uom
                            )
                            wizard_product_uom_qty = wizard_uom._compute_quantity(
                                item.product_qty, alloc_uom
                            )
                            all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                            self.create_allocation(po_line, line, all_qty, alloc_uom)
                        else:
                            all_qty = po_line.product_qty
                    else:
                        po_line_data = self._prepare_purchase_order_line(purchase, item)
                        if item.keep_description:
                            po_line_data["name"] = item.name
                        if not filtered_product_ids:
                            purchase_line = po_line_obj.create(po_line_data)
                        else:
                            purchase_line = po_line_obj
                        po_line = purchase_line

                        if not filtered_product_ids:
                            po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                                po_line.product_uom_qty, alloc_uom
                            )
                            wizard_product_uom_qty = wizard_uom._compute_quantity(
                                item.product_qty, alloc_uom
                            )
                            all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                            self.create_allocation(po_line, line, all_qty, alloc_uom)
                        else:
                            all_qty = po_line.product_qty
                    new_qty = pr_line_obj._calc_new_qty(
                        line, po_line=po_line, new_pr_line=new_pr_line
                    )
                    if not filtered_product_ids:
                        po_line.product_qty = all_qty
                        po_line._onchange_quantity()
                    # The onchange quantity is altering the scheduled date of the PO
                    # lines. We do not want that:
                    date_required = item.line_id.date_required
                    po_line.date_planned = datetime(
                        date_required.year, date_required.month, date_required.day
                    )
                    res.append(purchase.id)
                    rfq.append(purchase)
                    # purchase._get_gop_budget_line()
                    computerem = item.rem_qty - item.product_qty
                    # for line in purchase.order_line:
                    #     line._onchange_product()

                if self.purchase_order_id:
                    for pur_req_line in self.purchase_order_id:
                        order_ids = []
                        if pur_req_line.purchase_lines:
                            for pur_line in pur_req_line.purchase_lines:
                                if pur_line.id not in order_ids:
                                    order_ids.append(pur_line.id)
                        if purchase:
                            for pur_line in purchase.order_line:
                                if pur_line.id not in order_ids:
                                    order_ids.append(pur_line.id)
                        if order_ids:
                            pur_req_line.purchase_lines = [(6, 0, order_ids)]
        else:
            raise UserError(_("Enter a supplier."))
        if not res:
            return False
        for purchase in rfq:
            for line in purchase.order_line:
                line._compute_default_unit_price_budget(is_new_from_purchase_request=True)
                line.destination_warehouse_id = purchase.project.warehouse_address
            purchase.destination_warehouse_id = purchase.project.warehouse_address
        return {
            "domain": [("id", "in", res)],
            "name": _("RFQ"),
            "view_mode": "tree,form",
            "res_model": "purchase.order",
            "view_id": False,
            "context": context,
            "type": "ir.actions.act_window",
        }
    
    
    # def mod_make_purchase_order(self):
    #     res = []
    #     if self.supplier_ids:
    #         for supplier in self.supplier_ids:
    #             self.supplier_id = supplier
    #         purchase_obj = self.env["purchase.order"]
    #         po_line_obj = self.env["purchase.order.line"]
    #         pr_line_obj = self.env["purchase.request.line"]
    #         purchase = False
    #         context = dict(self.env.context) or {}
    #         IrConfigParam = self.env['ir.config_parameter'].sudo()
    #         if context.get('active_model') == "purchase.request.line":
    #             purchase_order_id = self.env[context.get('active_model')].browse(context.get('active_ids'))
    #             is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
    #             if is_good_services_order:
    #                 if all(line.is_goods_orders for line in purchase_order_id):
    #                     context.update({'is_goods_orders': True, 'goods_order': True, 'default_is_goods_orders': True})
    #                 elif all(line.is_services_orders for line in purchase_order_id):
    #                     context.update({'is_services_orders': True, 'services_good': True, 'default_is_services_orders': True})
    #                 if purchase_order_id and 'is_assets_orders' in purchase_order_id[0]._fields and \
    #                     all(line.is_assets_orders for line in purchase_order_id):
    #                     context.update({'is_assets_orders': True, 'assets_orders': True, 'default_is_assets_orders': True})
    #                 if purchase_order_id and 'is_rental_orders' in purchase_order_id[0]._fields and \
    #                     all(line.is_rental_orders for line in purchase_order_id):
    #                     context.update({'is_rental_orders': True, 'rentals_orders': True, 'default_is_rental_orders': True})
    #             for line in purchase_order_id:
    #                 if not line.assigned_to:
    #                     line.assigned_to = self.env.user.id
    #         pr_qty_limit = IrConfigParam.get_param('pr_qty_limit', "no_limit")
    #         max_percentage = int(IrConfigParam.get_param('max_percentage', 0))

    #         recs = {}
    #         for item in self.item_ids:
    #             # product_id = item.product_id.id
    #             product_group = self._get_product_group(item)
    #             if product_group in recs:
    #                 recs[product_group]['product_qty'] += item.product_qty
    #                 recs[product_group]['rem_qty'] += item.rem_qty
    #             else:
    #                 recs[product_group] = {}
    #                 recs[product_group]['product_qty'] = item.product_qty
    #                 recs[product_group]['rem_qty'] = item.rem_qty

    #         tmp_recs = {}
    #         for item in self.item_ids:
    #             # product_id = item.product_id.id
    #             product_group = self._get_product_group(item)
    #             if product_group in tmp_recs:
    #                 continue
    #             else:
    #                 tmp_recs[product_group] = True
    #                 item.product_qty = recs[product_group]['product_qty']
    #                 item.rem_qty = recs[product_group]['rem_qty']

    #             filtered_product_ids = False
    #             if item.product_qty <= 0:
    #                 continue
    #             if pr_qty_limit == 'percent':
    #                 percentage_qty = item.line_id.product_qty + ((item.line_id.product_qty * max_percentage) / 100)
    #                 calculate_qty = percentage_qty - (item.line_id.purchased_qty + item.line_id.tender_qty)
    #                 if item.product_qty > calculate_qty:
    #                     raise UserError(_("Quantity to Purchase for %s cannot request greater than %d") % (item.product_id.display_name, calculate_qty))
    #             elif pr_qty_limit == 'fix':
    #                 calculate_qty = item.line_id.product_qty - (item.line_id.purchased_qty + item.line_id.tender_qty)
    #                 if item.product_qty > calculate_qty:
    #                     raise UserError(_("Quantity to Purchase for %s cannot request greater than %d") % (item.product_id.display_name, calculate_qty))
    #             line = item.line_id
    #             if self.purchase_order_id:
    #                 purchase = self.purchase_order_id
    #                 purchase._onchange_partner_invoice_id()
    #                 filtered_product_ids = purchase.order_line.filtered(lambda m: m.product_id.id == item.product_id.id and m.destination_warehouse_id.id == item.line_id.dest_loc_id.id and m.project_scope.id == item.project_scope.id and m.section.id == item.section.id)
    #                 purchase.analytic_account_group_ids = [(4, analytic) for analytic in line.request_id.analytic_account_group_ids.ids]
    #                 for filter_product in filtered_product_ids:
    #                     filter_product.product_qty += item.product_qty
    #             if not purchase:
    #                 po_data = self._prepare_purchase_order(
    #                     line.request_id.picking_type_id,
    #                     line.request_id.group_id,
    #                     line.company_id,
    #                     line.origin,
    #                 )
    #                 purchase = purchase_obj.with_context(context).create(po_data)
    #                 purchase._onchange_partner_invoice_id()
    #             # Look for any other PO line in the selected PO with same
    #             # product and UoM to sum quantities instead of creating a new
    #             # po line
    #             domain = self._get_order_line_search_domain(purchase, item)
    #             available_po_lines = po_line_obj.search(domain)
    #             new_pr_line = True
    #             # If Unit of Measure is not set, update from wizard.
    #             if not line.product_uom_id:
    #                 line.product_uom_id = item.product_uom_id
    #             # Allocation UoM has to be the same as PR line UoM
    #             alloc_uom = line.product_uom_id
    #             wizard_uom = item.product_uom_id
    #             if available_po_lines and not item.keep_description:
    #                 new_pr_line = False
    #                 po_line = available_po_lines[0]
    #                 po_line.purchase_request_lines = [(4, line.id)]
    #                 po_line.move_dest_ids |= line.move_dest_ids
    #                 if not filtered_product_ids:
    #                     po_line_product_uom_qty = po_line.product_uom._compute_quantity(
    #                         po_line.product_uom_qty, alloc_uom
    #                     )
    #                     wizard_product_uom_qty = wizard_uom._compute_quantity(
    #                         item.product_qty, alloc_uom
    #                     )
    #                     all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
    #                     self.create_allocation(po_line, line, all_qty, alloc_uom)
    #                 else:
    #                     all_qty = po_line.product_qty
    #             else:
    #                 po_line_data = self._prepare_purchase_order_line(purchase, item)
    #                 if item.keep_description:
    #                     po_line_data["name"] = item.name
    #                 if not filtered_product_ids:
    #                     purchase_line = po_line_obj.create(po_line_data)
    #                 else:
    #                     purchase_line = po_line_obj
    #                 po_line = purchase_line

    #                 if not filtered_product_ids:
    #                     po_line_product_uom_qty = po_line.product_uom._compute_quantity(
    #                         po_line.product_uom_qty, alloc_uom
    #                     )
    #                     wizard_product_uom_qty = wizard_uom._compute_quantity(
    #                         item.product_qty, alloc_uom
    #                     )
    #                     all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
    #                     self.create_allocation(po_line, line, all_qty, alloc_uom)
    #                 else:
    #                     all_qty = po_line.product_qty
    #             new_qty = pr_line_obj._calc_new_qty(
    #                 line, po_line=po_line, new_pr_line=new_pr_line
    #             )
    #             if not filtered_product_ids:
    #                 po_line.product_qty = all_qty
    #                 po_line._onchange_quantity()
    #             # The onchange quantity is altering the scheduled date of the PO
    #             # lines. We do not want that:
    #             date_required = item.line_id.date_required
    #             po_line.date_planned = datetime(
    #                 date_required.year, date_required.month, date_required.day
    #             )
    #             res.append(purchase.id)
    #             purchase._get_gop_budget_line()
    #             computerem = item.rem_qty - item.product_qty
    #             # for line in purchase.order_line:
    #             #     line._onchange_product()
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

class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order.item"

    project = fields.Many2one(related='wiz_id.project', string='Project')

    # Material
    cs_material_id = fields.Many2one('material.material', string='CS Material ID')
    cs_material_gop_id = fields.Many2one('material.gop.material', string='CS Material GOP ID')
    bd_material_id = fields.Many2one('budget.material', string='BD Material ID')
    bd_material_gop_id = fields.Many2one('budget.gop.material', string='BD Material GOP ID')

    # Labour
    cs_labour_id = fields.Many2one('material.labour', string='CS Labour ID')
    cs_labour_gop_id = fields.Many2one('material.gop.labour', string='CS Labour GOP ID')
    bd_labour_id = fields.Many2one('budget.labour', string='BD Labour ID')
    bd_labour_gop_id = fields.Many2one('budget.gop.labour', string='BD Labour GOP ID')

    # Overhead
    cs_overhead_id = fields.Many2one('material.overhead', string='CS Overhead ID')
    cs_overhead_gop_id = fields.Many2one('material.gop.overhead', string='CS Overhead GOP ID')
    bd_overhead_id = fields.Many2one('budget.overhead', string='BD Overhead ID')
    bd_overhead_gop_id = fields.Many2one('budget.gop.overhead', string='BD Overhead GOP ID')

    # Equipment
    cs_equipment_id = fields.Many2one('material.equipment', string='CS Equipment ID')
    cs_equipment_gop_id = fields.Many2one('material.gop.equipment', string='CS Equipment GOP ID')
    bd_equipment_id = fields.Many2one('budget.equipment', string='BD Equipment ID')
    bd_equipment_gop_id = fields.Many2one('budget.gop.equipment', string='BD Equipment GOP ID')

    type = fields.Selection([('material','Material'),
                            ('labour','Labour'),
                            ('overhead','Overhead'),
                            ('equipment','Equipment')],
                            string = "Type")
    project_scope = fields.Many2one('project.scope.line', string='Project Scope')
    section = fields.Many2one('section.line', string='Section')
    variable = fields.Many2one('variable.template', string='Variable')
    group_of_product = fields.Many2one('group.of.product', string='Group of Product')
  