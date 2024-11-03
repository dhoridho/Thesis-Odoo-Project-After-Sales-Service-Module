from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError, Warning, AccessError, AccessDenied, MissingError, RedirectWarning
from datetime import datetime, date, timedelta
import pytz
import json


class RecurringMaintenance(models.Model):
    _name = 'property.maintenance.recurring'
    _description = 'Model for Recurring Maintenance'

    name = fields.Char(string='Maintenance Name', required=True)
    list_property_ids = fields.One2many(comodel_name='property.maintenance.listproperty', inverse_name='recurring_id', string='Property')
    maintenance_cost = fields.Float(string='Maintenance Cost', required=True)
    responsible = fields.Many2one('res.partner', string='Responsible', required=True)
    operation = fields.Selection([('service', 'Service'), ('repair', 'Repair')], string='Operation', required=True)
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
    next_date = fields.Date(string='Next Maintenance')
    frequency = fields.Integer(string='Frequency', required=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('cancel', 'Cancelled'),
        ('done', 'Done'),
    ], string='State', readonly=True,default='draft')
    description = fields.Text(string='Description')
    maintenance_count = fields.Integer(compute='_compute_maintenance_count', string='Maintenance Count')
    maintenance_type_id = fields.Many2one(comodel_name='property.maintenance.type', string='Maintenance Type', required=True)
    maintenance_schedule = fields.Selection(string='Maintenance Schedule', selection=[('daily', 'Daily'), ('monthly', 'Monthly'), ('yearly', 'Yearly')], required=True)

    def _compute_maintenance_count(self):
        for rec in self:
            rec.maintenance_count = self.env['property.maintanance'].search_count([('recurring_id', '=', rec.id)])

    #check date error
    @api.constrains('start_date', 'end_date', 'frequency')
    def _check_date(self):
        
        delta = self.end_date - self.start_date

        if self.start_date > self.end_date or self.start_date == self.end_date:
            raise ValidationError('Start Date must be less than End Date')
        
        if self.end_date <= self.get_today():
            raise ValidationError('End Date must be greater than today')

        if delta.days < self.frequency:
            raise ValidationError('Frequency must be less than the difference between Start Date and End Date')

    def _check_frequency(self):
        if self.frequency <= 0:
            raise ValidationError('Frequency must be greater than 0')
    
    @api.model
    def create(self, vals):
        res = super(RecurringMaintenance, self).create(vals)
        self.create_maintenance()
        return res

    def write(self, vals):
        res = super(RecurringMaintenance, self).write(vals)
        if vals.get('state') == 'active':
            if self.start_date <= self.get_today():
                self.next_date = self.get_today()
                self.create_maintenance()
            elif self.start_date > self.get_today():
                self.next_date = self.start_date
        return res

    def create_maintenance(self):
        rec_maintenance = self.env['property.maintenance.recurring'].search([('start_date', '!=', False), ('end_date', '!=', False), ('frequency', '!=', False)])
        # raise Warning(self.get_today())
        for rec in rec_maintenance:
            rec_id = self.env['property.maintanance'].search([('recurring_id', '=', rec.id),('date', '=', self.get_today())])
            if not rec_id and rec.state == 'active':
                if rec.start_date <= self.get_today() and rec.end_date >= self.get_today():
                    if rec.start_date == self.get_today() or rec.next_date == self.get_today():
                        for rec_list in rec.list_property_ids:
                            rec_maintenance_id = self.env['property.maintanance'].create({
                                'name': rec.name,
                                'property_id': rec_list.property_id.id,
                                'recurring_id': rec.id,
                                'maintain_cost': rec.maintenance_cost,
                                'responsible_id': rec.responsible.id,
                                'description': rec.description,
                                'operation': rec.operation,
                                'date': self.get_today(),
                                'maintenance_type_id': rec.maintenance_type_id.id,
                                'contract_ids': [(6, 0, rec_list.contract_ids.ids)],
                            })
                            
                            if rec.maintenance_schedule == 'daily':
                                next_date = self.get_today() + timedelta(days=rec.frequency)
                            elif rec.maintenance_schedule == 'monthly':
                                next_date = self.get_today() + timedelta(months=rec.frequency)
                            elif rec.maintenance_schedule == 'yearly':
                                next_date = self.get_today() + timedelta(years=rec.frequency)

                            rec.next_date = next_date
                            if rec.next_date > rec.end_date:
                                rec.state = 'done'

    def get_today(self):
        tz = pytz.timezone('Asia/Singapore')
        today = datetime.now(tz).date()
        return today

    def action_move_active(self):
        self.state = 'active'
        self.create_maintenance()
    
    def action_move_cancel(self):
        self.state = 'cancel'
        self.next_date = False
    
    def action_move_draft(self):
        self.state = 'draft'
    
    def maintenance_property_link(self):
        return {
            'name': 'Maintenance',
            'view_mode': 'tree,form',
            'res_model': 'property.maintanance',
            'type': 'ir.actions.act_window',
            'domain': [('recurring_id', '=', self.id)],
        }

