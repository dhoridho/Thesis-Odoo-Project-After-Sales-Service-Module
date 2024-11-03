# -*- coding: utf-8 -*-
# Part of Softhealer Technologies.

from odoo import models, fields, _

class MailComposeMessage(models.TransientModel):
    _inherit = 'mail.compose.message'

    def action_send_mail(self):
        super(MailComposeMessage, self).action_send_mail()
        if self.env.context.get('active_model') == 'purchase.agreement' and self.env.context.get('active_id'):
            tender_id = self.env['purchase.agreement'].sudo().browse(self.env.context.get('active_id'))
            if tender_id and self.partner_ids and self.env.company.sh_auto_add_followers:
                tender_id.message_subscribe(self.partner_ids.ids)


class ShPurchaseAgreement(models.Model):
    _name = 'purchase.agreement'
    _description = 'Purchase Agreement'
    _rec_name = 'name'
    _inherit = ['portal.mixin', 'mail.thread',
                'mail.activity.mixin', 'utm.mixin']

    name = fields.Char('Name', readonly=True, tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('bid_selection', 'Bid Selection'), (
        'closed', 'Closed'), ('cancel', 'Cancelled')], string="State", default='draft', tracking=True)
    rfq_count = fields.Integer("Received Quotations", compute='_compute_rfq_count')
    order_count = fields.Integer("Selected Orders", compute='_compute_order_count')
    sh_purchase_user_id = fields.Many2one(
        'res.users', 'Purchase Representative', tracking=True)
    sh_agreement_type = fields.Many2one(
        'purchase.agreement.type', 'Tender Type', required=True, tracking=True)
    sh_vender_id = fields.Many2one(
        'res.partner', 'Vendor', tracking=True)
    partner_id = fields.Many2one('res.partner', 'Partner')
    partner_ids = fields.Many2many(
        'res.partner', string='Vendors', tracking=True)
    user_id = fields.Many2one('res.users', 'User')
    sh_agreement_deadline = fields.Datetime(
        'Tender Deadline', tracking=True)
    sh_order_date = fields.Date('Ordering Date', tracking=True)
    sh_delivery_date = fields.Date(
        'Delivery Date', tracking=True)
    sh_source = fields.Char('Source Document', tracking=True)
    sh_notes = fields.Text("Terms & Conditions", tracking=True)
    sh_purchase_agreement_line_ids = fields.One2many(
        'purchase.agreement.line', 'agreement_id', string='Purchase Agreement Line')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True, default=lambda self: self.env.company)
    compute_custom_boolean = fields.Boolean(compute='_compute_module_boolean')
    sh_manage_tender_document = fields.Boolean(compute='_compute_tender_document')
    document_count = fields.Integer('Documents',compute='_compute_documents')

    def _compute_tender_document(self):
        for rec in self:
            rec.sh_manage_tender_document = False
            if self.env.company.sh_tender_document_manage:
                rec.sh_manage_tender_document = True

    def _compute_documents(self):
        for rec in self:
            rec.document_count = 0
            attachment_ids = self.env['ir.attachment'].sudo().search([('res_model','=','purchase.agreement'),('res_id','=',rec.id)])
            if attachment_ids:
                rec.document_count = len(attachment_ids.ids)
    
    def action_view_documents(self):
        self.ensure_one()
        return {
            'name':'Tender Documents',
            'type':'ir.actions.act_window',
            'res_model':'ir.attachment',
            'view_mode':'kanban,tree,form',
            'domain':[('res_model','=','purchase.agreement'),('res_id','=',self.id)],
            'target':'current',
            }

    def _compute_module_boolean(self):
        if self:
            for rec in self:
                rec.compute_custom_boolean = False
                portal_module_id = self.env['ir.module.module'].sudo().search(
                    [('name', '=', 'sh_po_tender_portal'), ('state', 'in', ['installed'])], limit=1)
                if portal_module_id:
                    rec.compute_custom_boolean = True

    def _compute_access_url(self):
        super(ShPurchaseAgreement, self)._compute_access_url()
        for tender in self:
            tender.access_url = '/my/tender/%s' % (tender.id)

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s %s' % ('Tender', self.name)

    def _compute_rfq_count(self):
        if self:
            for rec in self:
                purchase_orders = self.env['purchase.order'].sudo().search(
                    [('agreement_id', '=', rec.id), ('state', 'in', ['draft']), ('selected_order', '=', False)])
                if purchase_orders:
                    rec.rfq_count = len(purchase_orders.ids)
                else:
                    rec.rfq_count = 0

    def _compute_order_count(self):
        if self:
            for rec in self:
                purchase_orders = self.env['purchase.order'].sudo().search(
                    [('agreement_id', '=', rec.id), ('state', 'not in', ['cancel']), ('selected_order', '=', True)])
                if purchase_orders:
                    rec.order_count = len(purchase_orders.ids)
                else:
                    rec.order_count = 0

    def action_confirm(self):
        if self:
            for rec in self:
                seq = self.env['ir.sequence'].next_by_code(
                    'purchase.agreement')
                rec.name = seq
                rec.state = 'confirm'

    def action_new_quotation(self):
        if self:
            for rec in self:
                line_ids = []
                current_date = None
                if rec.sh_delivery_date:
                    current_date = rec.sh_delivery_date
                else:
                    current_date = fields.Datetime.now()
                for rec_line in rec.sh_purchase_agreement_line_ids:
                    line_vals = {
                        'product_id': rec_line.sh_product_id.id,
                        'name': rec_line.sh_product_id.name,
                        'date_planned': current_date,
                        'product_qty': rec_line.sh_qty,
                        'status': 'draft',
                        'agreement_id': rec.id,
                        'product_uom': rec_line.sh_product_id.uom_id.id,
                        'price_unit': rec_line.sh_price_unit,
                    }
                    line_ids.append((0, 0, line_vals))
                return {
                    'name': _('New'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'purchase.order',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'context': {'default_agreement_id': rec.id, 'default_user_id': rec.sh_purchase_user_id.id, 'default_order_line': line_ids},
                    'target': 'current'
                }

    def action_validate(self):
        if self:
            for rec in self:
                if self.env.company.sh_auto_add_followers and rec.partner_ids:
                    rec.message_subscribe(rec.partner_ids.ids)
                if self.env.company.sh_portal_user_create and rec.partner_ids:
                    for vendor in rec.partner_ids:
                        user_id = self.env['res.users'].sudo().search([('partner_id','=',vendor.id)],limit=1)
                        if not user_id:
                            portal_wizard_obj = self.env['portal.wizard']
                            created_portal_wizard =  portal_wizard_obj.create({})
                            if created_portal_wizard and vendor.email and self.env.user:
                                portal_wizard_user_obj = self.env['portal.wizard.user']
                                wiz_user_vals = {
                                    'wizard_id': created_portal_wizard.id,
                                    'partner_id': vendor.id,
                                    'email' : vendor.email,
                                    'in_portal' : True,
                                    'user_id' : self.env.user.id,
                                    }
                                created_portal_wizard_user = portal_wizard_user_obj.create(wiz_user_vals)
                                if created_portal_wizard_user:
                                    created_portal_wizard.action_apply()
                                    vendor_portal_user_id = self.env['res.users'].sudo().search([('partner_id','=',vendor.id)],limit=1)
                                    if vendor_portal_user_id:
                                        vendor_portal_user_id.is_tendor_vendor = True
                rec.state = 'bid_selection'

    def action_analyze_rfq(self):
        list_id = self.env.ref(
            'sh_po_tender_management.sh_bidline_tree_view').id
        form_id = self.env.ref(
            'sh_po_tender_management.sh_bidline_form_view').id
        pivot_id = self.env.ref(
            'sh_po_tender_management.purchase_order_line_pivot_custom').id
        return {
            'name': _('Tender Lines'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.line',
            'view_type': 'form',
            'view_mode': 'tree,pivot,form',
            'views': [(list_id, 'tree'), (pivot_id, 'pivot'), (form_id, 'form')],
            'domain': [('agreement_id', '=', self.id), ('state', 'not in', ['cancel']), ('order_id.selected_order', '=', False)],
            'context': {'search_default_groupby_product': 1},
            'target': 'current'
        }

    def action_set_to_draft(self):
        if self:
            for rec in self:
                rec.state = 'draft'

    def action_close(self):
        if self:
            for rec in self:
                rec.state = 'closed'

    def action_cancel(self):
        if self:
            for rec in self:
                rec.state = 'cancel'

    def action_send_tender(self):
        self.ensure_one()
        ir_model_data = self.env['ir.model.data']
        template_id = ir_model_data.get_object_reference(
            'sh_po_tender_management', 'email_template_edi_purchase_tedner')[1]
        try:
            compose_form_id = ir_model_data.get_object_reference(
                'mail', 'email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'purchase.agreement',
            'default_res_id': self.ids[0],
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True
        }
        if self.sh_vender_id:
            ctx.update({
                'default_partner_ids': [(6, 0, self.sh_vender_id.ids)]
            })
        if self.partner_ids:
            ctx.update({
                'default_partner_ids': [(6, 0, self.partner_ids.ids)]
            })
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }

    def action_view_quote(self):
        return {
            'name': _('Received Quotations'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('agreement_id', '=', self.id), ('selected_order', '=', False), ('state', 'in', ['draft'])],
            'target': 'current'
        }

    def action_view_order(self):
        return {
            'name': _('Selected Orders'),
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_id': self.id,
            'domain': [('agreement_id', '=', self.id), ('selected_order', '=', True), ('state', 'not in', ['cancel'])],
            'target': 'current'
        }


class ShPurchaseAgreementLine(models.Model):
    _name = 'purchase.agreement.line'
    _description = "Purchase Agreement Line"

    agreement_id = fields.Many2one('purchase.agreement', 'Purchase Tender')
    sh_product_id = fields.Many2one(
        'product.product', 'Product', required=True)
    sh_qty = fields.Float('Quantity', default=1.0)
    sh_ordered_qty = fields.Float(
        'Ordered Quantities', compute='_compute_ordered_qty')
    sh_price_unit = fields.Float('Unit Price')
    company_id = fields.Many2one('res.company', related='agreement_id.company_id',
                                 string='Company', store=True, readonly=True, default=lambda self: self.env.company)

    def _compute_ordered_qty(self):
        if self:
            for rec in self:
                order_qty = 0.0
                purchase_order_lines = self.env['purchase.order.line'].sudo().search([('product_id', '=', rec.sh_product_id.id), (
                    'agreement_id', '=', rec.agreement_id.id), ('order_id.selected_order', '=', True), ('order_id.state', 'in', ['purchase'])])
                for line in purchase_order_lines:
                    order_qty += line.product_qty
                rec.sh_ordered_qty = order_qty
