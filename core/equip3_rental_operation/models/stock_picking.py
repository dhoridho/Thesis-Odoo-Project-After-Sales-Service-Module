from odoo import fields,api,models
from odoo.exceptions import ValidationError
from datetime import datetime

class stockPicking(models.Model):
    _inherit = 'stock.picking'

    rental_return  = fields.Boolean()
    is_replace_product = fields.Boolean(string="Is Replace Product", default=False)
    is_replaced = fields.Boolean(string="Is Replaced", default=False)
    rental_product_delivery_refference = fields.Char("Rental Product Delivery Refference")
    hide_replace_product_button = fields.Boolean(
        "Hide Replace Product Button",
        compute="compute_hide_replace_product_button"
    )
    lot_ids = fields.Many2many(comodel_name="stock.production.lot", string="Serial Numbers")
    is_from_intercompany_transaction = fields.Boolean('Is FRomn INtercomany Transaction', default=False)

    @api.depends('is_replace_product', 'is_replaced', 'rental_id')
    def compute_hide_replace_product_button(self):
        for picking in self:
            if picking.is_replace_product:
                if picking.picking_type_code == "outgoing":
                    picking.hide_replace_product_button = picking.is_replaced
                else:
                    picking.hide_replace_product_button = True
            else:
                if picking.picking_type_code == "outgoing":
                    if picking.is_replaced:
                        picking.hide_replace_product_button = True
                    else:
                        picking.hide_replace_product_button = False
                else:
                    picking.hide_replace_product_button = True

    def _convert_to_asset(self):
        for move_line in self.move_line_ids:
            if move_line.product_id.type == 'asset':
                date = first_depreciation_manual_date = fields.Date.context_today(self)
                asset_category = move_line.product_id.asset_category_id

                date_list = str(date).split('-')
                cut_off_date_str = len(str(asset_category.cut_off_asset_date)) >= 2 and str(
                    asset_category.cut_off_asset_date) or '0' + str(asset_category.cut_off_asset_date)
                cut_off_date = '%s-%s-%s' % (date_list[0], date_list[1], cut_off_date_str)
                if not asset_category.prorata and str(date) > cut_off_date:
                    month = (int(date_list[1]) < 10 and '0%s' % (int(date_list[1]) + 1)) \
                            or (int(date_list[1]) >= 10 and int(date_list[1]) < 12 and str(int(date_list[1]) + 1)) \
                            or '01'
                    year = int(date_list[1]) < 12 and str(int(date_list[0])) or str(int(date_list[0]) + 1)
                    first_depreciation_manual_date = '%s-%s-%s' % (year, month, '01')
                elif not asset_category.prorata and str(date) <= cut_off_date:
                    first_depreciation_manual_date = '%s-%s-%s' % (date_list[0], date_list[1], '01')
                else:
                    first_depreciation_manual_date = date

                if move_line.product_id.asset_entry_perqty:
                    for qty in list(range(int(move_line.qty_done))):
                        asset_vals = {
                            "name": move_line.product_id.name,
                            "category_id": move_line.product_id.asset_category_id.id,
                            "value": move_line.move_id.purchase_line_id.price_unit,
                            "partner_id": self.partner_id.id,
                            "prorata": asset_category.prorata,
                            "first_depreciation_manual_date": first_depreciation_manual_date,
                            "cut_off_asset_date": asset_category.cut_off_asset_date,
                            "product_id": move_line.product_id.id,
                            "branch_id": self.branch_id.id,
                            "serial_number_id": move_line.lot_id.id,
                        }
                        if move_line.product_id.product_tmpl_id.type == 'asset':
                            asset_vals['product_template_id'] = move_line.product_id.product_tmpl_id.id
                        asset_values = self.env['account.asset.asset'].create(asset_vals).compute_depreciation_board()
                        return_of_assets = self.env['return.of.assets'].create({'product_template_id':move_line.product_id.product_tmpl_id.id,'lot_id':move_line.lot_id.id})

                else:
                    asset_vals = {
                        "name": move_line.product_id.name,
                        "category_id": move_line.product_id.asset_category_id.id,
                        "value": move_line.qty_done * move_line.move_id.purchase_line_id.price_unit,
                        "partner_id": self.partner_id.id,
                        "prorata": asset_category.prorata,
                        "first_depreciation_manual_date": first_depreciation_manual_date,
                        "cut_off_asset_date": asset_category.cut_off_asset_date,
                        "product_id": move_line.product_id.id,
                        "branch_id": self.branch_id.id,
                        "serial_number_id": move_line.lot_id.id,
                        
                    }
                    if move_line.product_id.product_tmpl_id.type == 'asset':
                        asset_vals['product_template_id'] = move_line.product_id.product_tmpl_id.id
                    asset_values = self.env['account.asset.asset'].create(asset_vals).compute_depreciation_board()

    def action_serialize(self):
        for product in self.rental_id.rental_line:
            product.lot_id.is_available_today = True

        return super(stockPicking, self).action_serialize()

    def action_assign(self):
        self.ensure_one()

        res = super(stockPicking, self).action_assign()
        self.update_lot_serial_number()

        return res

    def update_lot_serial_number(self):
        if self.rental_id:
            lot_ids = self.lot_ids
            temp = []

            for lot_id in lot_ids:
                for line in self.move_line_ids:
                    if lot_id.id not in temp:
                        line.write({'lot_id': lot_id.id})
                        temp.append(lot_id.id)

    def action_confirm(self):
        move_ids = self.move_ids_without_package
        if self.rental_id:
            if move_ids:
                self.lot_ids = [(6, 0, [move.lot_id.id for move in move_ids if move.for_rental_move])]

        if not self.show_check_availability:
            move = move_ids.filtered(
                lambda m: m.picking_id.id == self.id and m.product_id.type == 'asset'
            )
            if move:
                self.action_assign()
        
        res = super(stockPicking, self).action_confirm()


        if (
            self.is_from_intercompany_transaction
            and self.move_ids_without_package
            and self.picking_type_code == "incoming"
        ):
            self.update_lot_serial_number()

        return res

    @api.model
    def create(self, vals):
        context = dict(self.env.context) or {}
        pickings = super(stockPicking, self).create(vals)
        if context.get('rental_order'):
            for picking in pickings:
                picking.rental_id = context.get('rental_order')
                picking.branch_id = picking.rental_id.branch_id.id
        return pickings
    
    def get_partner_branch(self, company_id):
        branch = self.env['res.branch'].with_company(company_id).search(
            [
                ('company_id', '=', company_id),
            ], limit=1
        )

        return branch
    
    def get_partner_record(self, vendor_company_id):
        partner = self.env['res.partner'].search(
            [
                ('company_id', '=', vendor_company_id),
                ('type', '=', 'contact'),
                ('is_vendor', '=', True),
                ('related_company_id', '=', vendor_company_id)
            ], limit=1
        )

        return partner

    def create_intercompany_transaction(self, picking):
        """
        To avoid multi-company issue, make sure to deactivate some rules:
        - Location multi-company
        - Stock Location Multi-Branch Rule
        - Stock Warehouse Multi-Branch Rule
        - Warehouse multi-company
        - Stock Picking Multi-Branch Rule
        - stock_picking multi-company
        - stock_move multi-company
        - Stock Move Multi-Branch Rule
        - stock_move_line multi-company
        - Rental Order Group multi-branch

        Rules above moved to search_read and read_group function in Python each objects.
        """
        for picking in self.rental_pickings():
            if picking.picking_type_code == 'outgoing':
                company_id = picking.partner_id.related_company_id.id
                if not company_id:
                    raise ValidationError(
                        "Partner company for %s has not been choosen!"
                        % picking.partner_id.name
                    )

                vendor_company_id = picking.company_id.id
                partner = self.get_partner_record(vendor_company_id)
                if not partner.is_vendor:
                    raise ValidationError(
                        "Partner %s must be assign as Vendor in Purchase" % partner.name
                    )
                branch = self.get_partner_branch(company_id)

                stock_location = self.env['stock.location'].with_company(company_id).search(
                    [
                        ('company_id', '=', company_id),
                        ('branch_id', '=', branch.id),
                        ('usage', '=', 'internal'),
                        ('barcode', '!=', ''),
                    ], limit=1
                )

                picking_type = self.env['stock.picking.type'].with_company(company_id).search(
                    [
                        ('code', '=', 'incoming'),
                        ('company_id', '=', company_id)
                    ], limit=1
                )

                if stock_location:
                    location_dest_id = stock_location.id
                elif picking_type:
                    location_dest_id = picking_type.default_location_dest_id.id
                else:
                    raise ValidationError("Please set location destination for branch %s" % branch.id)

                picking_vals = {
                    'location_id': picking.location_dest_id.id,
                    'location_dest_id': stock_location.id,
                    'move_type': 'direct',
                    'partner_id': partner.id,
                    'scheduled_date': picking.scheduled_date,
                    'picking_type_id': picking_type.id,
                    'origin': picking.rental_id.name,
                    'transfer_id': picking.transfer_id.id,
                    'is_transfer_in': True,
                    'company_id': company_id,
                    'state': 'draft',
                    'branch_id': branch.id,
                    'rental_id': picking.rental_id.id,
                    'is_from_intercompany_transaction': True
                }
                intercompany_picking = (
                    self.env["stock.picking"].create(picking_vals)
                )

                sequence = 1
                for move in picking.move_ids_without_package:
                    product_id = move.product_id
                    if product_id:
                        product_id.company_id = False
                    move_vals = {
                        'move_line_sequence': sequence,
                        'picking_id': intercompany_picking.id,
                        'name': move.product_id.name,
                        'product_id': move.product_id.id,
                        'lot_id': move.lot_id.id,
                        'for_rental_move': True,
                        'product_uom_qty': move.product_uom_qty,
                        'product_uom': move.product_uom.id,
                        'location_id': intercompany_picking.location_id.id,
                        'location_dest_id': intercompany_picking.location_dest_id.id,
                        'date': intercompany_picking.scheduled_date,
                    }
                    self.env['stock.move'].create(move_vals)
                    sequence += 1
    
    def create_purchase_order_rental(self):
        """
        To avoid multi-company and branch issue, make sure to deactivate some rules:
        - Purchase Order Group multi-branch
        - Purchase Team Analysis Group multi-branch
        - Purchase Order Line multi-company
        - Purchase Order Line Group multi-branch

        Rules above moved to search_read and read_group function in Python for each objects.
        """
        for picking in self.rental_pickings():
            rental = picking.rental_id
            company_id = rental.partner_id.related_company_id.id
            if not company_id:
                raise ValidationError(
                    "Partner company for %s has not been choosen!"
                    % rental.partner_id.name
                )

            vendor_company_id = rental.company_id.id
            partner = self.get_partner_record(vendor_company_id)
            if not partner.is_vendor:
                raise ValidationError(
                    "Partner %s must be assign as Vendor in Purchase" % partner.name
                )
            branch = self.get_partner_branch(company_id)

            purchase_order = self.env["purchase.order"].create(
                {
                    "partner_id": partner.id,
                    "company_id": company_id,
                    "branch_id": branch.id,
                    "date_planned": rental.start_date,
                    "origin": rental.name,
                    "is_rental_orders": True,
                    'rent_duration': rental.rental_initial,
                    'rent_duration_unit': rental.rental_initial_type,
                    'po': True,

                }
            )

            for line in rental.rental_line:
                purchase_order_lines = self.env["purchase.order.line"].search(
                    [("order_id", "=", purchase_order.id)]
                )
                same_products = purchase_order_lines.filtered(
                    lambda po_line: line.product_id.id == po_line.product_id.id
                )
                if same_products:
                    for po_line in same_products:
                        po_line.write({"product_qty": po_line.product_qty + 1})
                else:
                    purchse_order_line = self.env["purchase.order.line"].create(
                        {
                            "product_id": line.product_id.id,
                            "product_qty": 1,
                            "date_planned": datetime.now(),
                            "product_uom": line.product_id.uom_id.id,
                            "price_unit": line.price_unit,
                            "display_type": False,
                            "order_id": purchase_order.id,
                        }
                    )
            
            purchase_order.button_confirm()

    def _action_done(self):
        context = dict(self.env.context) or {}
        res = super(stockPicking, self)._action_done()

        # make sure this method only apply for rental pickings
        for picking in self.rental_pickings():
            rental_id = picking.rental_id
            rental_id.write({
                'state': 'running',
                'state2': 'picked',
                'damage_order_cost': self.damage_cost_initem,
            })
            if rental_id.is_return:
                rental_id.write({
                'state2': 'returned'
            })
            for line in picking.checklist_line_rental:
                filter_line = rental_id.checklist_line_ids.filtered(lambda r: r.id == line.reff_id)
                filter_line.write({'is_outitem': line.is_outitem, 'is_initem': line.is_initem})
                to_remove_items_rental_order = rental_id.checklist_line_ids.filtered(
                    lambda r: r.is_outitem == False
                )
                if to_remove_items_rental_order:
                    to_remove_items_rental_order.unlink()
                if not line.is_outitem:
                    line.unlink()

            if picking.picking_type_code == "incoming":
                data = []
                for move in picking.move_line_ids:
                    for damage in picking.damage_cost_line_ids.filtered(
                        lambda d: d.lot_id.name == move.lot_id.name
                    ):
                        values = {
                            'lot_id': damage.lot_id.id,
                            'damage_notes': damage.damage_notes,
                            'attachment': damage.attachment,
                            'damage_cost': damage.damage_cost,
                        }
                        data.append((0, 0, values))
                rental_id.damage_cost_line_ids = data
                rental_do = rental_id.picking_ids.filtered(lambda p: p.name in picking.origin and p.picking_type_code == 'outgoing')
                rental_do.damage_cost_line_ids = data

            receiving_note_done = rental_id.picking_ids.filtered(
                lambda line: line.picking_type_code == 'incoming' and
                line.state == 'done'
            )
            receiving_notes = rental_id.picking_ids.filtered(
                lambda line: line.picking_type_code == 'incoming'
            )
            delivery_order = rental_id.picking_ids.filtered(
                lambda line: line.picking_type_code == 'outgoing'
            )
            picking_done = rental_id.picking_ids.filtered(lambda line: line.state == 'done')            
            if receiving_note_done and picking_done:
                if (len(rental_id.picking_ids) == len(picking_done) and
                    len(receiving_notes) == len(receiving_note_done) and
                    len(delivery_order) == len(receiving_notes)):
                    rental_id.write({
                        'is_in_validate': True,
                        'state2': 'returned'
                    })

            if (
                picking.state == "done"
                and rental_id.is_intercompany_transaction
                and picking.picking_type_code == "outgoing"
            ):
                self.create_intercompany_transaction(picking)

                if rental_id.state == "running":
                    self.create_purchase_order_rental()

        return res
    
    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain += [("company_id", "in", context.get("allowed_company_ids"))]

        if context.get("allowed_branch_ids"):
            domain += [
                "|",
                ("branch_id", "in", context.get("allowed_branch_ids")),
                ("branch_id", "=", False),
            ]

        result = super(stockPicking, self).search_read(
            domain=domain, fields=fields, offset=offset, limit=limit, order=order
        )

        return result

    @api.model
    def read_group(
        self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True
    ):
        domain = domain or []
        context = self.env.context

        if context.get("allowed_company_ids"):
            domain.extend([("company_id", "in", self.env.companies.ids)])

        if context.get("allowed_branch_ids"):
            domain.extend(
                [
                    "|",
                    ("branch_id", "in", context.get("allowed_branch_ids")),
                    ("branch_id", "=", False),
                ]
            )
        return super(stockPicking, self).read_group(
            domain,
            fields,
            groupby,
            offset=offset,
            limit=limit,
            orderby=orderby,
            lazy=lazy,
        )
