
from odoo import api, fields, models, SUPERUSER_ID, tools, _
from datetime import datetime
from odoo.exceptions import UserError, ValidationError, Warning


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

    @api.onchange('supplier_id')
    def onchange_partner(self):
        b = {}
        if self.env['ir.config_parameter'].sudo().get_param('is_vendor_approval_matrix'):
        # if self.env.company.is_vendor_approval_matrix:
            b = {'domain': {'supplier_id': [('state2', '=', 'approved'), ("is_company", "=", True), ('supplier_rank', '>', 0), ('is_vendor', '=', True)]}}
        else:
            b = {'domain': {'supplier_id': [('supplier_rank', '>', 0), ('is_vendor', '=', True)]}}
        return b

    @api.model
    def _domain_supplier_ids(self):
        domain = [("is_vendor","=",True)]
        pr_line_ids =False
        if self._context.get('active_model') == "purchase.request.line":
            pr_line_ids = self.env['purchase.request.line'].browse(self.env.context.get('active_ids'))

        elif self._context.get('active_model') == "purchase.request":
            pr_line_ids = self.env['purchase.request'].browse(self.env.context.get('active_ids'))
        if pr_line_ids:
            branch_ids = [branch_id for branch_id in pr_line_ids.mapped('branch_id').ids]
            domain.extend(['|',('branch_id','in',branch_ids),('branch_id','=',False)])
        return domain

    supplier_ids = fields.Many2many('res.partner', string="Vendor",
                                    required=True,
                                    domain=_domain_supplier_ids,
                                    # domain=[("is_company", "=", True)],
                                    context={'res_partner_search_mode': 'supplier', 'show_vat': True,
                                             'tree_view_ref': 'equip3_purchase_operation.view_res_partner_line_tree',
                                             'default_is_vendor': 1,
                                             'search_default_supplier': 1},)

    supplier_id = fields.Many2one(
        comodel_name="res.partner",
        string="Supplier",
        required=False,
        domain=[("is_company", "=", True)],
        context={"res_partner_search_mode": "supplier", "default_is_company": True},
    )
    create_rfq = fields.Selection([
        ('existing_rfq', 'Existing RFQ'),
        ('new_rfq', 'New RFQ')], string='Create RFQ', default='existing_rfq')
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Vendor")
    message = fields.Text("Message", compute='_compute_message')

    @api.depends('item_ids')
    def _compute_message(self):
        for rec in self:
            res_pr_line = []
            if len(rec.item_ids) > 1:
                for i in rec.item_ids:
                    if i.product_qty < 1:
                        res_pr_line.append(i.line_id.request_id.name)
            if res_pr_line:
                rec.message = 'Warning!\n' + ', '.join(res_pr_line) + "  will not included into RFQ due to remaining qty = 0."
            else:
                rec.message = ''


    @api.onchange('purchase_order_id')
    def change_partner(self):
        for i in self:
            if i.purchase_order_id:
                i.partner_id = i.purchase_order_id.partner_id.id
            else:
                i.partner_id = False

    @api.onchange('create_rfq')
    def check_create_rfq(self):
        if self.create_rfq == 'existing_rfq':
            self.supplier_ids = False
        else:
            self.purchase_order_id = False

    @api.model
    def _fill_objects(self):
        vendor = self.env['res.partner'].search(
            ['&', ('supplier_id', '!=', False), ('supplier_ids', '=', False)])
        for r in vendor:
            if not r.supplier_ids and r.supplier_id:
                r.supplier_ids = [(4, r.supplier_id.id)]
            else:
                r.supplier_ids = False

    @api.model
    def _prepare_purchase_order_line(self, po, item):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_purchase_order_line(po, item)
        context = dict(self.env.context) or {}
        if context.get('goods_order'):
            res['is_goods_orders'] = True
        elif context.get('services_good'):
            res['is_services_orders'] = True
        elif context.get('assets_orders'):
            res['is_assets_orders'] = True
        destination_warehouse_id = item.line_id.dest_loc_id.id or False
        picking_type_id = item.line_id.dest_loc_id.in_type_id.id or False
        if po and not destination_warehouse_id and not picking_type_id:
            stock_warehouse = False
            if po.company_id and po.branch_id:
                self.env.cr.execute("""
                        SELECT id,in_type_id
                        FROM stock_warehouse
                        WHERE company_id = %s AND branch_id = %s AND active = True ORDER BY id ASC LIMIT 1
                    """ % (po.company_id.id, po.branch_id.id))
                stock_warehouse = self.env.cr.fetchall()
            destination_warehouse_id = stock_warehouse[0][0] if stock_warehouse else False
            picking_type_id = stock_warehouse[0][1] if stock_warehouse else False
        res['price_unit'] = item.line_id.currency_id._convert(item.line_id.estimated_cost, po.currency_id, item.line_id.company_id, fields.Date.context_today(self))
        res['destination_warehouse_id'] = destination_warehouse_id
        res['picking_type_id'] = picking_type_id
        res['request_line_id'] = item.line_id.id
        res['analytic_tag_ids'] = [(6, 0, item.line_id.analytic_account_group_ids.ids)]
        res["product_uom"] = item.product_uom_id and item.product_uom_id.id
        res['branch_id'] = po.branch_id.id if po.branch_id else self.env.branch.id
        return res

    @api.model
    def _prepare_purchase_order(self, picking_type, group_id, company, origin):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._prepare_purchase_order(picking_type, group_id, company, origin)
        context = dict(self.env.context) or {}
        active_model = context.get('active_model')
        request_id = self.env[active_model].browse(context.get('active_ids'))
        if active_model == 'purchase.request':
            # request_id = self.env[active_model].browse(context.get('active_ids'))
            res['is_delivery_receipt'] = request_id.is_single_request_date
            res['is_single_delivery_destination'] = request_id.is_single_delivery_destination
            res['currency_id'] = self.supplier_id.property_purchase_currency_id.id or request_id.currency_id.id or self.env.company.currency_id.id
            res['origin'] = request_id.name
        elif active_model == 'purchase.request.line':
            request_line_ids = self.env[active_model].browse(context.get('active_ids'))
            res['currency_id'] = self.supplier_id.property_purchase_currency_id.id or self.env.company.currency_id.id
            res['origin'] = ','.join(request_line_ids.mapped('request_id.name'))
        if context.get('goods_order'):
            res['is_goods_orders'] = True
        elif context.get('services_good'):
            res['is_services_orders'] = True
        elif context.get('assets_orders'):
            res['is_assets_orders'] = True
        branch_id = False
        if request_id.branch_id:
            if len(request_id.branch_id) > 1:
                branch_id = self.env.branch.id
            else:
                branch_id = request_id.branch_id.id
        stock_warehouse = False
        destination_warehouse_id = self.pr_id.destination_warehouse.id or False
        picking_type_id = self.pr_id.picking_type_id.id
        if not destination_warehouse_id or not picking_type_id:
            if request_id.company_id.id and branch_id:
                self.env.cr.execute("""
                        SELECT id,in_type_id
                        FROM stock_warehouse
                        WHERE company_id = %s AND branch_id = %s AND active = True ORDER BY id ASC LIMIT 1
                    """ % (request_id.company_id.id, branch_id))
                stock_warehouse = self.env.cr.fetchall()
            destination_warehouse_id = stock_warehouse[0][0] if stock_warehouse else False
            picking_type_id = stock_warehouse[0][1] if stock_warehouse else False
        res['destination_warehouse_id'] = destination_warehouse_id
        res['picking_type_id'] = picking_type_id
        res['branch_id'] = branch_id
        res['date_order'] = datetime.now()
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

    @api.model
    def _get_order_line_search_domain(self, order, item):
        res = super(PurchaseRequestLineMakePurchaseOrder, self)._get_order_line_search_domain(order, item)
        res.append(
            ("destination_warehouse_id", "=", item.line_id.dest_loc_id.id or False)
        )
        if self.pr_id:
            if not self.pr_id.is_single_request_date:
                res.append(
                    ("date_planned", "=", item.line_id.date_required or False)
                )
        return res

    @api.model
    def _prepare_item(self, line):
        res = super()._prepare_item(line)
        res['date_required'] = line.date_required
        res['dest_loc_id'] = line.dest_loc_id.id
        res['product_qty'] = 0 if line.remaning_qty < 0 else line.remaning_qty
        return res

    def get_vendor_pricelist(self, vendor_pricelist, item):
        res_vendor_pricelist = []
        get_min_price = 0
        use_vendor_pl = False
        # mendapatkan vendor pricelist paling optimal
        if vendor_pricelist:
            for vendor in vendor_pricelist:
                if vendor.date_start and vendor.date_end:
                    if vendor.date_start <= datetime.today().date() <= vendor.date_end:
                        res_vendor_pricelist.append(vendor)
                else:
                    res_vendor_pricelist.append(vendor)
        for res_vendor_pl in res_vendor_pricelist:
            if item.product_qty >= res_vendor_pl.min_qty:
                res_price = item.product_qty * res_vendor_pl.price
                if not get_min_price:
                    get_min_price = res_price
                    use_vendor_pl = res_vendor_pl
                else:
                    if get_min_price > res_price:
                        use_vendor_pl = res_vendor_pl
        return use_vendor_pl

    def mod_make_purchase_order(self):
        res = []
        context = dict(self.env.context) or {}
        purchase_obj = self.env["purchase.order"]
        po_line_obj = self.env["purchase.order.line"]
        pr_id = self.pr_id or self.env['purchase.request.line'].browse(self.env.context['active_ids']).request_id
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        is_good_services_order = IrConfigParam.get_param('is_good_services_order', False)
        # is_good_services_order = self.env.company.is_good_services_order
        if context.get('active_model') == 'purchase.request.line':
            context['default_pr_id'] = pr_id.ids
        if is_good_services_order:
            if all(line.is_goods_orders for line in pr_id.line_ids):
                context.update({'is_goods_orders': True, 'goods_order': True, 'default_is_goods_orders': True})
            elif all(line.is_services_orders for line in pr_id.line_ids):
                context.update({'is_services_orders': True, 'services_good': True, 'default_is_services_orders': True})
            if pr_id.line_ids and 'is_assets_orders' in pr_id.line_ids[0]._fields and \
                    all(line.is_assets_orders for line in pr_id.line_ids):
                context.update({'is_assets_orders': True, 'assets_orders': True, 'default_is_assets_orders': True})
            if pr_id.line_ids and 'is_rental_orders' in pr_id.line_ids[0]._fields and \
                    all(line.is_rental_orders for line in pr_id.line_ids):
                context.update({'is_rental_orders': True, 'rentals_orders': True, 'default_is_rental_orders': True})
        # qty_item = sum(self.item_ids.mapped('product_qty'))
        # if qty_item <= 0:
        #     raise ValueError("There are no products for the new RFQ!")
        if self.create_rfq == 'existing_rfq':
            res_pr_line = []
            if 'next' not in self.env.context:
                for i in self.item_ids:
                    if i.product_qty < 1:
                        res_pr_line.append(i.line_id.request_id.name)
            if res_pr_line:
                if len(self.item_ids) == 1:
                    raise ValidationError('You cannot create an RFQ for PR line with remaining quantity = 0.')

            for item in self.item_ids:
                line = item.line_id
                if item.product_qty < 1:
                    continue
                price_unit = False
                res_line_rfq = self.purchase_order_id.order_line.filtered(lambda x: x.product_id.id == item.product_id.id and x.destination_warehouse_id.id == item.line_id.dest_loc_id.id and x.date_planned.date() == item.line_id.date_required)
                vendor_pricelist = item.product_id.seller_ids.filtered(lambda r: r.name == self.purchase_order_id.partner_id and r.state1 == 'approved').sorted(
                    key=lambda r: r.min_qty
                )
                use_vendor_pl = self.get_vendor_pricelist(vendor_pricelist, item)
                # mengubah price unit dari vendor pricelist paling optimal
                if use_vendor_pl:
                    if item.product_qty >= use_vendor_pl.min_qty:
                        price_unit = use_vendor_pl.price
                if not res_line_rfq:
                    if item.product_qty > 0:
                        po_line_data = self._prepare_purchase_order_line(self.purchase_order_id, item)
                        res_line_rfq = self.purchase_order_id.order_line.filtered(lambda x: x.product_id.id == item.product_id.id and x.destination_warehouse_id.id == po_line_data['destination_warehouse_id'] and x.date_planned.date() == item.line_id.date_required)
                        if not res_line_rfq:
                            if price_unit:
                                po_line_data['price_unit'] = price_unit
                            po_line_obj.create(po_line_data)
                if res_line_rfq:
                    for i in res_line_rfq:
                        i.product_qty += item.product_qty
                        if price_unit:
                            i.price_unit = price_unit
                # penambahan self.create_allocation krna pada module aslinya (purchase_request) ini sudah ada
                # namun dihilangkan disini jadi tidak mentrigger "Qty In Progress"
                domain = self._get_order_line_search_domain(self.purchase_order_id, item)
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
                    po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                        po_line.product_uom_qty, alloc_uom
                    )
                    wizard_product_uom_qty = wizard_uom._compute_quantity(
                        item.product_qty, alloc_uom
                    )
                    all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                    self.create_allocation(po_line, line, all_qty, alloc_uom)
            res.append(self.purchase_order_id.id)
        else:
            res_pr_line = []
            if 'next' not in self.env.context:
                for i in self.item_ids:
                    if i.product_qty < 1:
                        res_pr_line.append(i.line_id.request_id.name)
            if res_pr_line:
                if len(self.item_ids) == 1:
                    raise ValidationError('You cannot create an RFQ for PR line with remaining quantity = 0.')
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
            for supplier in self.supplier_ids:
                item_ids = []
                self.supplier_id = supplier
                po_data = self._prepare_purchase_order(
                    picking_type_id,
                    group_id,
                    company_id,
                    ', '.join(origins),
                )
                po_data['from_purchase_request'] = True
                po_data['partner_id'] = supplier.id
                po_data['date_planned'] = request_date
                purchase = purchase_obj.with_context(context).create(po_data)
                res.append(purchase.id)
                purchase._onchange_partner_invoice_id()

                for item in self.item_ids:
                    branch_ids = []
                    branch_ids.append(item.line_id.branch_id.id)
                    line = item.line_id
                    if item.id not in item_ids:
                        if item.line_id.request_id.is_single_request_date and item.line_id.request_id.is_single_delivery_destination:
                            res_line = self.item_ids.filtered(lambda x: x.product_id.id == item.product_id.id and x.line_id.estimated_cost == item.line_id.estimated_cost)
                        elif item.line_id.request_id.is_single_request_date and not item.line_id.request_id.is_single_delivery_destination:
                            res_line = self.item_ids.filtered(lambda x: x.product_id.id == item.product_id.id and x.line_id.estimated_cost == item.line_id.estimated_cost and x.line_id.dest_loc_id == item.line_id.dest_loc_id)
                        elif not item.line_id.request_id.is_single_request_date and item.line_id.request_id.is_single_delivery_destination:
                            res_line = self.item_ids.filtered(lambda x: x.product_id.id == item.product_id.id and x.line_id.estimated_cost == item.line_id.estimated_cost and x.line_id.date_required == item.line_id.date_required)
                        else:
                            res_line = self.item_ids.filtered(lambda x: x.product_id.id == item.product_id.id and x.line_id.estimated_cost == item.line_id.estimated_cost and x.line_id.dest_loc_id == item.line_id.dest_loc_id and x.line_id.date_required == item.line_id.date_required)
                        qty = sum(res_line.mapped('product_qty'))
                        po_line_data = self._prepare_purchase_order_line(purchase, item)
                        po_line_data['product_qty'] = qty
                        vendor_pricelist = item.product_id.seller_ids.filtered(lambda r: r.name == supplier and r.state1 == 'approved').sorted(
                            key=lambda r: r.min_qty
                        )
                        use_vendor_pl = self.get_vendor_pricelist(vendor_pricelist, item)
                        # mengubah price unit dari vendor pricelist paling optimal
                        if use_vendor_pl:
                            if po_line_data['product_qty'] >= use_vendor_pl.min_qty:
                                po_line_data['price_unit'] = use_vendor_pl.price
                        po_line_id = False
                        if qty > 0:
                            po_line_id = po_line_obj.create(po_line_data)
                        if res_line and po_line_id:
                            for i in res_line:
                                item_ids.append(i.id)
                                i.line_id.purchase_lines = [(4,po_line_id.id)]
                                i.line_id.purchase_order_line_ids = [(4,po_line_id.id)]
                                i.line_id.purchased_qty += i.product_qty
                        # penambahan self.create_allocation krna pada module aslinya (purchase_request) ini sudah ada 
                        # namun dihilangkan disini jadi tidak mentrigger Qty In Progress
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
                            po_line_product_uom_qty = po_line.product_uom._compute_quantity(
                                po_line.product_uom_qty, alloc_uom
                            )
                            wizard_product_uom_qty = wizard_uom._compute_quantity(
                                item.product_qty, alloc_uom
                            )
                            all_qty = min(po_line_product_uom_qty, wizard_product_uom_qty)
                            self.create_allocation(po_line, line, all_qty, alloc_uom)
                    else:
                        continue
                branch_ids.append(purchase.branch_id.id)
                purchase.branch_ids = [(6, 0, branch_ids)]
        return {
            "domain": [("id", "in", res)],
            "name": _("RFQ"),
            "view_mode": "tree,form",
            "res_model": "purchase.order",
            "view_id": False,
            "context": context,
            "type": "ir.actions.act_window",
        }

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
                    'state', '=', 'draft'
                ), ('dp', '=', False)])
        return domain

    purchase_order_id = fields.Many2one(domain=_default_domain_purchase_order)

class PurchaseRequestLineMakePurchaseOrderItem(models.TransientModel):
    _inherit = "purchase.request.line.make.purchase.order.item"

    destination_location_id = fields.Many2one('stock.location', string='Destination Location')
    rem_qty = fields.Float(compute='_compute_rem_qty', string='Remaining Qty', default=0.0)
    date_required = fields.Date(string="Expected Date")
    dest_loc_id = fields.Many2one('stock.warehouse', string="Destination")

    @api.depends('rem_qty')
    def _compute_rem_qty(self):
        for record in self:
            record.rem_qty = 0 if record.line_id.remaning_qty < 0 else record.line_id.remaning_qty
