
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError,UserError


class CreatePurchaseRequestDirect(models.TransientModel):
    _name = "create.purchase.request.direct"
    _description = "Create Purchase Request Direct"

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
        domain.extend([(
                    'state', 'in', ('draft', 'sent')
                ), ('dp', '=', True)])
        return domain
    
    @api.model
    def _domain_supplier_ids(self):
        domain = [("is_company", "=", True),("is_vendor","=",True)]
        pr_line_ids =False
        if self._context.get('active_model') == "purchase.request.line":
            pr_line_ids = self.env['purchase.request.line'].browse(self.env.context.get('active_ids'))

        elif self._context.get('active_model') == "purchase.request":
            pr_line_ids = self.env['purchase.request'].browse(self.env.context.get('active_ids'))
        if pr_line_ids:
            if len(pr_line_ids.branch_id.ids) > 1:
                raise ValidationError("Please select purchase request line with the same branch!")
            domain.extend([('branch_id','=',pr_line_ids.branch_id.id)])
        return domain

    @api.model
    def _domain_journal_id(self):
        # domain = [("is_company", "=", True)]
        domain=[("type", "in", ("bank", "cash"))]
        pr_line_ids =False
        if self._context.get('active_model') == "purchase.request.line":
            pr_line_ids = self.env['purchase.request.line'].browse(self.env.context.get('active_ids'))

        elif self._context.get('active_model') == "purchase.request":
            pr_line_ids = self.env['purchase.request'].browse(self.env.context.get('active_ids'))
        if pr_line_ids:
            domain.extend([('branch_id','=',pr_line_ids.branch_id.id)])
        return domain
    

    purchase_order_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Direct Purchase",
        domain=_default_domain_purchase_order,
    )
    sync_data_planned = fields.Boolean(
        string="Merge on PO lines with equal Scheduled Date"
    )
    supplier_id = fields.Many2one(
        comodel_name="res.partner",
        string="Supplier",
        required=True,
        domain=_domain_supplier_ids,
        # domain=[("is_company", "=", True)],
        context={"res_partner_search_mode": "supplier", "default_is_company": True},
    )
    item_ids = fields.One2many(
        comodel_name="create.purchase.request.direct.lines",
        inverse_name="wiz_id",
        string="Items",
    )
    
    journal_id = fields.Many2one('account.journal', string='Journal',domain=_domain_journal_id)

    @api.model
    def _domain_supplier_ids(self):
        domain = [("is_company", "=", True),("is_vendor","=",True)]
        pr_line_ids =False
        if self._context.get('active_model') == "purchase.request.line":
            pr_line_ids = self.env['purchase.request.line'].browse(self.env.context.get('active_ids'))

        elif self._context.get('active_model') == "purchase.request":
            pr_line_ids = self.env['purchase.request'].browse(self.env.context.get('active_ids'))
        if pr_line_ids:
            domain.extend([('branch_id','=',pr_line_ids.branch_id.id)])
        return domain

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        active_model = self.env.context.get("active_model", False)
        request_line_ids = []
        if active_model == "purchase.request.line":
            request_line_ids += self.env.context.get("active_ids", [])
        elif active_model == "purchase.request":
            request_ids = self.env.context.get("active_ids", False)
            request_line_ids += (
                self.env[active_model].browse(request_ids).mapped("line_ids.id")
            )
        if not request_line_ids:
            return res
        res["item_ids"] = self.get_items(request_line_ids)
        request_lines = self.env["purchase.request.line"].browse(request_line_ids)
        supplier_ids = request_lines.mapped("supplier_id").ids
        if len(supplier_ids) == 1:
            res["supplier_id"] = supplier_ids[0]
        return res

    @api.model
    def _prepare_item(self, line):
        return {
            "line_id": line.id,
            "request_id": line.request_id.id,
            "product_id": line.product_id.id,
            "name": line.name or line.product_id.name,
            "product_qty": 0 if line.remaning_qty < 0 else line.remaning_qty,
            "product_uom_id": line.product_uom_id.id,
        }

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
    def check_group(self, request_lines):
        if len(list(set(request_lines.mapped("request_id.group_id")))) > 1:
            raise UserError(
                _(
                    "You cannot create a single purchase order from "
                    "purchase requests that have different procurement group."
                )
            )

    @api.model
    def get_items(self, request_line_ids):
        request_line_obj = self.env["purchase.request.line"]
        items = []
        request_lines = request_line_obj.browse(request_line_ids)
        self._check_valid_request_line(request_line_ids)
        self.check_group(request_lines)
        for line in request_lines:
            items.append([0, 0, self._prepare_item(line)])
        return items

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin, is_single_request_date, request_date, is_single_delivery_destination, destination_warehouse_id, request_id=False, ):
        if not self.supplier_id:
            raise UserError(_("Enter a supplier."))
        context = dict(self.env.context) or {}
        supplier = self.supplier_id
        if destination_warehouse_id:
            destination_warehouse_id = destination_warehouse_id.id
        data = {
            "partner_id": self.supplier_id.id,
            "fiscal_position_id": supplier.property_account_position_id
            and supplier.property_account_position_id.id
            or False,
            "picking_type_id": picking_type.id,
            "company_id": company.id,
            "group_id": group_id.id,
            "dp": True,
            "is_delivery_receipt": is_single_request_date,
            "date_planned": request_date,
            "is_single_delivery_destination": is_single_delivery_destination,
            "destination_warehouse_id": destination_warehouse_id,
        }
        active_model = context.get('active_model')
        branch_id = False
        if active_model == 'purchase.request':
            request_id = self.env[active_model].browse(context.get('active_ids'))
            data['origin'] = request_id.name
            request_id.write({'purchase_req_state' : 'in_progress'})
            if request_id.branch_id:
                branch_id = request_id.branch_id.id
            data['analytic_account_group_ids'] = [(6, 0, request_id.analytic_account_group_ids.ids)]
        elif active_model == 'purchase.request.line':
            data['origin'] = origin
            request_id.write({'purchase_req_state' : 'in_progress'})
            if request_id.branch_id:
                branch_id = request_id.branch_id.id
            data['analytic_account_group_ids'] = [(6, 0, request_id.mapped('analytic_account_group_ids').ids)]
        if context.get('goods_order'):
            data['is_goods_orders'] = True
        elif context.get('services_good'):
            data['is_services_orders'] = True
        elif context.get('assets_orders'):
            data['is_assets_orders'] = True
        data['branch_id'] = branch_id
        data['date_order'] = datetime.now()
        data['journal_id'] = self.journal_id.id
        return data

    @api.model
    def _get_purchase_line_onchange_fields(self):
        return ["product_uom", "price_unit", "name", "taxes_id"]

    @api.model
    def _execute_purchase_line_onchange(self, vals):
        cls = self.env["purchase.order.line"]
        onchanges_dict = {
            "onchange_product_id": self._get_purchase_line_onchange_fields()
        }
        for onchange_method, changed_fields in onchanges_dict.items():
            if any(f not in vals for f in changed_fields):
                obj = cls.new(vals)
                getattr(obj, onchange_method)()
                for field in changed_fields:
                    vals[field] = obj._fields[field].convert_to_write(obj[field], obj)

    def create_allocation(self, po_line, pr_line, new_qty, alloc_uom):
        vals = {
            "requested_product_uom_qty": new_qty,
            "product_uom_id": alloc_uom.id,
            "purchase_request_line_id": pr_line.id,
            "purchase_line_id": po_line.id,
        }
        return self.env["purchase.request.allocation"].create(vals)

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        if not item.product_id:
            raise UserError(_("Please select a product for all lines"))
        product = item.product_id

        # Keep the standard product UOM for purchase order so we should
        # convert the product quantity to this UOM
        qty = item.product_uom_id._compute_quantity(
            item.product_qty, product.uom_po_id or product.uom_id
        )
        # Suggest the supplier min qty as it's done in Odoo core
        min_qty = item.line_id._get_supplier_min_qty(product, po.partner_id)
        qty = max(qty, min_qty)
        date_required = item.line_id.date_required
        vals = {
            "name": product.name,
            "order_id": po.id,
            "product_id": product.id,
            "product_uom": product.uom_po_id.id or product.uom_id.id,
            "price_unit": 0.0,
            "product_qty": qty,
            "account_analytic_id": item.line_id.analytic_account_id.id,
            "purchase_request_lines": [(4, item.line_id.id)],
            "date_planned": datetime(
                date_required.year, date_required.month, date_required.day
            ),
            "move_dest_ids": [(4, x.id) for x in item.line_id.move_dest_ids],
        }
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            vals['is_goods_orders'] = True
        elif context.get('services_good'):
            vals['is_services_orders'] = True
        elif context.get('assets_orders'):
            vals['is_assets_orders'] = True
        vals['destination_warehouse_id'] = item.line_id.dest_loc_id.id
        vals['picking_type_id'] = item.line_id.picking_type_dest.id
        vals['request_line_id'] = item.line_id.id
        vals['analytic_tag_ids'] = [(6, 0, item.line_id.analytic_account_group_ids.ids)]
        self._execute_purchase_line_onchange(vals)
        return vals

    @api.model
    def _get_purchase_line_name(self, order, line):
        product_lang = line.product_id.with_context(
            {"lang": self.supplier_id.lang, "partner_id": self.supplier_id.id}
        )
        name = product_lang.display_name
        if product_lang.description_purchase:
            name += "\n" + product_lang.description_purchase
        return name

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
        order_line_data.append(("destination_warehouse_id", "=", item.line_id.dest_loc_id.id or False))
        return order_line_data

    def create_dp_from_pr(self, purchase_request_ids):
        purchase_obj = self.env["purchase.order"]
        po_line_obj = self.env["purchase.order.line"]
        is_single_request_date = purchase_request_ids.mapped('is_single_request_date')
        is_single_delivery_destination = purchase_request_ids.mapped('is_single_delivery_destination')
        context = dict(self.env.context) or {}
        if self.purchase_order_id:
            purchase = self.purchase_order_id
            for item in self.item_ids:
                filtered_product_ids = purchase.order_line.filtered(lambda m: m.product_id.id == item.product_id.id and m.destination_warehouse_id.id == item.line_id.dest_loc_id.id)
                purchase.analytic_account_group_ids = [(4, analytic) for analytic in item.request_id.analytic_account_group_ids.ids]
                for filter_product in filtered_product_ids:
                    filter_product.product_qty += item.product_qty
        else:
            name = ""
            for pr in purchase_request_ids:
                if not name:
                    name += pr.name
                else:
                    name += ", %s" % pr.name
            if len(set(is_single_request_date)) > 1:
                is_single_request_date = False
                request_date = False
            else:
                is_single_request_date = is_single_request_date[0]
                request_date = purchase_request_ids[0].request_date
            if len(set(is_single_delivery_destination)) > 1:
                is_single_delivery_destination = False
                destination_warehouse = False
            else:
                is_single_delivery_destination = is_single_delivery_destination[0]
                destination_warehouse = purchase_request_ids[0].destination_warehouse
            po_data = self._prepare_purchase_order(
                purchase_request_ids.picking_type_id,
                purchase_request_ids.group_id,
                purchase_request_ids.company_id,
                name,
                is_single_request_date,
                request_date,
                is_single_delivery_destination,
                destination_warehouse,
                purchase_request_ids,
            )
            purchase = purchase_obj.with_context(context).create(po_data)
            res_item_ids = self.item_ids.sorted(key=lambda x: x.product_id.id)
            same_line = []
            for item in res_item_ids:
                if item not in same_line:
                    same_line = res_item_ids.filtered(lambda m: m.id != item.id and m.product_id.id == item.product_id.id and m.line_id.dest_loc_id.id == item.line_id.dest_loc_id.id and m.line_id.date_required == item.line_id.date_required)
                    if same_line:
                        item.product_qty += sum(same_line.mapped('product_qty'))
                else:
                    continue
                po_line_data = self._prepare_purchase_order_line(purchase, item)
                if item.keep_description:
                    po_line_data["name"] = item.name
                po_line_obj.create(po_line_data)
        return purchase.ids

    def make_purchase_order_direct(self):
        res = []
        purchase_obj = self.env["purchase.order"]
        po_line_obj = self.env["purchase.order.line"]
        pr_line_obj = self.env["purchase.request.line"]
        context = dict(self.env.context) or {}
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        if context.get('active_model') == "purchase.request.line":
            purchase_order_id = self.env[context.get('active_model')].browse(context.get('active_ids'))
            is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
            # is_good_services_order = self.env.company.is_good_services_order
            if is_good_services_order:
                if all(line.is_goods_orders for line in purchase_order_id):
                    context.update({'is_goods_orders': True, 'goods_order': True, 'default_is_goods_orders': True})
                elif all(line.is_services_orders for line in purchase_order_id):
                    context.update({'is_services_orders': True, 'services_good': True, 'default_is_services_orders': True})
                if purchase_order_id and 'is_assets_orders' in purchase_order_id[0]._fields and \
                    all(line.is_assets_orders for line in purchase_order_id):
                    context.update({'is_assets_orders': True, 'assets_orders': True, 'default_is_assets_orders': True})
                if purchase_order_id and 'is_rental_orders' in purchase_order_id[0]._fields and \
                    all(line.is_rental_orders for line in purchase_order_id):
                    context.update({'is_rental_orders': True, 'rentals_orders': True, 'default_is_rental_orders': True})
            for line in purchase_order_id:
                if not line.assigned_to:
                    line.assigned_to = self.env.user.id
        pr_qty_limit = IrConfigParam.get_param('pr_qty_limit', "no_limit")
        max_percentage = int(IrConfigParam.get_param('max_percentage', 0))
        # pr_qty_limit = self.env.company.pr_qty_limit
        # max_percentage = self.env.company.max_percentage
        purchase_ids = []
        if context.get('active_model') == "purchase.request":
            recs = {}
            purchase = False
            for item in self.item_ids:
                product_id = item.product_id.id
                if product_id in recs:
                    recs[product_id]['product_qty'] += item.product_qty
                    recs[product_id]['rem_qty'] += item.rem_qty
                else:
                    recs[product_id] = {}
                    recs[product_id]['product_qty'] = item.product_qty
                    recs[product_id]['rem_qty'] = item.rem_qty

            tmp_recs = {}
            for item in self.item_ids:
                product_id = item.product_id.id
                if product_id in tmp_recs:
                    continue
                else:
                    tmp_recs[product_id] = True
                    item.product_qty = recs[product_id]['product_qty']
                    item.rem_qty = recs[product_id]['rem_qty']

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
                    filtered_product_ids = purchase.order_line.filtered(lambda m: m.product_id.id == item.product_id.id and m.destination_warehouse_id.id == item.line_id.dest_loc_id.id)
                    purchase.analytic_account_group_ids = [(4, analytic) for analytic in line.request_id.analytic_account_group_ids.ids]
                    for filter_product in filtered_product_ids:
                        filter_product.product_qty += item.product_qty
                if not purchase:
                    po_data = self._prepare_purchase_order(
                        line.request_id.picking_type_id,
                        line.request_id.group_id,
                        line.company_id,
                        line.origin,
                        line.request_id.is_single_request_date,
                        line.request_id.request_date,
                        line.request_id.is_single_delivery_destination,
                        line.request_id.destination_warehouse
                    )
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
                purchase_ids.append(purchase.id)
                computerem = item.rem_qty - item.product_qty
        elif context.get('active_model') == "purchase.request.line":
            purchase_request_line_ids = self.env[context.get('active_model')].browse(context.get('active_ids'))
            purchase_request_ids = purchase_request_line_ids.mapped('request_id')
            if len(purchase_request_ids.picking_type_id) > 1 or len(purchase_request_ids.group_id) > 1 or len(purchase_request_ids.company_id) > 1:
                for request_id in purchase_request_ids:
                    recs = {}
                    purchase = False
                    for item in self.item_ids.filtered(lambda r: r.request_id.id == request_id.id):
                        product_id = item.product_id.id
                        if product_id in recs:
                            recs[product_id]['product_qty'] += item.product_qty
                            recs[product_id]['rem_qty'] += item.rem_qty
                        else:
                            recs[product_id] = {}
                            recs[product_id]['product_qty'] = item.product_qty
                            recs[product_id]['rem_qty'] = item.rem_qty
                    tmp_recs = {}
                    for item in self.item_ids.filtered(lambda r: r.request_id.id == request_id.id):
                        product_id = item.product_id.id
                        if product_id in tmp_recs:
                            continue
                        else:
                            tmp_recs[product_id] = True
                            item.product_qty = recs[product_id]['product_qty']
                            item.rem_qty = recs[product_id]['rem_qty']

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
                            filtered_product_ids = purchase.order_line.filtered(lambda m: m.product_id.id == item.product_id.id and m.destination_warehouse_id.id == item.line_id.dest_loc_id.id)
                            purchase.analytic_account_group_ids = [(4, analytic) for analytic in line.request_id.analytic_account_group_ids.ids]
                            for filter_product in filtered_product_ids:
                                filter_product.product_qty += item.product_qty
                        if not purchase:
                            po_data = self._prepare_purchase_order(
                                line.request_id.picking_type_id,
                                line.request_id.group_id,
                                line.company_id,
                                request_id.name,
                                line.request_id.is_single_request_date,
                                line.request_id.request_date,
                                request_id.is_single_delivery_destination,
                                request_id.destination_warehouse,
                                request_id
                            )
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
                        purchase_ids.append(purchase.id)
                        computerem = item.rem_qty - item.product_qty
            else:
                # menyatukan PR line dalam 1 direct purchase apabila PR memungkinkan
                purchase_ids = self.with_context(context).create_dp_from_pr(purchase_request_ids)
        if not purchase_ids:
            return False
        return {
            "domain": [("id", "in", purchase_ids)],
            "name": _("RFQ"),
            "view_mode": "tree,form",
            "res_model": "purchase.order",
            "view_id": False,
            "context": context,
            "type": "ir.actions.act_window",
        }

