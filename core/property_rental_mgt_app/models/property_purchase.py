# -*- coding: utf-8 -*-

from odoo import models,fields,api,_
from odoo.exceptions import UserError
from datetime import datetime, timedelta

class PropertyBuy(models.TransientModel):
    _name = "property.buy"
    _description = "Buy New Propery"
    
    property_id = fields.Many2one('product.product', domain=[('is_property','=',True)])
    desc = fields.Text(string="More Details")
    property_price = fields.Float(string="Price")
    partial_payment_id = fields.Many2one('partial.payment', string="Use Partial Payment")
    state = fields.Selection([('avl','Available'),('sold','Sold')], string="Status", default="avl")
    is_partial = fields.Boolean("Partial Payment")
    owner_id = fields.Many2one('res.partner')
    purchaser_id = fields.Many2one('res.partner')

    @api.onchange('property_id')
    def get_payment(self):
        if self.property_id:
            return {'domain':{'partial_payment_id':[('id','in',self.property_id.partial_payment_ids.ids)]}}

    # get Property details.
    @api.model
    def default_get(self,default_fields):
        res = super(PropertyBuy, self).default_get(default_fields)
        ctx = self._context
        purchase_data = {'property_id':ctx.get('property_id'),
                        'desc':ctx.get('desc'),
                        'property_price':ctx.get('property_price'),
                        'purchaser_id':ctx.get('purchaser_id'),
                        'owner_id':ctx.get('owner_id')}
        res.update(purchase_data)
        return res

    # Create invoice for purchased property. 
    def property_buy_invoice(self):
        active_id = self._context.get('active_id')
        product_id = self.env['product.product'].browse(active_id)
        # Search for the income account
        if product_id.property_account_income_id:
            income_account = product_id.property_account_income_id.id
        elif product_id.categ_id.property_account_income_categ_id:
            income_account = product_id.categ_id.property_account_income_categ_id.id
        else:
            raise UserError(_('Please define income '
                              'account for this product: "%s" (id:%d).')
                            % (product_id.name, product_id.id))
        invoice_list = []
        if self.partial_payment_id:
            number_of_pay = self.partial_payment_id.number_of_pay
            if not number_of_pay < 1:
                invoice_payment =  self.property_price / number_of_pay
                self.property_id.write({'is_partial':True})
                flag = False
                c= 0
                current = fields.Date.today()
                for number in range(number_of_pay):
                    vals  = {
                        'property_id':self.property_id.id,
                        'move_type': 'out_invoice',
                        'invoice_origin':self.property_id.name,
                        'partner_id': self.purchaser_id.id,
                        'invoice_date_due':current,
                        'invoice_date':fields.Date.today(),
                        'invoice_user_id':self.property_id.salesperson_id.id,
                        'invoice_line_ids': [(0,0,{
                            'name':self.property_id.name,
                            'product_id':self.property_id.id,
                            'account_id': income_account,
                            'price_unit': invoice_payment})],
                        }

                    if flag == True:
                        if c < number_of_pay:
                            current = current + timedelta(days=30)
                            vals['invoice_date_due'] = current
                    invoice = self.env["account.move"].with_context(mail_create_nosubscribe=True).create(vals)
                    if invoice:
                        invoice_list.append(invoice.id)
                    c += 1
                    flag = True

        else:
            values = {
                'property_id':self.property_id.id,
                'move_type': 'out_invoice',
                'invoice_origin':self.property_id.name,
                'partner_id': self.purchaser_id.id,
                'invoice_date_due':fields.Date.today(),
                'invoice_date':fields.Date.today(),
                'invoice_user_id':self.property_id.salesperson_id.id,
                'invoice_line_ids': [(0,0,{'name':self.property_id.name, 'product_id':self.property_id.id, 'account_id': income_account, 'price_unit': self.property_price})],
                }
            invoice_id = self.env["account.move"].create(values)
            if invoice_id:
                invoice_list.append(invoice_id.id)

        if invoice_list:
            invoices = self.env['account.move'].browse(invoice_list)
            self.property_id.write({'state':'sold','user_id':self.env.user.id,'is_sold':True,'invoice_ids':[(6,0,invoice_list)]})
            template_id =  self.env.ref('property_rental_mgt_app.property_purchased_template')
            template_values = template_id.generate_email(self.id, ['subject', 'body_html', 'email_from', 'email_to', 'partner_to', 'email_cc', 'reply_to', 'scheduled_date'])
            mail_mail_obj = self.env['mail.mail']
            msg_id = mail_mail_obj.sudo().create(template_values)
            if msg_id:
                mail_mail_obj.sudo().send(msg_id)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: