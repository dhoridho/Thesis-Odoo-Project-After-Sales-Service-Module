from odoo import api, fields, models, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    delivery_type_id = fields.Many2one("delivery.type.sale", string="Delivery Type")
    delivery_type = fields.Selection(
        [
            ("delivery_before_payment", "Delivery Before Payment"),
            ("delivery_after_payment", "Delivery After Payment"),
        ],
        string="Delivery Type",
    )
    npwp = fields.Char("NPWP", related="partner_id.vat", store=True)
    attachment_type = fields.Selection(
        [
            ("url", "URL"),
            ("file", "File"),
        ],
        string="Type",
    )
    file = fields.Binary("File")
    url = fields.Char("URL")
    inden = fields.Boolean("Inden")
    po_customer = fields.Char("PO Customer")
    # pricelist_id = fields.Many2one(
    #     domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('sale_order_type','=','order')]"
    # )
    is_partner_hs_code = fields.Boolean("Partner HS Code")

    @api.onchange("partner_id")
    def _onchange_partner_id(self):
        for rec in self:
            if rec.partner_id and rec.partner_id.delivery_type:
                rec.delivery_type = rec.partner_id.delivery_type

    @api.depends(
        "amount_total",
        "margin_percent",
        "discount_amt",
        "discount_amt_line",
        "branch_id",
    )
    def _compute_approving_customer_matrix(self):
        IrConfigParam = self.env["ir.config_parameter"].sudo()
        is_total_amount = IrConfigParam.get_param("is_total_amount", False)
        is_margin_amount = IrConfigParam.get_param("is_margin_amount", False)
        is_discount_amount = IrConfigParam.get_param("is_discount_amount", False)
        is_segmentation = IrConfigParam.get_param("is_segmentation", False)
        total_sequence = IrConfigParam.get_param("total_sequence", 0)
        margin_sequence = IrConfigParam.get_param("margin_sequence", 0)
        discount_sequence = IrConfigParam.get_param("discount_sequence", 0)
        segmentation_sequence = IrConfigParam.get_param("segmentation_sequence", 0)

        data = []
        if is_total_amount:
            data.insert(int(total_sequence) - 1, "total_amt")
        if is_margin_amount:
            data.insert(int(margin_sequence) - 1, "pargin_per")
        if is_discount_amount:
            data.insert(int(discount_sequence) - 1, "discount_amt")
        if is_segmentation:
            data.insert(int(segmentation_sequence) - 1, "segmentation")

        for record in self:
            matrix_ids = []
            if record.is_customer_approval_matrix:
                record.approving_matrix_sale_id = False
                for sale_matrix_config in data:
                    if sale_matrix_config == "total_amt":
                        matrix_id = self.env["approval.matrix.sale.order"].search(
                            [
                                ("config", "=", "total_amt"),
                                ("minimum_amt", "<=", record.amount_total),
                                ("maximum_amt", ">=", record.amount_total),
                                ("company_id", "=", record.company_id.id),
                                ("branch_id", "=", record.branch_id.id),
                            ],
                            limit=1,
                        )
                        if matrix_id:
                            matrix_ids.append(matrix_id.id)
                    elif sale_matrix_config == "pargin_per":
                        matrix_id = self.env["approval.matrix.sale.order"].search(
                            [
                                ("config", "=", "pargin_per"),
                                ("minimum_amt", "<=", record.margin_percent * 100),
                                ("maximum_amt", ">=", record.margin_percent * 100),
                                ("company_id", "=", record.company_id.id),
                                ("branch_id", "=", record.branch_id.id),
                            ],
                            limit=1,
                        )
                        if matrix_id:
                            matrix_ids.append(matrix_id.id)
                    elif sale_matrix_config == "discount_amt":
                        if record.discount_type == "line":
                            matrix_id = self.env["approval.matrix.sale.order"].search(
                                [
                                    ("config", "=", "discount_amt"),
                                    ("minimum_amt", "<=", record.discount_amt_line),
                                    ("maximum_amt", ">=", record.discount_amt_line),
                                    ("company_id", "=", record.company_id.id),
                                    ("branch_id", "=", record.branch_id.id),
                                ],
                                limit=1,
                            )
                            if matrix_id:
                                matrix_ids.append(matrix_id.id)
                        else:
                            matrix_id = self.env["approval.matrix.sale.order"].search(
                                [
                                    ("config", "=", "discount_amt"),
                                    ("minimum_amt", "<=", record.discount_amt),
                                    ("maximum_amt", ">=", record.discount_amt),
                                    ("company_id", "=", record.company_id.id),
                                    ("branch_id", "=", record.branch_id.id),
                                ],
                                limit=1,
                            )
                            if matrix_id:
                                matrix_ids.append(matrix_id.id)
                    elif sale_matrix_config == "segmentation":
                        matrix_id = self.env["approval.matrix.sale.order"].search(
                            [
                                ("config", "=", "segmentation"),
                                ("company_id", "=", record.company_id.id),
                                (
                                    "customer_segmentation_id",
                                    "=",
                                    record.partner_id.customer_segmentation_id.id,
                                ),
                                ("branch_id", "=", record.branch_id.id),
                            ],
                            limit=1,
                        )
                        if matrix_id:
                            matrix_ids.append(matrix_id.id)
                record.approving_matrix_sale_id = [(6, 0, matrix_ids)]
            else:
                record.approving_matrix_sale_id = False


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    brand_ids = fields.Many2many(
        "product.brand", related="product_template_id.brand_ids"
    )

    @api.depends(
        "qty_invoiced",
        "qty_delivered",
        "product_uom_qty",
        "order_id.state",
        "order_id.delivery_type",
    )
    def _get_to_invoice_qty(self):
        for line in self:
            if line.order_id.state in ["sale", "done"]:
                if line.order_id.delivery_type:
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
                else:
                    pass
                    # this is not supported and does not follow the bussiness flow of the client
                    line.qty_to_invoice = line.product_uom_qty - line.qty_invoiced
            else:
                line.qty_to_invoice = 0