RecurringMaintenance()

class ListMaintenanceProperty(models.Model):
    _name = 'property.maintenance.listproperty'
    _description = 'Model for List Property Maintenance'

    recurring_id = fields.Many2one(comodel_name='property.maintenance.recurring', string='Recurring Maintenance')
    property_id = fields.Many2one(comodel_name='product.product', string='Property', required=True, domain=[('is_property', '=', True), ('property_book_for', '=', 'rent'), ('is_reserved', '=', True)])
    name = fields.Char(string='Name')
    contract_ids = fields.Many2many(comodel_name='agreement', string='Contract', required=True)
    contract_ids_domain = fields.Char(string='Contract Domain', compute='_compute_contract_ids_domain')

    @api.depends('property_id')
    def _compute_contract_ids_domain(self):
        for rec in self:
            contract_ids = self.env['agreement'].search([('property_id', '=', rec.property_id.id)])
            if contract_ids:
                rec.contract_ids_domain = json.dumps([('id', 'in', contract_ids.ids)])
            else:
                rec.contract_ids_domain = json.dumps([('id', '=', 0)])

    

class MaintenanceProperty(models.Model):
    _inherit = 'property.maintanance'

    recurring_id = fields.Many2one(comodel_name='property.maintenance.recurring', string='Recurring Maintenance')
    contract_ids = fields.Many2many(comodel_name='agreement', string='Contract', required=True)
    invoice_id = fields.Many2many(comodel_name='account.move', string='Invoice Status', readonly=True)
 
    @api.model
    def write(self, vals):
        res = super(MaintenanceProperty, self).write(vals)
        if vals.get('state') == 'invoice':
            self.property_id.maintenance_spent = self.property_id.maintenance_spent + self.maintain_cost
        if vals.get('state') == 'cancel':
            if self.property_id.maintenance_spent > 0:
                self.property_id.maintenance_spent = self.property_id.maintenance_spent - self.maintain_cost

    @api.depends('invoice_id')
    # override to bypass calculate o2m invoice
    def _compute_invoice_count(self):
        self.invoice_count = self.env['account.move'].search_count([('id','=',self.invoice_id.ids)])

    # override to bypass invoice from contract and no longer from property
    def create_maintanance_invoice(self):
        product_id = self.property_id
        # Search for the income account
        if product_id.property_account_income_id:
            income_account = product_id.property_account_income_id.id
        elif product_id.categ_id.property_account_income_categ_id:
            income_account = product_id.categ_id.property_account_income_categ_id.id
        else:
            raise UserError(_('Please define income '
                              'account for this product: "%s" (id:%d).')
                            % (product_id.name, product_id.id))

        for contract in self.contract_ids:
            vals  = {
                'property_maintenance_id': self.id,
                'property_id':self.property_id.id,
                'move_type': 'out_invoice',
                'invoice_origin':self.name,
                'partner_id': self.responsible_id.id,
                'invoice_date_due':self.date,
                'invoice_date':self.date,
                'invoice_user_id':self.property_id.salesperson_id.id,
                'invoice_line_ids': [(0,0,{
                    'name':self.name + ' / ' + contract.name,
                    'product_id':self.property_id.id,
                    'account_id': income_account,
                    'price_unit': self.maintain_cost})],
                }
            invoice_id = self.env["account.move"].create(vals)
            if invoice_id:
                self.invoice_id = [(4, invoice_id.id)]
                self.state = "invoice"
                invoice_id.agreement_id = contract.id

    # override to bypass view o2m invoice
    def action_view_invoice(self):
        invoices = self.env['account.move'].search([('id','=',self.invoice_id.ids)])
        action = self.env.ref('account.action_move_out_invoice_type').read()[0]
        if len(invoices) > 0:
            action['domain'] = [('id', 'in', invoices.ids)]
            action['context'] = {'group_by': ['agreement_id']}
        else:
            action = {'type': 'ir.actions.act_window_close'}
        return action

    def button_cancel(self):
        invoice = self.env['account.move'].browse(self.invoice_id.ids).sudo().unlink()
        return super(MaintenanceProperty, self).button_cancel()