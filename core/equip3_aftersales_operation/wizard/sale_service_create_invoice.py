import time

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"
    _description = "Sales Advance Payment Invoice"

    @api.model
    def _default_invoicing_timesheet_enabled(self):
        if self._context.get("active_model") == "sale.service":
            return False
        return super(SaleAdvancePaymentInv, self)._default_invoicing_timesheet_enabled()

    invoicing_timesheet_enabled = fields.Boolean(
        default=_default_invoicing_timesheet_enabled
    )

    @api.model
    def _default_has_down_payment(self):
        if self._context.get("active_model") != "sale.service":
            return super(SaleAdvancePaymentInv, self)._default_has_down_payment()

        if self._context.get("active_model") == "sale.service" and self._context.get(
            "active_id", False
        ):
            sale_service = self.env["sale.service"].browse(
                self._context.get("active_id")
            )
            return sale_service.line_ids.filtered(lambda l: l.is_downpayment)
        return False

    has_down_payments = fields.Boolean(default=_default_has_down_payment)

    @api.model
    def _default_currency_id(self):
        if self._context.get("active_model") != "sale.service":
            return super(SaleAdvancePaymentInv, self)._default_currency_id()

        if self._context.get("active_model") == "sale.service" and self._context.get(
            "active_id", False
        ):
            sale_service = self.env["sale.service"].browse(
                self._context.get("active_id")
            )
            return sale_service.currency_id

    currency_id = fields.Many2one(default=_default_currency_id)

    def _get_fiscal_pos(self, partner):
        return self.env["account.fiscal.position"].get_fiscal_position(partner.id)

    def _prepare_invoice_values_service(self, service, name, amount, service_line):
        fiscal_position = self._get_fiscal_pos(service.partner_id)

        return {
            "ref": service.name,
            "move_type": "out_invoice",
            "invoice_origin": service.name,
            "invoice_user_id": service.create_uid.id,
            "narration": service.followup,
            "partner_id": service.partner_id.id,
            "fiscal_position_id": fiscal_position.id,
            "partner_shipping_id": service.partner_id.id,
            "currency_id": service.pricelist_id.currency_id.id,
            "partner_bank_id": service.company_id.partner_id.bank_ids[:1].id,
            "invoice_line_ids": [
                (
                    0,
                    0,
                    {
                        "name": name,
                        "price_unit": amount,
                        "quantity": 1.0,
                        "product_id": self.product_id.id,
                        "account_id": self.product_id.categ_id.property_account_income_categ_id.id,
                        "product_uom_id": service_line.product_uom.id,
                        "tax_ids": [(6, 0, service_line.tax_ids.ids)],
                        "sale_service_line_ids": [(6, 0, [service_line.id])],
                        "analytic_tag_ids": [(6, 0, service_line.analytic_tag_ids.ids)],
                        "analytic_account_id": False,
                    },
                )
            ],
        }

    def _get_advance_details_service(self, service):

        context = {"lang": service.partner_id.lang}
        if self.advance_payment_method == "percentage":
            if all(self.product_id.taxes_id.mapped("price_include")):
                amount = service.amount_total * self.amount / 100
            else:
                amount = service.amount_untaxed * self.amount / 100
            name = _("Down payment of %s%%") % (self.amount)
        else:
            amount = self.fixed_amount
            name = _("Down Payment")
        del context

        return amount, name

    def _create_dp_invoice_service(self, service, service_line, amount):
        if (self.advance_payment_method == "percentage" and self.amount <= 0.00) or (
            self.advance_payment_method == "fixed" and self.fixed_amount <= 0.00
        ):
            raise UserError(_("The value of the down payment amount must be positive."))

        amount, name = self._get_advance_details_service(service)

        invoice_vals = self._prepare_invoice_values_service(
            service, name, amount, service_line
        )
        fiscal_position_id = self._get_fiscal_pos(service.partner_id)

        if fiscal_position_id:
            invoice_vals["fiscal_position_id"] = fiscal_position_id.id
        invoice = (
            self.env["account.move"].sudo().create(invoice_vals).with_user(self.env.uid)
        )
        invoice.message_post_with_view(
            "mail.message_origin_link",
            values={"self": invoice, "origin": service},
            subtype_id=self.env.ref("mail.mt_note").id,
        )
        return invoice

    def _prepare_line_service(self, service, analytic_tag_ids, tax_ids, amount):
        context = {"lang": service.partner_id.lang}
        so_values = {
            "name": _("Down Payment: %s") % (time.strftime("%m %Y"),),
            "price_unit": amount,
            "product_qty": 1.0,
            "order_id": service.id,
            "disc_amount": 0.0,
            "product_uom": self.product_id.uom_id.id,
            "product_id": self.product_id.id,
            "analytic_tag_ids": analytic_tag_ids,
            "tax_ids": [(6, 0, tax_ids)],
            "is_downpayment": True,
        }
        del context
        return so_values
    
    def _get_advance_details(self, order):
        if order:
            context = {'lang': order.partner_id.lang}
            if self.advance_payment_method == 'percentage':
                if all(self.product_id.taxes_id.mapped('price_include')):
                    amount = order.amount_total * self.amount / 100
                else:
                    amount = order.amount_untaxed * self.amount / 100
                name = _("Down payment of %s%%") % (self.amount)
            else:
                amount = self.fixed_amount
                name = _('Down Payment')
            del context

            return amount, name
        return super()._get_advance_details(order)


    def create_invoices(self):
        if self._context.get("active_model") != "sale.service":
            return super(SaleAdvancePaymentInv, self).create_invoices()
        sale_services = self.env["sale.service"].browse(
            self._context.get("active_ids", [])
        )

        if self.advance_payment_method == "delivered":
            if not self.deduct_down_payments:
                raise UserError(
                    _(
                        "Only final invoice is supported for now, please select `Deduct Down Payment` option"
                    )
                )
            sale_services._create_invoices(final=self.deduct_down_payments)
        else:
            # Create deposit product if necessary
            if not self.product_id:
                vals = self._prepare_deposit_product()
                self.product_id = self.env["product.product"].create(vals)
                self.env["ir.config_parameter"].sudo().set_param(
                    "sale.default_deposit_product_id", self.product_id.id
                )

            service_line_obj = self.env["sale.service.line"]
            for order in sale_services:
                amount, name = self._get_advance_details(order)
                fiscal_position_id = self._get_fiscal_pos(order.partner_id)
                if self.product_id.invoice_policy != "order":
                    raise UserError(
                        _(
                            'The product used to invoice a down payment should have an invoice policy set to "Ordered quantities". Please update your deposit product to be able to create a deposit invoice.'
                        )
                    )
                if self.product_id.type != "service":
                    raise UserError(
                        _(
                            "The product used to invoice a down payment should be of type 'Service'. Please use another product or update this product."
                        )
                    )
                taxes = self.product_id.taxes_id.filtered(
                    lambda r: not order.company_id or r.company_id == order.company_id
                )
                tax_ids = fiscal_position_id.map_tax(
                    taxes, self.product_id, order.partner_id
                ).ids
                analytic_tag_ids = []
                for line in order.line_ids:
                    analytic_tag_ids = [
                        (4, analytic_tag.id, None)
                        for analytic_tag in line.analytic_tag_ids
                    ]

                so_line_values = self._prepare_line_service(
                    order, analytic_tag_ids, tax_ids, amount
                )
                so_line = service_line_obj.create(so_line_values)
                order.invoice_ids |= self._create_dp_invoice_service(
                    order, so_line, amount
                )
        if self._context.get("open_invoices", False):
            return sale_services.show_invoices()
        return {"type": "ir.actions.act_window_close"}

    def _prepare_deposit_product(self):
        return {
            "name": "Down payment",
            "type": "service",
            "invoice_policy": "order",
            "property_account_income_id": self.deposit_account_id.id,
            "taxes_id": [(6, 0, self.deposit_taxes_id.ids)],
            "company_id": False,
        }
