from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime, date, timedelta
import pytz


class Equip3SaleService(models.Model):
    _name = "sale.service"
    _inherit = "mail.thread"

    _description = "Sale Service"

    name = fields.Char(string="Name", default="Draft", readonly=True, copy=False)
    partner_id = fields.Many2one(comodel_name="res.partner", string="Customer")
    facility_area = fields.Many2one(
        comodel_name="aftersale.facility.area", string="Facility Area"
    )
    maintenance_team_id = fields.Many2one(
        comodel_name="aftersale.maintenance.team", string="Maintenance Team"
    )
    warranty = fields.Boolean(string="Warranty")
    maintenance_type = fields.Selection(
        selection=[
            ("cal", _("Calibration")),
            ("repair", _("Repair")),
            ("service", _("Service")),
            ("other", _("Other")),
        ],
        string="Maintenance Type",
    )

    reference = fields.Char(string="Reference", readonly=True)
    scheduled_date = fields.Date(string="Scheduled Date")
    end_date = fields.Date(string="End Date")
    company_id = fields.Many2one(
        comodel_name="res.company",
        string="Company",
        default=lambda self: self.env.user.company_id,
    )
    branch_id = fields.Many2one(comodel_name="res.branch", string="Branch")
    remarks = fields.Text(string="Remarks")
    discount_type = fields.Selection(
        selection=[("global", _("Global")), ("line", _("Line"))],
        string="Discount Type",
        default="global",
    )
    line_ids = fields.One2many(
        comodel_name="sale.service.line",
        inverse_name="order_id",
        string="Order Products Line",
    )
    line_material_ids = fields.One2many(
        comodel_name="sale.service.line",
        inverse_name="order_material_id",
        string="Order Material Line",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        string="Currency",
        default=lambda self: self.env.user.company_id.currency_id,
    )
    amount_total = fields.Monetary(
        string="Total", compute="_compute_amount", store=True
    )
    amount_untaxed = fields.Monetary(
        string="Untaxed Amount", compute="_compute_amount", store=True
    )
    amount_tax = fields.Monetary(string="Tax", compute="_compute_amount", store=True)
    amount_total_material = fields.Monetary(
        string="Total", compute="_compute_amount", store=True
    )
    amount_untaxed_material = fields.Monetary(
        string="Untaxed Amount", compute="_compute_amount", store=True
    )
    amount_tax_material = fields.Monetary(
        string="Tax", compute="_compute_amount", store=True
    )
    grand_amount_total = fields.Monetary(
        string="Grand Total", compute="_compute_amount", store=True
    )
    grand_amount_untaxed = fields.Monetary(
        string="Grand Untaxed Total", compute="_compute_amount", store=True
    )
    grand_amount_taxed = fields.Monetary(
        string="Grand Amount Tax", compute="_compute_amount", store=True
    )
    down_payment_amount = fields.Monetary(
        string="Down Payment", compute="_compute_amount", store=True
    )
    terms_condition_id = fields.Many2one(
        comodel_name="sale.terms.and.conditions", string="Terms and Conditions"
    )
    note = fields.Text("Note")
    state = fields.Selection(
        [
            ("draft", _("Draft")),
            ("waiting", _("Waiting Approval")),
            ("pending", _("Pending Payment")),
            ("sale", _("Sales Service")),
            ("rejected", _("Rejected")),
        ],
        default="draft",
        string="State",
    )
    pricelist_id = fields.Many2one(
        comodel_name="product.pricelist",
        string=_("Pricelist"),
        domain=[("sale_order_type", "=", "service")],
    )
    location_id = fields.Many2one("stock.location", string=_("Material Location"))
    delivery_type = fields.Selection(
        selection=[
            ("delivery_before_payment", "Delivery Before Payment"),
            ("delivery_after_payment", "Delivery After Payment"),
        ],
        string="Delivery Type",
        default="delivery_before_payment",
        required=True
    )
    invoice_ids = fields.Many2many(
        "account.move",
        "account_move_service_rel",
        "service_id",
        "move_id",
        string=_("Invoices"),
    )
    invoice_paid = fields.Boolean(compute="compute_invoice", store=True)
    invoice_count = fields.Integer(compute="compute_invoice", store=True)
    purchase_ids = fields.Many2many(
        "purchase.order",
        "purchase_order_service_rel",
        "purchase_id",
        "service_id",
        string=_("Purchases"),
    )
    purchase_count = fields.Integer(compute="compute_purchases")
    condition_beforehanded = fields.Text(string="Condition Before Handed")
    task_performance = fields.Text(string="Task Performance")
    followup = fields.Text(string="Followup Action and Note")
    maintenance_service_id = fields.Many2one(
        comodel_name="maintenance.service", string="Maintenance Service"
    )
    maintenance_state = fields.Selection(related="maintenance_service_id.state")
    display_create_invoice = fields.Boolean(compute="_onchange_delivery_type")
    approval_matrix_id = fields.Many2one(
        comodel_name="sale.service.approval.matrix",
        compute="_compute_aproval_matrix",
        string="Approval Matrix",
    )
    approved_matrix_ids = fields.One2many(
        "sale.service.approval.matrix.line", "sale_service_id", string="Approved Matrix"
    )
    approval_matrix_line_id = fields.Many2one(
        "sale.service.approval.matrix.line",
        string="Approval Matrix Line",
        compute="_get_approve_button",
        store=False,
        readonly=True,
    )
    is_approve_button = fields.Boolean(
        string="Is Approve Button", compute="_get_approve_button", store=False
    )

    is_previous_approved = fields.Boolean(
        string="Is Previous Approved", compute="_check_previous_approver"
    )
    
    @api.depends("approved_matrix_ids")
    def _check_previous_approver(self):
        count_approver = len(self.approved_matrix_ids)
        if count_approver ==  1:
            self.is_previous_approved = True
        else:
            count_approved = len(self.approved_matrix_ids.filtered(lambda r: r.approved))
            if count_approved == 0:
                if self.approved_matrix_ids:
                    check_first_approver = self.approved_matrix_ids[0].user_ids.ids
                else:
                    check_first_approver = None 

                if check_first_approver is not None and self.env.user.id in check_first_approver:
                    self.is_previous_approved = True
                else:
                    self.is_previous_approved = False
            else :
                check_previous_approver = self.approved_matrix_ids[count_approved - 1].approved
                if count_approved < len(self.approved_matrix_ids):
                    check_next_approver = self.approved_matrix_ids[count_approved].user_ids.ids
                else:
                    check_next_approver = None 

                if check_next_approver is not None and self.env.user.id in check_next_approver and check_previous_approver:
                    self.is_previous_approved = True
                else:
                    self.is_previous_approved = False
 



    def _get_sale_service_approval_matrix_setting(self):
        sale_service_approval_matrix_config = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("equip3_aftersales_operation.sale_service_approval_matrix")
        )

        return sale_service_approval_matrix_config

    is_sale_service_approval_matrix = fields.Boolean(
        string="Is Sale Service Approval Matrixd",
        default=_get_sale_service_approval_matrix_setting,
    )

    def _get_approve_button(self):
        for record in self:
            matrix_line = sorted(
                record.approved_matrix_ids.filtered(lambda r: not r.approved),
                key=lambda r: r.sequence,
            )
            if len(matrix_line) == 0:
                record.is_approve_button = False
                record.approval_matrix_line_id = False
            elif len(matrix_line) > 0:
                matrix_line_id = matrix_line[0]
                if (
                    self.env.user.id in matrix_line_id.user_ids.ids
                    and self.env.user.id != matrix_line_id.last_approved.id
                ):
                    record.is_approve_button = True
                    record.approval_matrix_line_id = matrix_line_id.id
                else:
                    record.is_approve_button = False
                    record.approval_matrix_line_id = False

    @api.depends("company_id", "branch_id")
    def _compute_aproval_matrix(self):
        if self.company_id and self.branch_id:
            approval_matrix = self.env["sale.service.approval.matrix"].search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("branch_id", "=", self.branch_id.id),
                ],
                order="create_date DESC",
                limit=1,
            )
            self.approval_matrix_id = approval_matrix.id
        else:
            self.approval_matrix_id = False

    @api.onchange("approval_matrix_id")
    def _compute_approving_matrix_lines(self):
        data = [(5, 0, 0)]
        for record in self:
            if record.state == "draft" and record.is_sale_service_approval_matrix:
                record.approved_matrix_ids = []
                counter = 1
                record.approved_matrix_ids = []
                for rec in record.approval_matrix_id:
                    for line in rec.approval_matrix_ids:
                        data.append(
                            (
                                0,
                                0,
                                {
                                    "sequence": counter,
                                    "user_ids": [(6, 0, line.user_ids.ids)],
                                    "minimum_approver": line.minimum_approver,
                                },
                            )
                        )
                        counter += 1
                record.approved_matrix_ids = data

    @api.depends("delivery_type")
    def _onchange_delivery_type(self):
        if self.delivery_type == "delivery_after_payment" and self.state in [
            "waiting",
            "pending",
        ]:
            self.display_create_invoice = True
        elif self.delivery_type == "delivery_before_payment" and self.state in [
            "waiting",
            "pending",
            "sale",
        ]:
            self.display_create_invoice = True
        else:
            self.display_create_invoice = False

    @api.onchange("partner_id")
    def partner_id_change(self):
        self.delivery_type = self.partner_id.delivery_type

    def create_purchase(self):
        context = self._context.copy()
        view = self.env.ref(
            "equip3_aftersales_operation.make_purchase_wizard_form_view"
        )
        return {
            "name": "Create Purchase Order",
            "type": "ir.actions.act_window",
            "view_mode": "form",
            "res_model": "make.purchase.order.wizard",
            "views": [(view.id, "form")],
            "view_id": view.id,
            "target": "new",
            "context": context,
        }

    def show_invoices(self):
        invoices = self.mapped("invoice_ids")
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account.action_move_out_invoice_type"
        )
        if len(invoices) > 1:
            action["domain"] = [("id", "in", invoices.ids)]
        elif len(invoices) == 1:
            form_view = [(self.env.ref("account.view_move_form").id, "form")]
            if "views" in action:
                action["views"] = form_view + [
                    (state, view) for state, view in action["views"] if view != "form"
                ]
            else:
                action["views"] = form_view
            action["res_id"] = invoices.id
        else:
            action = {"type": "ir.actions.act_window_close"}

        context = {
            "default_move_type": "out_invoice",
        }
        if len(self) == 1:
            context.update(
                {
                    "default_partner_id": self.partner_id.id,
                    "default_partner_shipping_id": self.partner_id.id,
                    "default_invoice_origin": self.mapped("name"),
                    "default_user_id": self.env.user.id,
                }
            )
        action["context"] = context
        return action

    def show_purchases(self):
        self.ensure_one()
        action = {
            "res_model": "purchase.order",
            "type": "ir.actions.act_window",
            "name": _("Purchase Order generated from %s", self.name),
            "domain": [("id", "in", self.purchase_ids.ids)],
            "view_mode": "tree,form",
        }

        return action

    def compute_purchases(self):
        for rec in self:
            rec.purchase_count = len(rec.purchase_ids)

    @api.depends("invoice_ids", "invoice_ids.payment_state")
    def compute_invoice(self):
        for rec in self:
            rec.invoice_count = len(rec.invoice_ids)
            rec.invoice_paid = (
                rec.invoice_ids
                and all([inv.payment_state == "paid" for inv in rec.invoice_ids])
                or False
            )

            partially_paid = False
            fully_paid = False

            if rec.invoice_ids:
                sum_of_invoice_paid = 0
                for invoice_id in rec.invoice_ids.filtered(lambda inv: inv.state not in ['cancel', 'draft']):
                    if invoice_id.payment_state == 'paid':
                        sum_of_invoice_paid += 1
                if sum_of_invoice_paid != 0:
                    if sum_of_invoice_paid < len(rec.line_ids):
                        partially_paid = True
                    else:
                        fully_paid = True
            
            if fully_paid:
                rec.invoice_paid = True
                if self._name == "sale.service":
                    rec.state = "sale"
                    _vals = rec._prepare_maintenance_vals()
                    rec.maintenance_service_id = self.env["maintenance.service"].create(_vals)

    @api.onchange("pricelist_id")
    def pricelist_id_change(self):
        if self.pricelist_id:
            self.currency_id = self.pricelist_id.currency_id
        for line in self.line_ids | self.line_material_ids:
            line.product_qty_change()

    @api.onchange("facility_area")
    def facility_area_change(self):
        if self.facility_area:
            self.branch_id = self.facility_area.branch_id

    @api.onchange("branch_id", "facility_area")
    def branch_facility_change(self):
        if not self.branch_id:
            self.location_id = False
        elif self.facility_area:
            self.location_id = self.facility_area.location_id

    def request_aproval(self):
        self.write(
            {
                "state": "waiting",
                "name": self.env["ir.sequence"].next_by_code("sale.service")
                or _("New"),
            }
        )

    def action_approve(self):
        for record in self:
            user = self.env.user
            if record.is_approve_button and record.approval_matrix_line_id:
                approval_matrix_line_id = record.approval_matrix_line_id
                if (
                    user.id in approval_matrix_line_id.user_ids.ids
                    and user.id not in approval_matrix_line_id.approved_users.ids
                ):
                    name = approval_matrix_line_id.state_char or ""
                    utc_datetime = datetime.now()
                    local_timezone = pytz.timezone(self.env.user.tz)
                    local_datetime = utc_datetime.replace(tzinfo=pytz.utc)
                    local_datetime = local_datetime.astimezone(local_timezone).strftime(
                        DEFAULT_SERVER_DATETIME_FORMAT
                    )
                    if name != "":
                        name += "\n • %s: Approved - %s" % (
                            self.env.user.name,
                            local_datetime,
                        )
                    else:
                        name += "• %s: Approved - %s" % (
                            self.env.user.name,
                            local_datetime,
                        )

                    approval_matrix_line_id.write(
                        {
                            "last_approved": self.env.user.id,
                            "state_char": name,
                            "approved_users": [(4, user.id)],
                        }
                    )
                    if approval_matrix_line_id.minimum_approver == len(
                        approval_matrix_line_id.approved_users.ids
                    ):
                        approval_matrix_line_id.write(
                            {"time_stamp": datetime.now(), "approved": True}
                        )

            if len(record.approved_matrix_ids) == len(
                record.approved_matrix_ids.filtered(lambda r: r.approved)
            ):
                record._create_maintenance()

    def action_reject(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Sale Service Reject",
            "res_model": "sale.service.matrix.reject",
            "view_type": "form",
            "view_mode": "form",
            "target": "new",
        }

    def _prepare_maintenance_vals(self):
        self.ensure_one
        _vals = self.copy_data()[0]
        _vals["line_ids"] = [(0, 0, l.copy_data()[0]) for l in self.line_ids]
        _vals["line_material_ids"] = [
            (0, 0, l.copy_data()[0]) for l in self.line_material_ids
        ]
        _vals["reference"] = self.name
        return _vals

    def action_confirm(self):
        self.write(
            {
                "name": self.env["ir.sequence"].next_by_code("sale.service")
                or _("New"),
            }
        )
        self._create_maintenance()

    def _create_maintenance(self):
        for rec in self:
            if rec.maintenance_type == "other":
                continue
            if rec.is_sale_service_approval_matrix:
                if rec.delivery_type == "delivery_before_payment":
                    rec.state = "sale"
                elif (
                    rec.delivery_type == "delivery_after_payment"
                    or not rec.delivery_type
                ):
                    rec.state = "pending"

                # if (
                #     rec.delivery_type == "delivery_after_payment"
                #     and not rec.invoice_paid
                # ):
                #     raise ValidationError(
                #         _(
                #             "This service cannot be processed due to outstanding payment!"
                #         )
                #     )
            else:
                if rec.delivery_type == "delivery_after_payment":
                    rec.state = "pending"
                elif (
                    rec.delivery_type == "delivery_before_payment"
                    or not rec.delivery_type
                ):
                    rec.state = "sale"

            if rec.state == "sale":
                _vals = rec._prepare_maintenance_vals()
                rec.maintenance_service_id = self.env["maintenance.service"].create(_vals)

    @api.onchange("terms_condition_id")
    def terms_condition_id_change(self):
        if self.terms_condition_id:
            self.note = self.terms_condition_id.terms_and_conditions

    @api.depends(
        "line_ids",
        "line_material_ids",
        "line_ids.amount_total",
        "line_material_ids.amount_total",
        "line_ids.amount_untaxed",
        "line_material_ids.amount_untaxed",
    )
    def _compute_amount(self):
        for rec in self:
            amount_total = sum(
                rec.line_ids.filtered(lambda l: not l.is_downpayment).mapped(
                    "amount_total"
                )
            )
            amount_untaxed = sum(
                rec.line_ids.filtered(lambda l: not l.is_downpayment).mapped(
                    "amount_untaxed"
                )
            )
            amount_tax = amount_total - amount_untaxed

            amount_total_material = sum(
                rec.line_material_ids.filtered(lambda l: not l.is_downpayment).mapped(
                    "amount_total"
                )
            )
            amount_untaxed_material = sum(
                rec.line_material_ids.filtered(lambda l: not l.is_downpayment).mapped(
                    "amount_untaxed"
                )
            )
            amount_tax_material = amount_total_material - amount_untaxed_material
            down_payment_amount = sum(
                rec.line_ids.filtered(lambda l: l.is_downpayment).mapped("amount_total")
            )
            shadow_down_payment = down_payment_amount * -1
            grand_amount_total = (
                amount_total + amount_total_material + shadow_down_payment
            )  # FIXME: grand total deduct downpayment? NO
            grand_amount_untaxed = amount_untaxed + amount_untaxed_material
            grand_amount_taxed = amount_tax + amount_tax_material

            rec.amount_total = amount_total
            rec.amount_untaxed = amount_untaxed
            rec.amount_tax = amount_tax
            rec.amount_total_material = amount_total_material
            rec.amount_untaxed_material = amount_untaxed_material
            rec.amount_tax_material = amount_tax_material

            rec.down_payment_amount = down_payment_amount
            rec.grand_amount_total = grand_amount_total
            rec.grand_amount_untaxed = grand_amount_untaxed
            rec.grand_amount_taxed = grand_amount_taxed

    def get_invoiceable_lines(self):
        self.ensure_one()
        return self.line_ids.filtered(
            lambda l: not l.is_downpayment and l.invoiced_qty < l.product_qty
        ) | self.line_material_ids.filtered(
            lambda l: not l.is_downpayment
            and l.invoiced_qty < l.product_qty
            and l.chargable
        )

    def button_create_invoice(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id(
            "sale.action_view_sale_advance_payment_inv"
        )
        action["context"] = {"active_ids": self.ids}
        return action

    def _create_invoices(self, final):
        for rec in self:
            invoiceable_lines = rec.get_invoiceable_lines()
            if not invoiceable_lines:
                raise ValidationError(_("This Sale Service has no invoiceable lines."))
            invoiceVals = rec._perpare_invoice_vals()
            invoiceVals["invoice_line_ids"] = rec._prepare_invoice_line_vals(final)

            rec.invoice_ids |= (
                self.env["account.move"]
                .sudo()
                .create([invoiceVals])
                .with_user(self.env.uid)
            )

    def _perpare_invoice_vals(self):
        self.ensure_one()
        journal = (
            self.env["account.move"]
            .with_context(default_move_type="out_invoice")
            ._get_default_journal()
        )
        if not journal:
            raise UserError(
                _("Please define an accounting sales journal for the company %s (%s).")
                % (self.company_id.name, self.company_id.id)
            )
        service = self
        fiscal_position_id = self.env["account.fiscal.position"].get_fiscal_position(
            service.partner_id.id
        )
        invoice_vals = {
            "ref": service.name,
            "move_type": "out_invoice",
            "invoice_origin": service.name,
            "invoice_user_id": service.create_uid.id,
            "narration": service.followup,
            "partner_id": service.partner_id.id,
            "fiscal_position_id": fiscal_position_id.id,
            "partner_shipping_id": service.partner_id.id,
            "currency_id": service.pricelist_id.currency_id.id,
            "partner_bank_id": service.company_id.partner_id.bank_ids[:1].id,
        }
        return invoice_vals

    def _prepare_invoice_line_vals(self, final):
        self.ensure_one()
        if not final:
            raise ValidationError(
                _(
                    "Only final invoice is supported for now, please select `Deduct Down Payment` option"
                )
            )
        ilVals = []
        ilVals.append((0, 0, self._prepare_il_section(_("Products"))))
        for prodline in self.line_ids.filtered(
            lambda l: not l.is_downpayment
            and l.invoiced_qty < l.product_qty
            and l.chargable
        ):
            ilVals.append((0, 0, prodline._prepare_il_vals()))
        if self.line_material_ids.filtered(
            lambda l: l.invoiced_qty < l.product_qty and l.chargable
        ):
            ilVals.append((0, 0, self._prepare_il_section(_("Material"))))
        for matline in self.line_material_ids.filtered(
            lambda l: l.invoiced_qty < l.product_qty and l.chargable
        ):
            ilVals.append((0, 0, matline._prepare_il_vals()))
        dplines = self.line_ids.filtered(lambda l: l.is_downpayment)
        if dplines:
            ilVals.append((0, 0, self._prepare_il_section(_("Down Payments"))))
        for dpline in dplines:
            ilVals.append((0, 0, dpline._prepare_il_vals()))
        return ilVals

    @api.model
    def _prepare_il_section(self, name):
        return {
            "display_type": "line_section",
            "name": name,
            "product_id": False,
            "product_uom_id": False,
            "quantity": 0,
            "discount": 0,
            "price_unit": 0,
            "account_id": False,
        }


class Equip3SaleServiceLine(models.Model):
    _name = "sale.service.line"
    _description = "Sale Service Line"

    line_type = fields.Selection(
        [("product", _("Product")), ("material", _("Material"))], string=_("Type")
    )

    order_id = fields.Many2one(comodel_name="sale.service", string="Order", copy=False)
    order_material_id = fields.Many2one(
        comodel_name="sale.service", string="Order", copy=False
    )
    name = fields.Char(string="Description")
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    analytic_tag_ids = fields.Many2many(
        comodel_name="account.analytic.tag", string=_("Analytic Group")
    )
    disc_method = fields.Selection(
        [("fixed", _("Fixed")), ("per", _("Percentage"))], string="Discount Method"
    )
    disc_percentage = fields.Float(string="Discount Percentage")
    disc_amount = fields.Float(string="Discount Amount")
    product_qty = fields.Float(string="Quantity")
    related_product_categ = fields.Many2one(related="product_id.uom_id.category_id")
    product_uom = fields.Many2one(comodel_name="uom.uom", string="Unit of Measure")
    price_unit = fields.Float(string="Price Unit")
    tax_ids = fields.Many2many(comodel_name="account.tax", string="Taxes")
    amount_untaxed = fields.Float(
        string="Untaxed Amount", compute="_compute_amount", store=True
    )
    amount_total = fields.Float(
        string="Total Amount", compute="_compute_amount", store=True
    )
    invoiced_qty = fields.Float(
        string="Invoiced Quantity", compute="compute_invoiced_qty", store=True
    )
    chargable = fields.Boolean(string="Chargable", default=True)
    is_downpayment = fields.Boolean()
    sale_service_line_ids = fields.Many2many(
        "account.move.line",
        "account_move_line_serviceline_rel",
        "serviceline_id",
        "moveline_id",
    )
    maintenance_id = fields.Many2one(
        "maintenance.service", _("Maintenance"), copy=False
    )
    maintenance_material_id = fields.Many2one(
        "maintenance.service", _("Maintenance"), copy=False
    )

    @api.depends("sale_service_line_ids", "sale_service_line_ids.move_id.state")
    def compute_invoiced_qty(self):
        for rec in self:
            rec.invoiced_qty = sum(
                rec.sale_service_line_ids.filtered(
                    lambda ml: ml.move_id.state != "cancel"
                ).mapped("quantity")
            )

    @api.onchange(
        "disc_method", "product_qty", "price_unit", "disc_amount", "disc_percentage"
    )
    def disc_change(self):
        if self.product_qty == 0.0 or self.price_unit == 0.0 or not self.disc_method:
            return
        if self.disc_method == "per":
            self.disc_amount = (
                self.disc_percentage / 100 * self.price_unit * self.product_qty
            )
        else:
            self.disc_percentage = (
                100 * self.disc_amount / (self.price_unit * self.product_qty)
            )

    @api.onchange("product_id")
    def product_id_change(self):
        self.name = self.product_id.display_name
        self.product_uom = self.product_id.uom_id
        self.tax_ids = self.product_id.taxes_id
        self.product_qty_change()

    def _prepare_il_vals(self):
        quantity = (
            -1 * self.product_qty
            if self.is_downpayment
            else (self.product_qty - self.invoiced_qty)
        )
        return {
            "name": self.product_id.display_name,
            "price_unit": self.price_unit,
            "quantity": quantity,  # FIXME: should consider UoM difference
            "discount_method": (
                "fix" if self.disc_method == "fixed" else self.disc_method
            ),
            "discount_amount": (
                self.disc_amount
                if self.disc_method == "fixed"
                else self.disc_percentage
            ),
            "product_id": self.product_id.id,
            "product_uom_id": self.product_uom.id,
            "tax_ids": [(6, 0, self.tax_ids.ids)],
            "sale_service_line_ids": [(6, 0, [self.id])],
            "analytic_tag_ids": [(6, 0, self.analytic_tag_ids.ids)],
            "analytic_account_id": False,
            "account_id": self.product_id.categ_id.property_account_income_categ_id.id,
        }

    def get_model_m2o(self):
        service = self.order_id | self.order_material_id
        return service and service[0] or service

    @api.onchange("product_uom", "product_qty")
    def product_qty_change(self):
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        service = self.get_model_m2o()
        if service.pricelist_id and service.partner_id:
            product_context = dict(
                self.env.context,
                partner_id=service.partner_id.id,
                date=service.create_date
                and service.create_date.today()
                or fields.Date.today(),
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get("fiscal_position"),
            )

            price, rule_id = service.pricelist_id.with_context(
                product_context
            ).get_product_price_rule(
                self.product_id, self.product_qty or 1.0, service.partner_id
            )
            self.price_unit = price

    @api.depends(
        "order_id.discount_type",
        "order_material_id.discount_type",
        "price_unit",
        "tax_ids",
        "product_qty",
        "disc_amount",
    )
    def _compute_amount(self):
        for rec in self:
            _amount = rec.price_unit * rec.product_qty - rec.disc_amount
            service = rec.get_model_m2o()
            taxes = self.tax_ids.compute_all(
                _amount, service.pricelist_id.currency_id, 1.0, product=rec.product_id
            )
            rec.amount_untaxed = taxes["total_excluded"]
            rec.amount_total = taxes["total_included"]
