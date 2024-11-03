# -*- coding: utf-8 -*-
##############################################################################
#
# developed by Shilal Software Center 
# Email : shilalgroup@gmail.com
# Phones : +249902605920 
# whatsapp : +249902605920
#    
##############################################################################

from datetime import datetime, timedelta
from odoo import models, api, fields, _
from odoo.exceptions import UserError, AccessError, ValidationError


class SscReportCreator(models.Model):
    _name = 'ssc.create.report'
    _description = "Model Contain all importanat data to print report throught one of the designed demplates"

    date = fields.Date(string="Date", default=fields.Date.today())
    user_id = fields.Many2one('res.users', string='Created By', default=lambda self: self.env.user, readonly=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete="cascade", help="The type of document this template can be used with", 
        domain="[('model','in',['account.move','hr.contract','hr.employee','res.partner','product.pricelist','purchase.order','sale.order','stock.picking','stock.inventory','account.payment'])]")
    template_id = fields.Many2one('ssc.create.template', string="Template", domain="[('model_id','=',model_id),('state','=','applied')]")
    model = fields.Char(string="Model Name", related='model_id.model')
    body = fields.Html(string="Body", translate=True, sanitize=False, related='template_id.body')
    employee_id = fields.Many2one('hr.employee', string="Employee")
    contract_id = fields.Many2one('hr.contract', string="Employee")
    sale_order_id = fields.Many2one('sale.order', string="Sale Order")
    purchase_order_id = fields.Many2one('purchase.order', string="Purchase Order")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    stock_picking_id = fields.Many2one('stock.picking', string="Picking")
    stock_inventory_id = fields.Many2one('stock.inventory', string="Inventory Adjustments")
    partner_id = fields.Many2one('res.partner', string="Partner")
    account_payment_id = fields.Many2one('account.payment', string="Account Payment")
    product_pricelist_id = fields.Many2one('product.pricelist', string="Product Pricelist")

    
    def _find_mail_template(self, force_confirmation_template=False):
        """
        find mail template by id
        """
        template_id = False

        template_id = self.env['mail.template'].search([('name', '=', self.template_id.name)]).id
        

        return template_id
    
    def action_test_mail_send(self):
        ''' 
        Opens a wizard to compose an email, with relevant mail template loaded by default 
        '''
        self.template_id.action_to_apply()

        self.ensure_one()
        template_id = self._find_mail_template()
        
        # lang = self.env.context.get('lang')
        # template = self.env['mail.template'].browse(template_id)
        # if template.lang:
        #     lang = template._render_template(template.lang, self.model_id.model, self.model_id.ids)

        default_res_id = self.template_id.id
        if self.employee_id:
            default_res_id = self.employee_id.id
        if self.contract_id:
            default_res_id = self.contract_id.id
        if self.sale_order_id:
            default_res_id = self.sale_order_id.id
        if self.purchase_order_id:
            default_res_id = self.purchase_order_id.id
        if self.invoice_id:
            default_res_id = self.invoice_id.id
        if self.stock_picking_id:
            default_res_id = self.stock_picking_id.id
        if self.stock_inventory_id:
            default_res_id = self.stock_inventory_id.id
        if self.partner_id:
            default_res_id = self.partner_id.id
        if self.account_payment_id:
            default_res_id = self.account_payment_id.id
        if self.product_pricelist_id:
            default_res_id = self.product_pricelist_id.id

        ctx = {
            'default_model': self.model_id.model,
            'default_res_id': default_res_id,
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'mark_so_as_sent': True,
            'custom_layout': "mail.mail_notification_paynow",
            'default_orientation': self.template_id.orientation,
            'proforma': self.env.context.get('proforma', False),
            'force_email': True,
            'default_check_value': True,
            'default_is_log': True,
            # 'model_description': self.with_context(lang=lang).type_name,
        }
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }