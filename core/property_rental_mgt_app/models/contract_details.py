# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta

class RentContract(models.Model):
    _name = 'contract.contract'
    _description = 'Contract'

    name = fields.Char("Name", required=True)
    contract_type = fields.Selection([('monthly',"Monthly"),('yearly',"Yearly")], default="monthly")
    month = fields.Integer("#Month", default=1)
    year = fields.Integer('#Year',default=1)

    @api.model
    def create(self, vals):
        res = super(RentContract,self).create(vals)
        if res:
            if res.contract_type == 'monthly':
                if res.month <= 0:
                    raise UserError(_("Please enter valid month in number...!"))
            if res.contract_type == 'yearly':
                if res.month <= 0:
                    raise UserError(_("Please enter valid year in number...!"))
        return res

class ContractDetails(models.Model):
    _name = 'contract.details'
    _description = "Contract Details"

    name = fields.Char()
    contract_id = fields.Many2one('contract.contract', required=True)
    date = fields.Date("Current Date",default=datetime.today().date())
    from_date = fields.Date("Start Date", required=True)
    to_date = fields.Date("Expired Date", required=True)
    property_id = fields.Many2one('product.product', required=True, domain=[('is_property','=',True),('property_book_for','=','rent'),('state','!=','reserve')])
    partner_id = fields.Many2one('res.users', string="Renter", required=True)
    renewal_date = fields.Date("Renewal Date")
    owner_id = fields.Many2one('res.partner', string="Owner", required=True)
    rent_price = fields.Float(readonly=True)
    deposite = fields.Float("Deposite Amount", required=True)
    state = fields.Selection([('new',"New"),('running',"Running"),('expire',"Expire"),('cancel','Cancelled')], default="new")
    contract_month = fields.Integer("Contract Month")

    @api.model
    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('contract.details') or _('New')
        result = super(ContractDetails, self).create(vals)
        return result

    def unlink(self):
        for line in self:
            if line.state != 'new':
                raise UserError(_('You cannot delete property contract (name: %s)') % (line.name,))
        return super(ContractDetails, self).unlink()

    def expired_contract_remainder(self):
        today_date = datetime.today().date()
        expired_contract = self.search([('to_date','<=',today_date)])
        new_contract = self.search([('from_date','<=',today_date),('to_date','>',today_date),('state','=','new')])
        for rec in new_contract:
            rec.write({'state':'running'})
        for record in expired_contract:
            record.write({'state':'expire'})
            template_id = self.env.ref('property_rental_mgt_app.rental_contract_template')
            auther = record.owner_id
            template_id.sudo().with_context(auther=auther).send_mail(record.id, force_send=True)
        return True

    def monthly_maintainance_remainder(self):
        today_date = datetime.today().date()
        running_contract = self.search([('state','=','running')])
        for rec in running_contract:
            if rec.property_id.rent_unit == 'monthly':
                from_date = rec.from_date + relativedelta(months=1)
                if from_date == today_date:
                    template_id = self.env.ref('property_rental_mgt_app.monthly_maintainance_template')
                    auther = rec.property_id.salesperson_id
                    template_id.sudo().with_context(auther=auther).send_mail(rec.id, force_send=True)
            if rec.property_id.rent_unit == 'yearly':
                from_date = rec.from_date + relativedelta(years=1)
                if from_date == today_date:
                    template_id = self.env.ref('property_rental_mgt_app.yearly_maintainance_template')
                    auther = rec.property_id.salesperson_id
                    template_id.sudo().with_context(auther=auther).send_mail(rec.id, force_send=True)
        return True

    def create_renew_contract(self):
        view_id = self.env.ref('property_rental_mgt_app.renew_contract_wizard')
        if view_id:
            renew_contract_data = {
                'name' : _('Renew Contract Configure'),
                'type' : 'ir.actions.act_window',
                'view_type' : 'form',
                'view_mode' : 'form',
                'res_model' : 'renew.contract',
                'view_id' : view_id.id,
                'target' : 'new',
                'context' : {
                            'rent_price':self.rent_price,
                            'contract_id':self.contract_id.id,
                            'renter_id':self.partner_id.id,
                            'owner_id':self.owner_id.id,
                            'property_id':self.property_id.id,
                            'name':self.name,
                            'parent_id':self.id,
                             },
            }
        return renew_contract_data

    def cancel_contract(self):
        for record in self:
            record.property_id.state = 'rent'
            record.state = 'cancel'
            history_ids = self.env['renter.history'].search([('contract_id','=', record.id)], limit=1)
            history_ids.state = 'cancel'
            history_ids.is_invoice = True

