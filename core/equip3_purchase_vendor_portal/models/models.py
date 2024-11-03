# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api,_
from odoo.http import request
from datetime import date


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    @api.model
    def create(self, vals):
        if 'name' not in vals:
            if self.env.user.partner_id.id:
                vals['name'] = self.env.user.partner_id.id
        if 'date_start' in vals:
            if vals['date_start'] == '':
                vals['date_start'] = False
        if 'date_end' in vals:
            if vals['date_end'] == '':
                vals['date_end'] = False
        res = super(SupplierInfo, self).create(vals)
        return res

    def action_mass_approved(self):
        for rec in self:
            if rec.state != 'waiting_approval':
                continue
            rec.request_partner_id = self.env.user.partner_id.id
            if rec.approval_ids:
                for line in rec.approval_ids:
                    if not line.approved:
                        line.approved = True
            rec.action_approved()

    def action_mass_request_approval(self):
        for rec in self:
            if rec.state != 'draft' and not rec.is_vendor_pricelist_approval_matrix and not rec.vendor_pricelist_approval_matrix and not rec.approval_ids:
                continue
            rec.action_request_for_approval()
    
    def action_mass_reject(self):
        active_ids = request.env.context.get('active_ids', [])
        return {
            'type': 'ir.actions.act_window',
            'name': _('Reject Vendor Pricelist'),
            'res_model': 'cancel.supplier.memory',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'is_mass_reject': 1,
                'default_supplier_ids': active_ids,
            },
        }
        
    def action_mass_set_to_draft(self):
        for rec in self:
            if rec.state == 'rejected':
                rec.action_draft()
        return

class UoM(models.Model):
    _inherit = 'uom.uom'

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def set_notes(self):
        res_text = ""
        for res in self:
            if res.term_condition_box:
                res_text = res.term_condition_box
        return res_text

    def set_notes_service(self):
        res_text = ""
        for res in self:
            if res.service_level_agreement_box:
                res_text = res.service_level_agreement_box
        return res_text

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        return res

class TermCondition(models.Model):
    _inherit = 'term.condition'

    @api.constrains('term_condition')
    def update_term_con(self):
        for res in self:
            purchases = self.env['purchase.order'].search([('term_condition', '=', res.id)])
            for purchase in purchases:
                purchase._set_term_condition_box()

class purchase_aggreement(models.Model):
    _inherit = 'purchase.agreement'

    vendor_names = fields.Char(string='Vendor Names', compute="_compute_vendor_names", store=True)
    purchase_order_ids = fields.One2many('purchase.order', 'agreement_id')

    @api.depends('partner_ids')
    def _compute_vendor_names(self):
        for i in self:
            if i.partner_ids:
                i.vendor_names = ', '.join(i.partner_ids.mapped('name'))
            else:
                i.vendor_names = ''
                


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_customer = fields.Boolean(string="Is a customer")
    is_vendor = fields.Boolean(string="Is a vendor")

class PurchaseRequisition(models.Model):
    _name = "purchase.requisition"
    _description = "Purchase Requisition"
    _inherit = ["purchase.requisition", 'mail.thread', 'mail.activity.mixin', 'portal.mixin']

    def _compute_access_url(self):
        super(PurchaseRequisition, self)._compute_access_url()
        for record in self:
            record.access_url = '/my/blanket/order/%s' % (record.id)

    def _get_report_base_filename(self):
        return 'Blanket Order'