class CreatePurchaseRequestDirectLines(models.TransientModel):
    _name = "create.purchase.request.direct.lines"
    _description = "Create Purchase Request Direct Lines"


    wiz_id = fields.Many2one(
        comodel_name="create.purchase.request.direct",
        string="Wizard",
        required=True,
        ondelete="cascade",
        readonly=True,
    )
    line_id = fields.Many2one(
        comodel_name="purchase.request.line", string="Purchase Request Line"
    )
    request_id = fields.Many2one(
        comodel_name="purchase.request",
        related="line_id.request_id",
        string="Purchase Request",
        readonly=False,
    )
    product_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        related="line_id.product_id",
        readonly=False,
    )
    name = fields.Char(string="Description", required=True)
    product_qty = fields.Float(
        string="Quantity to purchase", digits="Product Unit of Measure"
    )
    product_uom_id = fields.Many2one(
        comodel_name="uom.uom", string="UoM", required=True
    )
    destination_location_id = fields.Many2one('stock.location', string='Destination Location')
    rem_qty = fields.Float(compute='_compute_rem_qty', string='Remaining Qty', default=0.0)
    keep_description = fields.Boolean(
        string="Copy descriptions to new PO",
        help="Set true if you want to keep the "
        "descriptions provided in the "
        "wizard in the new PO.",
    )

    @api.depends('rem_qty')
    def _compute_rem_qty(self):
        for record in self:
            record.rem_qty = 0 if record.line_id.remaning_qty < 0 else record.line_id.remaning_qty
