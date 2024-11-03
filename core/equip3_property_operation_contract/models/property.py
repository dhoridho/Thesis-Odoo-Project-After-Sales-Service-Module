from odoo import models, fields, api, _
from odoo.exceptions import UserError



class Prduct(models.Model):
    _inherit = 'product.product'
    
    contract_count = fields.Integer(compute='_compute_contract_count', string='Contract Count')
    agreement_id = fields.Many2one('agreement', string='Agreement', domain=[('is_template', '=', False)])
    
    def _compute_contract_count(self):
        for rec in self:
            rec.contract_count = self.env['agreement'].search_count([('property_id', '=', rec.id)])
                
    def contract_action_link(self):
        agreement = self.env['agreement'].search([('property_id', '=', self.id)])
        if len(agreement) > 1:
            views = [(self.env.ref('equip3_property_operation_contract.property_agreement_tree_view').id, 'tree'), (self.env.ref('agreement_legal.partner_agreement_form_view').id, 'form')]
            return{
                'name': 'Contracts',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'view_id': False,
                'res_model': 'agreement',
                'views': views,
                'domain': [('property_id', '=', self.id)],
                'type': 'ir.actions.act_window',
            }
        else:
            return {
                'name': _('Contract'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'agreement',
                'res_id': agreement.ids[0],
                'target': 'current',
            }
    
    def set_rentable(self):
        if self.property_book_for != 'rent':
            raise UserError(_("This property only allow for rent..!"))
        if self.rent_price <= 0 or self.deposite <= 0:
            raise UserError(_("Please enter valid property rent or deposite price for (%s)..!") % self.name)
        agreement = self.env['agreement'].search([('property_id', '=', self.id)])
        for rec in agreement:
            if rec.is_recurring_invoice == True:
                raise UserError(_("You can not set rentable property for active contract..!"))
        # if agreement.is_recurring_invoice == True:
        #     raise UserError(_("You can not set rentable property for active contract..!"))
        self.state = 'rent'
    
    def button_confirm(self):
        if self.state == 'draft' and self.property_book_for == 'sale':
            if self.property_price <= 0 or self.discounted_price <= 0:
                raise UserError(_("Please enter valid property price or reasonable amount...!"))
            self.state = 'sale'
        if self.state == 'draft' and self.property_book_for == 'rent':
            if self.rent_price <= 0 or self.deposite <= 0:
                raise UserError(_("Please enter valid property rent amount...!"))
            contracts = self.env['agreement'].search([("is_template", "=", True)])
            if not contracts:
                raise UserError(_("Please first create contract template for property rental...!(Contract Management -> Configuration -> Templates)"))
            self.state = 'rent'

        if self.user_commission_ids:
            for each in self.user_commission_ids:
                if each.percentage <= 0:
                    raise UserError(_("Please enter valid commission percentage in commission lines...!"))
    
    def buy_now_property(self):
        if self.agreement_id:
            raise UserError(_("This property (%s) already sold out..!")%self.name)
        if self.property_book_for != 'sale':
            raise UserError(_("This property only allow for Rent..!"))
        if self.property_price < 1:
            raise UserError(_("Please enter valid property price for (%s)..!") % self.name)

        view_id = self.env.ref('equip3_property_operation_contract.property_buy_contract_wizard')
        if self.reasonable_price:
            property_price = self.discounted_price
        else:
            property_price = self.property_price
        if view_id:
            buy_property_data = {
                'name' : _('Purchase Property & Partial Payment'),
                'type' : 'ir.actions.act_window',
                'view_type' : 'form',
                'view_mode' : 'form',
                'res_model' : 'property.buy.contract',
                'view_id' : view_id.id,
                'target' : 'new',
                'context' : {
                            'property_id' : self.id,
                            'property_price':property_price,
                            'purchaser_id':self.env.user.partner_id.id,
                                },
            }
        return buy_property_data
                
    def reserve_property(self):

        if self.property_book_for != 'rent':
            raise UserError(_("This property only allow for sale..!"))
        if self.rent_price <= 0 or self.deposite <= 0:
            raise UserError(_("Please enter valid property rent or deposite price for (%s)..!") % self.name)
        view_id = self.env.ref('equip3_property_operation_contract.property_rent_contract_wizard')

        if view_id:
            book_property_data = {
                'name' : _('Reserve Property & Contract Configure'),
                'type' : 'ir.actions.act_window',
                'view_type' : 'form',
                'view_mode' : 'form',
                'res_model' : 'property.rent.contract',
                'view_id' : view_id.id,
                'target' : 'new',
                'context' : {
                            'property_id' :self.id,
                            'renter_id':self.user_id.id or self.env.user.id,
                            'deposite':self.deposite,
                                },
            }
        return book_property_data
    
class Agreement(models.Model):
    _inherit = 'agreement'
    
    property_id = fields.Many2one('product.product', string='Property', domain=[('is_property', '=', True)])

