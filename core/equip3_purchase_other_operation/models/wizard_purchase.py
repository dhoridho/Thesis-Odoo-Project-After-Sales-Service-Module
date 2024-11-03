from odoo import api, fields, models, _ 
from datetime import date

class WizardQuotationAgreement(models.TransientModel):
    _name = "wizard.quotation.agreement"
    _description = "Wizard Quotation Agreement"
    
    agreement_id = fields.Many2one('purchase.agreement', string="Tender")
    partner_ids = fields.Many2many('res.partner', string='Vendors')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    
    def _send_notification_tender(self, agreement_id):
        is_email_notification_tender = self.env['ir.config_parameter'].get_param('equip3_purchase_other_operation.is_email_notification_tender')
        # is_email_notification_tender = self.env.company.is_email_notification_tender
        tender_scope = agreement_id.tender_scope
        
        if is_email_notification_tender and tender_scope == 'invitation_tender':
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            url = f"{base_url}/my/tender/{agreement_id.id}"
            template_id = self.env.ref('equip3_purchase_other_operation.email_template_purchase_tender_invitation_portal')
            company_email = self.env.user.company_id.email
            
            for partner in agreement_id.partner_ids:
                email_to = partner.email
                ctx = {
                    'email_from' : company_email,
                    'email_to' : email_to,
                    'partner_name' : partner.name,
                    'date': date.today(),
                    'url' : url,
                }
                template_id.sudo().with_context(ctx).send_mail(agreement_id.id, True)

    def action_new_quotation_wizard(self):
        for res in self:
            existing_partner_ids = self.env['purchase.order'].search(
                [('partner_id', 'in', res.partner_ids.ids), ('agreement_id', '=', res.agreement_id.id)]).mapped('partner_id.id')

            new_partner_ids = [
                partner.id for partner in res.partner_ids if partner.id not in existing_partner_ids]

            if new_partner_ids:
                res.agreement_id.create_new_rfq(
                    self.env['res.partner'].browse(new_partner_ids))
                res._send_notification_tender(res.agreement_id)


class ShPurchaseOrderWizard(models.TransientModel):
    _inherit = 'purchase.order.wizard'

    partner_id = fields.Many2one(required=False)
    date_planned = fields.Datetime(required=False)
    order_selection = fields.Selection(required=False)
    sh_group_by_partner = fields.Boolean("Group By")
    sh_cancel_old_rfqs = fields.Selection([('none', 'None'), ('cancel_all_old', "Cancel Old RFQ'S of Tender"), ('cancel_old_partner', "Cancel Old RFQ'S of Selected Tender of Partners")],
                                          default='none',
                                          string="Cancel Old RFQ'S"
                                          )
    sh_create_po = fields.Selection([
        ('rfq', 'RFQ'),
        ('po', 'Purchase Order')
    ], default='rfq', string="Create RFQ/Purchase Order")

    def action_create_po(self):
        context = dict(self._context or {})
        purchase_order_line = self.env['purchase.order.line'].sudo().search(
            [('id', 'in', context.get('active_ids'))])
        active_id = self.env['purchase.order.line'].sudo().search([('id', 'in', dict(self._context or {}).get('active_ids'))],limit=1)
        is_rental_orders = False
        if 'is_rental_orders' in active_id._fields:
            is_rental_orders = active_id.mapped('is_rental_orders')[0]
        if self.env['ir.config_parameter'].sudo().get_param('is_good_services_order') == 'True':       
        # if self.env.company.is_good_services_order:
            is_goods_orders = active_id.mapped('is_goods_orders')[0]
            is_services_orders = active_id.mapped('is_services_orders')[0]
            is_assets_orders = active_id.mapped('is_assets_orders')[0]
            if is_goods_orders:
                context.update({
                    'default_is_goods_orders': is_goods_orders,
                    "goods_order": True,
                })
            elif is_services_orders:
                context.update({
                    'default_is_services_orders': is_services_orders,
                    'services_good': True,
                    })
            elif is_assets_orders:
                context.update({
                    'default_is_assets_orders': is_assets_orders,
                    'assets_orders': True,
                    })
            elif is_rental_orders:
                context.update({
                    'default_is_rental_orders': is_rental_orders,
                    'rentals_orders': True,
                    'is_rental_orders': True,
                })
        else:
            if is_rental_orders:
                context.update({
                    'default_is_rental_orders': is_rental_orders,
                    'rentals_orders': True,
                    'is_rental_orders': True,
                })
            else:
                context.update({'default_is_goods_orders': False})

        if self.sh_cancel_old_rfqs == 'cancel_all_old':
            for line in purchase_order_line:
                purchase_orders = self.env['purchase.order'].sudo().search(
                    [('agreement_id', '=', line.agreement_id.id), ('state', 'in', ['draft'])])
                if purchase_orders:
                    for order in purchase_orders:
                        order.button_cancel()
        elif self.sh_cancel_old_rfqs == 'cancel_old_partner':
            partner_list = []
            agreement_list = []
            for order_line in purchase_order_line:
                if order_line.partner_id and order_line.partner_id not in partner_list:
                    partner_list.append(order_line.partner_id.id)
                if order_line.agreement_id and order_line.agreement_id not in agreement_list:
                    agreement_list.append(order_line.agreement_id.id)
            purchase_orders = self.env['purchase.order'].sudo().search(
                [('state', 'in', ['draft'])])
            if purchase_orders:
                for order in purchase_orders:
                    if order.partner_id.id in partner_list and order.agreement_id.id in agreement_list:
                        order.button_cancel()
        if purchase_order_line:
            if not self.sh_group_by_partner:
                order_ids = []
                origin = ",".join(purchase_order_line.mapped('agreement_id.name'))
                partners = purchase_order_line.mapped('partner_id')
                for partner in partners:
                    vals = {}
                    po_line = []
                    for order_line in purchase_order_line.filtered(lambda l: l.partner_id.id == partner.id):
                        vals = {
                            'partner_id': order_line.partner_id.id,
                            'agreement_id': order_line.agreement_id.id,
                            'user_id': self.env.user.id,
                            'origin' : origin,
                            'date_planned': order_line.date_planned,
                            'picking_type_id': order_line.order_id.picking_type_id.id or False,
                            'branch_id': order_line.order_id.branch_id.id,
                            'analytic_account_group_ids': order_line.order_id.analytic_account_group_ids.ids,
                            'not_editable': order_line.order_id.not_editable,
                            'is_editable': order_line.order_id.is_editable,
                        }
                        if context.get('goods_order'):
                            vals.update({'is_goods_orders': True})
                        elif context.get('services_good'):
                            vals.update({'is_services_orders': True})
                        elif context.get('assets_orders'):
                            vals.update({'is_assets_orders': True})
                        elif is_rental_orders:
                            context.update({
                                'default_is_rental_orders': is_rental_orders,
                                'rentals_orders': True,
                                'is_rental_orders': True,
                            })
                        line_vals = {
                            'product_id': order_line.product_id.id,
                            'name': order_line.product_id.name,
                            'status': 'draft',
                            'product_uom': order_line.product_uom.id,
                            'product_qty': order_line.product_qty,
                            'base_price': order_line.base_price,
                            'update_base': order_line.update_base,
                            'price_unit': order_line.price_unit,
                            'picking_type_id': order_line.order_id.picking_type_id.id,
                            'destination_warehouse_id': order_line.destination_warehouse_id.id,
                            'analytic_tag_ids': order_line.analytic_tag_ids.ids,
                            'taxes_id': [(6, 0, order_line.taxes_id.ids)],
                        }
                        po_line.append((0, 0, line_vals))
                        
                    if 'partner_id' in vals and vals['partner_id']:
                        if po_line:
                            vals['order_line'] = po_line
                        purchase_order_id = self.env['purchase.order'].with_context(context).create(vals)
                        purchase_order_id._onchange_partner_invoice_id()
                        if active_id.is_goods_orders:
                            purchase_order_id.is_goods_orders = active_id.is_goods_orders
                            for line in purchase_order_id.order_line:
                                line.is_goods_orders = purchase_order_id.is_goods_orders
                                
                        if self.sh_create_po == 'po':
                            purchase_order_id.selected_order = True
                            purchase_order_id.button_confirm()
                        else:
                            purchase_order_id.selected_order = False
                        order_ids.append(purchase_order_id.id)
                return {
                    'name': _("Purchase Orders/RFQ's"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', order_ids)],
                    'target': 'current',
                    'context': context,
                }
            else:
                partner_list = []
                agreement_id = None
                picking_id = None
                order_ids = []
                for order_line in purchase_order_line:
                    if order_line.partner_id and order_line.partner_id not in partner_list:
                        partner_list.append(order_line.partner_id)
                    agreement_id = order_line.agreement_id
                    picking_id = order_line.order_id.picking_type_id.id,
                for partner in partner_list:
                    order_vals = {}
                    order_vals = {
                        'partner_id': partner.id,
                        'user_id': self.env.user.id,
                        'agreement_id': agreement_id.id,
                        'picking_type_id': picking_id,
                        'branch_id': agreement_id.branch_id.id,
                        'analytic_account_group_ids': agreement_id.account_tag_ids.ids,
                        'not_editable': True,
                        'is_editable': True,
                    }
                    order_id = self.env['purchase.order'].with_context(context).create(order_vals)
                    order_ids.append(order_id.id)
                    line_ids = []
                    
                    for order_line in purchase_order_line:
                        if order_line.partner_id.id == partner.id:
                            order_line_vals = {
                                'order_id': order_id.id,
                                'product_id': order_line.product_id.id,
                                'name': order_line.product_id.name,
                                'status': 'draft',
                                'product_uom': order_line.product_uom.id,
                                'product_qty': order_line.product_qty,
                                'price_unit': order_line.price_unit,
                                'destination_warehouse_id': order_line.destination_warehouse_id.id,
                                'analytic_tag_ids': order_line.analytic_tag_ids.ids,
                                'picking_type_id': order_line.order_id.picking_type_id.id,
                                'taxes_id': [(6, 0, order_line.taxes_id.ids)]
                            }
                            line_ids.append((0, 0, order_line_vals))
                    order_id.order_line = line_ids
                    
                    if active_id.is_goods_orders:
                        order_id.is_goods_orders = active_id.is_goods_orders
                        for line in order_id.order_line:
                            line.is_goods_orders = order_id.is_goods_orders
                    
                    if self.sh_create_po == 'po':
                        order_id.selected_order = True
                        order_id.button_confirm()
                    else:
                        order_id.selected_order = False
                return {
                    'name': _("Purchase Orders/RFQ's"),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'domain': [('id', 'in', order_ids)],
                    'target': 'current',
                    'context': context,
                }
