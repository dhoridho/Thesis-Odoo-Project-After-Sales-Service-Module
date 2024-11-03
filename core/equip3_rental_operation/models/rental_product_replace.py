from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class RentalProductReplaceInherit(models.Model):
    _inherit = "rental.product.replace"

    replace_product_ids = fields.One2many(
        comodel_name="replace.new.product.line",
        inverse_name="replace_id",
        compute="_compute_replace_product_ids",
        string=" Replace Products",
    )

    @api.depends(
        "existing_product_ids.replace_product_id",
        "existing_product_ids.replace_serial_number_id",
    )
    def _compute_replace_product_ids(self):
        replace_product_lines = []
        for line in self.existing_product_ids:
            if line.replace_product_id and line.replace_serial_number_id:
                replace_product_lines.append(
                    (
                        0,
                        0,
                        {
                            "product_id": line.replace_product_id.id,
                            "lot_id": line.replace_serial_number_id.id,
                        },
                    )
                )

                self.replace_product_ids = replace_product_lines
            else:
                self.replace_product_ids = False

    @api.model
    def default_get(self, fields):
        rec = super(RentalProductReplaceInherit, self).default_get(fields)
        picking_id = self._context.get("active_id")
        moves = self.env["stock.picking"].browse(picking_id).move_ids_without_package
        exlines = []
        for move in moves:
            exlines.append(
                (
                    0,
                    0,
                    {
                        "ro_line_id": move.rental_line_id.id,
                        "replace_id": self.id,
                        "replace_item": True,
                        "product_id": move.product_id.id,
                        "product_categ_id": move.product_id.categ_id.id,
                        "lot_id": move.lot_id.id,
                        "product_qty": 1,
                    },
                )
            )
        rec.update({"existing_product_ids": exlines})
        return rec

    def action_create_return(self, picking):
        # returned_picking = (
        #     self.env["stock.return.picking"]
        #     .sudo()
        #     .search([("picking_id", "=", picking.id)])
        # )
        # # raise ValidationError(f"{returned_picking}")
        # if not returned_picking:
        return_obj = (
            self.env["stock.return.picking"]
            .sudo()
            .create({"picking_id": picking.id})
        )
        return_obj._onchange_picking_id()
        if picking.move_line_ids:
            picking_line = []
            for move_line in picking.move_line_ids:
                picking_line.append(
                    (
                        0,
                        0,
                        {
                            "product_id": move_line.product_id.id,
                            "lot_id": move_line.lot_id and move_line.lot_id.id,
                            "uom_id": move_line.product_uom_id.id,
                            "qty": move_line.qty_done,
                        },
                    )
                )
            return_obj.return_line_ids = picking_line
        return_obj.create_returns()
        picking.rental_return = True

    def replace_product(self):
        active_id = self._context.get("active_id")
        current_picking = self.env["stock.picking"].browse(active_id)
        rental = current_picking.rental_id
        is_replace = []
        replace_lines = []

        for line in self.existing_product_ids:
            if line.replace_serial_number_id.id == line.lot_id.id:
                raise ValidationError(
                    _("You cannot replace product with the same Serial Number!")
                )
            elif not line.replace_product_id:
                raise ValidationError(_("Replace Product cannot be empty!"))
            elif not line.replace_serial_number_id:
                raise ValidationError(_("Replace Serial Number cannot be empty!"))
            elif not line.replace_product_id and not line.replace_serial_number_id:
                raise ValidationError(
                    _("Replace Product and Replace Serial Number cannot be empty!")
                )

        for existing_product in self.existing_product_ids:
            lot_id = existing_product.ro_line_id.lot_id
            rental_histories = self.env["rental.history"].search(
                [
                    ("production_lot_id_custom", "=", lot_id.id),
                    ("rental_id", "=", rental.id),
                ]
            )
            for rental_history in rental_histories:
                rental_history.state = "close"

        if current_picking.state != "done":
            current_picking.action_cancel()
        else:
            self.action_create_return(current_picking)

        for replace_line in self.replace_product_ids:
            if rental.rental_initial_type == "months":
                replace_line.product_id.replacement_value = replace_line.unit_price
            if rental.rental_initial_type == "weeks":
                replace_line.product_id.weekly_replacement_value = (
                    replace_line.unit_price
                )
            if rental.rental_initial_type == "days":
                replace_line.product_id.daily_replacement_value = (
                    replace_line.unit_price
                )

            product = replace_line.product_id
            name = product.name_get()[0][1]
            pick_type = (
                self.env["stock.picking.type"]
                .search(
                    [
                        ("name", "=", _("Delivery Orders")),
                        ("warehouse_id", "=", rental.warehouse_id.id),
                    ],
                    limit=1,
                )
                .id
            )
            if product.description_sale:
                name += "\n" + product.description_sale

            vals = {
                "name": name,
                "product_categ_id": replace_line.product_id.categ_id.id,
                "product_id": replace_line.product_id.id,
                "price_unit": rental.rental_initial * replace_line.unit_price,
                "lot_id": replace_line.lot_id.id,
                "rental_id": rental.id,
            }
            replace_line.lot_id.is_available_today = False
            replace_lines.append(self.env["rental.order.line"].create(vals).id)
            self.env["rental.history"].create(
                {
                    "production_lot_id_custom": vals["lot_id"],
                    "start_date": rental.start_date,
                    "end_date": rental.end_date,
                    "rental_id": vals["rental_id"],
                    "state": "confirm",
                }
            )

        if replace_lines:
            for order_line in self.env["rental.order.line"].browse(replace_lines):
                # Create picking
                order_line._action_launch_procurement_rule_custom()
                order_line.unlink()

            if current_picking.picking_type_code == "outgoing":
                current_picking.is_replaced = True

        # Find created picking from rental product replace
        created_picking = self.env["stock.picking"].search(
            [("picking_type_code", "=", "outgoing")], limit=1, order="create_date desc"
        )
        created_picking.rental_id = rental.id
        created_picking.rental_product_delivery_refference = current_picking.name
        created_picking.is_replace_product = True

        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'rental.order',
            'target': 'current',
            'res_id': rental.id
        }


class ReplaceExistingProductLineInherit(models.Model):
    _inherit = "replace.existing.product.line"

    lot_avail_ids = fields.Many2many(
        comodel_name="stock.production.lot",
        string="Allowed Lot Ids",
        compute="_compute_lot_avail_ids",
    )
    replace_product_id = fields.Many2one(
        comodel_name="product.product",
        domain="[('categ_id', '=', product_categ_id)]",
        required=True,
        string="Replace Product",
    )
    replace_serial_number_id = fields.Many2one(
        comodel_name="stock.production.lot",
        domain="[('id', 'in', lot_avail_ids)]",
        required=True,
        string="Replace Serial Number",
    )

    @api.depends("replace_product_id")
    def _compute_lot_avail_ids(self):
        for line in self:
            if line.replace_product_id:
                avail_lot_ids = self.env['stock.production.lot'].search(
                    [
                        ('product_id', '=', line.replace_product_id.id),
                        ('product_qty', '>', 0),
                        ('is_available_today', '=', True)
                    ]
                )
                if avail_lot_ids:
                    line.lot_avail_ids = [
                        (6, 0, [lot.id for lot in avail_lot_ids])
                    ]
                else:
                    line.lot_avail_ids = False
            else:
                line.lot_avail_ids = False
