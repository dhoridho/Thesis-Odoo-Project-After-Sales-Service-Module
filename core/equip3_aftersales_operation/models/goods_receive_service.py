from odoo import models, api, fields, _
from odoo.exceptions import ValidationError


class Equip3GoodsReceiveService(models.Model):
    _name = "goods.receive.service"
    _description = "Goods Receive Service"

    name = fields.Char(string="Name", default="Draft", readonly=True)
    request_date = fields.Date(string="Request Date")
    request_by = fields.Many2one(comodel_name="res.users", string="Request By")
    partner_id = fields.Many2one(comodel_name="res.partner", string="Customer")
    facility_area = fields.Many2one(comodel_name="aftersale.facility.area", string="Facility Area")
    description = fields.Text(string="Description")
    line_ids = fields.One2many(
        comodel_name="goods.receive.service.line", inverse_name="goods_receive_id", string="Products"
    )
    line_checklist_ids = fields.One2many(
        comodel_name="goods.receive.service.line", inverse_name="goods_receive_checklist_id", string="Products"
    )
    state = fields.Selection(
        [("draft", _("Draft")), ("confirm", _("Confirmed"))],
        string=_("Status"),
        default="draft",
    )
    is_confirmed = fields.Boolean('Is Confirmed')

    def _prepare_sale_service(self):
        self.ensure_one()
        return {
            "facility_area": self.facility_area.id,
            "partner_id": self.partner_id.id,
            "reference": self.name,
            "delivery_type": self.partner_id.delivery_type,
            "line_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": l.product_id.id,
                        "product_qty": l.product_qty,
                        "product_uom": l.product_uom.id,
                    },
                )
                for l in self.line_ids.filtered(lambda l: l.toservice)
            ],
            "line_material_ids": [
                (
                    0,
                    0,
                    {
                        "product_id": l.product_id.id,
                        "product_qty": l.product_qty,
                        "product_uom": l.product_uom.id,
                    },
                )
                for l in self.line_checklist_ids.filtered(lambda l: l.toservice)
            ],
        }

    def button_confirm(self):
        for rec in self:
            if rec.line_ids:
                checked = rec.line_ids.filtered(lambda line: line.toservice and line.product_qty < 1)
                if checked:
                    raise ValidationError("You need to add and checklist at least one product")
            else:
                raise ValidationError("You need to add and checklist at least one product")
            
            rec.write({
                "state": "confirm",
                "name": self.env['ir.sequence']. next_by_code('goods.receive.service') or _('New'),
                "is_confirmed": True
            })
            # create sale sercvice
            vals = rec._prepare_sale_service()
            self.env["sale.service"].create(vals)


class Equip3GoodsReceiveServiceLine(models.Model):
    _name = "goods.receive.service.line"
    _description = "Goods Receive Service Line"
    _rec_name = "product_id"

    toservice = fields.Boolean()
    goods_receive_id = fields.Many2one(comodel_name="goods.receive.service", string="Goods Receive Service")
    goods_receive_checklist_id = fields.Many2one(
        comodel_name="goods.receive.service", string="Goods Receive Service"
    )
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    product_qty = fields.Float(string="Product Qty")
    product_uom = fields.Many2one(comodel_name="uom.uom", string="Unit of Measure")
    prod_categ_id = fields.Many2one(related="product_id.uom_id.category_id")
    note = fields.Text(string="Note")

    @api.onchange("product_id")
    def product_id_change(self):
        self.product_uom = self.product_id.uom_id
