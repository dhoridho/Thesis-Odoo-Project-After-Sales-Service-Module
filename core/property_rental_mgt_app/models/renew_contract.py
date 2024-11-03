# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date,datetime
from dateutil.relativedelta import relativedelta

class RenewContract(models.TransientModel):
    _name = 'renew.contract'
    _description = "Renew Contract"

    name = fields.Char()
    contract_id = fields.Many2one('contract.contract', readonly=True)
    property_id = fields.Many2one('product.product', readonly=True, domain=[('is_property','=',True)])
    rent_price = fields.Float(readonly=True)
    renter_id = fields.Many2one('res.users', readonly=True)
    owner_id = fields.Many2one('res.partner', readonly=True)
    deposite = fields.Float(string="Total Rent", required=True, readonly=True)
    from_date = fields.Date(string="From Date", required=True)
    to_date = fields.Date(string="Expired Date", required=True, help="Default expired date automatically set for one month after start date. ")
    date = fields.Date("Current Date", default=fields.Date.today(), readonly=True)
    renewal_date = fields.Date("Renew Date", required=True)
    state = fields.Selection([('running',"Renew"),('expire',"Expire")], default="running")
    month = fields.Integer()

    @api.onchange('from_date')
    def check_contract_date(self):
        if self.from_date:
            if self.from_date < date.today() or self.property_id.property_avl_from > self.from_date:
                return {
                        'warning': {'title': 'Warning!', 'message': 'Please enter valid contract start date...!'},
                        'value': {'from_date': None}
                        }
            self.to_date = self.from_date + relativedelta(months=self.month)
            self.renewal_date = self.to_date

    # get rent Property details.
    @api.model
    def default_get(self,default_fields):
        res = super(RenewContract, self).default_get(default_fields)
        ctx = self._context
        parent_contract  = ctx.get('parent_id')
        parent_id = self.env['contract.details'].browse(parent_contract)
        property_data = {
            'deposite':parent_id.deposite,
            'month':parent_id.contract_month,
            'contract_id':parent_id.contract_id.id,
            'name':ctx.get('name'),
            'property_id':ctx.get('property_id'),
            'rent_price':ctx.get('rent_price'), 
            'renter_id':ctx.get('renter_id'), 
            'owner_id':ctx.get('owner_id')
        }
        res.update(property_data)
        return res

    def update_rent_contract(self):
        if self.deposite < 1:
            raise UserError(_('Please enter valid deposite amount...!'))
        contract_id = self.env['contract.details'].browse(self._context.get('parent_id'))
        contract_id.write({'deposite':self.deposite, 'date':self.date, 'from_date':self.from_date, 'to_date':self.to_date, 'renewal_date':self.renewal_date,'state':self.state})
        contract_id.property_id.write({'renter_history_ids':[(0,0,{'deposite':self.deposite,'reference':self.contract_id.name,'property_id':self.property_id.id,'owner_id':self.owner_id.id, 'state':"avl", 'rent_price':self.rent_price, 'renter_id':self.renter_id.id, 'date':fields.Date.today(), 'from_date':self.from_date, 'to_date':self.to_date, 'property_id':self.property_id.id})]})
