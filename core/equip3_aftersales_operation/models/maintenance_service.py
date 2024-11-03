from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import date, timedelta


class Equip3MaintancenService(models.Model):
    _inherit = "sale.service"
    _name = "maintenance.service"
    _description = "Aftersales Maintenance Service"

    # Pending, Handle, On Check, Service, Done, Undone, Closed
    state = fields.Selection(
        [
            ("pending", _("Pending")),
            ("handle", _("Handle")),
            ("oncheck", _("On Check")),
            ("service", _("Service")),
            ("done", _("Done")),
            ("undone", _("Undone")),
            ("closed", _("Closed")),
        ],
        default="pending",
        string="State",
    )

    line_ids = fields.One2many(
        "sale.service.line", "maintenance_id", string=_("Order Products Line")
    )
    line_material_ids = fields.One2many(
        "sale.service.line", "maintenance_material_id", string=_("Order Material Line")
    )
    purchase_ids = fields.Many2many(
        "purchase.order",
        "purchase_order_maintenance_service_rel",
        "purchase_id",
        "service_id",
    )
    invoice_ids = fields.Many2many(
        "account.move",
        "account_move_maintenance_service_rel",
        "move_id",
        "service_id",
        string=_("Invoices"),
    )

    def process_stock_move(self):
        for rec in self:
            moves = self.env["stock.move"]
            for mat in rec.line_material_ids:
                moves |= self.env["stock.move"].create(
                    {
                        "name": rec.name,
                        "date": rec.create_date,
                        "product_id": mat.product_id.id,
                        "product_uom_qty": mat.product_qty,
                        "product_uom": mat.product_uom.id,
                        "location_dest_id": rec.partner_id.property_stock_customer.id,
                        "location_id": rec.location_id.id,
                        "company_id": rec.company_id.id,
                    }
                )
            moves._action_confirm()
            moves._action_assign()
            messg = ""
            _states = dict(moves._fields["state"].selection)
            for _move in moves.filtered(lambda m: m.state != "assigned"):
                messg += f"Product: {_move.product_id.name}, state: {_states.get(_move.state)}\n"
            if messg:
                raise ValidationError(
                    _(
                        f"This Maintenance Service cannot be closed due to insufficient material available in this location\n{messg}"
                    )
                )
            for moveline in moves.mapped("move_line_ids"):
                moveline.qty_done = moveline.product_uom_qty
            moves._action_done()

    def do_handle(self):
        self.write({"state": "handle"})

    def do_oncheck(self):
        self.write({"state": "oncheck"})

    def do_service(self):
        self.write({"state": "service"})

    def do_done(self):
        self.write({"state": "done"})

    def do_undone(self):
        self.write({"state": "undone"})

    def do_close(self):
        self.process_stock_move()
        self.filtered(lambda rec: rec.maintenance_type == "cal").create_reminder()
        self.write({"state": "closed"})
    
    @api.model_create_multi
    def create(self, vals):
        for _val in vals:
            if _val.get("name", _("Draft")) == "Draft":
                _val["name"] = self.env["ir.sequence"].next_by_code(self._name)
        return super(Equip3MaintancenService, self).create(vals)

    def create_reminder(self):
        pass
