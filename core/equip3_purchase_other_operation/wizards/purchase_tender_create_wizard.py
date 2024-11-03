
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PurchaseTenderCreateWizard(models.TransientModel):
    _name = 'purchase.tender.create.wizard'
    _description = 'Purchase Tender Create Wizard'

    @api.model
    def _default_domain(self):
        domain_vendor = []
        pr_line_ids = []
        if self.env['ir.config_parameter'].sudo().get_param('is_vendor_approval_matrix'):
        # if self.env.company.is_vendor_approval_matrix:
            domain_vendor = [('state2', '=', 'approved'),('supplier_rank', '>', 0),('is_vendor', '=', True)]
        
        else:
            domain_vendor = [('supplier_rank', '>', 0), ('is_vendor', '=', True)]

        if self._context.get('active_model') == "purchase.request.line":
            pr_line_ids = self.env['purchase.request.line'].browse(self.env.context.get('active_ids'))

        elif self._context.get('active_model') == "purchase.request":
            pr_line_ids = self.env['purchase.request'].browse(self.env.context.get('active_ids'))
        if pr_line_ids:
            domain_vendor.extend([('branch_id','=',pr_line_ids.branch_id.id)])
        return domain_vendor

    vendor_ids = fields.Many2many('res.partner', string='Vendor', domain=_default_domain, context={"res_partner_search_mode": "supplier", "default_is_company": True})
    product_line_ids = fields.One2many('purchase.tender.create.lines.wizard', 'purchase_tender_lines', string="Product Lines")
    sh_source = fields.Char(string="Source")
    company_id = fields.Many2one('res.company', default=lambda self:self.env.user.company_id, required="1")

    def _create_tender_vals(self):
        data = []
        recs = {}
        context = dict(self.env.context) or {}
        IrConfigParam = self.env['ir.config_parameter'].sudo()
        pr_qty_limit = IrConfigParam.get_param('pr_qty_limit', "no_limit")
        max_percentage = int(IrConfigParam.get_param('max_percentage', 0))
        # pr_qty_limit = self.env.company.pr_qty_limit
        # max_percentage = self.env.company.max_percentage
        purchase_request_id = False
        for record in self:
            for product_line_id in record.product_line_ids:
                if product_line_id.tender_qty <= 0:
                    continue
                purchase_request_id = product_line_id.pr_line_id.request_id
                if pr_qty_limit == 'percent':
                    percentage_qty = product_line_id.pr_line_id.product_qty + ((product_line_id.pr_line_id.product_qty * max_percentage) / 100)
                    calculate_qty = percentage_qty - (product_line_id.pr_line_id.purchased_qty + product_line_id.pr_line_id.tender_qty)
                    if product_line_id.tender_qty > calculate_qty:
                        raise UserError(_("Quantity to Tender for %s cannot request greater than %d") % (product_line_id.product_id.display_name, calculate_qty))
                elif pr_qty_limit == 'fix':
                    calculate_qty = product_line_id.pr_line_id.product_qty - (product_line_id.pr_line_id.purchased_qty + product_line_id.pr_line_id.tender_qty)
                    if product_line_id.tender_qty > calculate_qty:
                        raise UserError(_("Quantity to Tender for %s cannot request greater than %d") % (product_line_id.product_id.display_name, calculate_qty))
                product_line_id.pr_line_id.tender_qty += product_line_id.tender_qty

                product_id = product_line_id.product_id.id
                if product_id in recs:
                    # here just update the quantities or any other fields you want to sum
                    recs[product_id]['sh_qty'] += product_line_id.tender_qty
                    recs[product_id]['sh_ordered_qty'] += product_line_id.remaning_qty
                else:
                    recs[product_id] = {'sh_product_id' : product_line_id.product_id.id,
                                'sh_product_description': product_line_id.product_description,
                                'sh_qty' : product_line_id.tender_qty,
                                'request_line_id': product_line_id.pr_line_id.id,
                                'sh_ordered_qty' : product_line_id.remaning_qty,
                                'sh_product_uom_id': product_line_id.uom.id,
                                'dest_warehouse_id': product_line_id.destination_warehouse.id,
                                'analytic_tag_ids': product_line_id.analytics_tag_ids.ids,
                                'schedule_date': product_line_id.schedule_date,
                    }
        for rvals in recs.values():
            data.append((0, 0, rvals))
        vals = {}
        if data:
            vals = {
                'partner_ids' : self.vendor_ids.ids,
                'sh_source': self.sh_source,
                'purchase_request_id': purchase_request_id.id,
                'sh_purchase_agreement_line_ids' : data,
                'branch_id': purchase_request_id.branch_id.id
            }
        return vals

    def action_confirm(self):
        res = []
        if self.product_line_ids:
            self.product_line_ids[0].request_id.purchase_req_state = 'in_progress'
        vals = self._create_tender_vals()
        if not vals:
            return False
        context = dict(self.env.context) or {}
        purchase_tender = self.env['purchase.agreement'].create(vals)
        purchase_tender.set_expiry_date()
        res.append(purchase_tender.id)
        if context.get('goods_order'):
            purchase_tender.is_goods_orders = True
        elif context.get('services_good'):
            purchase_tender.is_services_orders = True
        elif context.get('assets_orders'):
            purchase_tender.is_assets_orders = True
        elif context.get('rentals_orders'):
            purchase_tender.is_rental_orders = True
        purchase_tender.create_approval()
        return {
                "domain": [("id", "in", res)],
                'type': 'ir.actions.act_window',
                'name': 'Purchase Tender',
                'view_mode': 'tree,form',
                'res_model': 'purchase.agreement',
                'res_id' : purchase_tender.id,
                "view_id": False,
                "context": False,
            }

class PurchaseTenderCreateLinesWizard(models.TransientModel):
    _name = 'purchase.tender.create.lines.wizard'
    _description = 'Purchase Tender Create Lines Wizard'

    purchase_tender_lines = fields.Many2one('purchase.tender.create.wizard', string='Purchase Tender Lines')
    product_id = fields.Many2one('product.product', string="Product")
    product_description = fields.Char(string="Description")
    remaning_qty = fields.Float(string="Remaning Qty")
    tender_qty = fields.Float(string="Quantity To Tender")
    uom = fields.Many2one('uom.uom', string="Uom")
    pr_line_id = fields.Many2one('purchase.request.line', string="Purchase Line")
    request_id = fields.Many2one('purchase.request', related='pr_line_id.request_id', string="Purchase Request")
    destination_warehouse = fields.Many2one('stock.warehouse', string="Warehouse")
    analytics_tag_ids = fields.Many2many('account.analytic.tag', string="Analytic Tags")
    schedule_date = fields.Date(string="Schedule Date")
