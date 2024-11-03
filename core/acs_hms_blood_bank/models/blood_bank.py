# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AcsBloodRequisition(models.Model):
    _name = 'acs.blood.requisition'
    _description = 'Blood Requisition'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin']

    STATES = {'to_invoice': [('readonly', True)], 'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    @api.model
    def _get_service_id(self):
        service_product = False
        if self.env.user.company_id.acs_blood_requisition_product_id:
            service_product = self.env.user.company_id.acs_blood_requisition_product_id.id
        return service_product

    name = fields.Char(string='Name', copy=False, default="/", tracking=True)
    partner_id = fields.Many2one('res.partner', ondelete='cascade', 
        string='Contact', required=True, states=STATES)
    patient_id = fields.Many2one('hms.patient', ondelete='cascade', 
        string='Patient', states=STATES, tracking=True)
    blood_group = fields.Selection([
        ('A+', 'A+'),('A-', 'A-'),
        ('B+', 'B+'),('B-', 'B-'),
        ('AB+', 'AB+'),('AB-', 'AB-'),
        ('O+', 'O+'),('O-', 'O-')], string='Blood Group', states=STATES, tracking=True)
    lot_id = fields.Many2one('stock.production.lot', ondelete='restrict', string='Blood Bag Serial', 
        domain=[('is_blood_bag','=',True),('requisition_id','=',False)], states=STATES)
    user_id = fields.Many2one('res.users', ondelete='restrict', string='Responsible', 
        help="Responsible Person", default=lambda self: self.env.user, states=STATES, required=True)
    date = fields.Datetime('Date', default=fields.Datetime.now, states=STATES, required=True)
    is_outside = fields.Boolean('Is Outside', states=STATES)
    location = fields.Char('Location', states=STATES)
    remark = fields.Text('Remark', states=STATES)
    state = fields.Selection([
        ('draft','Draft'),
        ('running','Running'),
        ('to_invoice', 'To Invoice'),
        ('done','Donated'),
        ('cancel','Cancel')], default="draft", string="State", tracking=True)
    service_product_id = fields.Many2one('product.product', ondelete='restrict', 
        string='Blood Issuance Service', help="Blood Process Charge Service", 
        domain=[('type', '=', "blood")], default=_get_service_id, states=STATES)
    product_id = fields.Many2one('product.product', 'Blood Bag', required=True, 
        domain=[('hospital_product_type', '=', "blood")], states=STATES,
        help='Blood Bag Name. Make sure that the Blood Bag (product) has all the'\
        ' proper information at product level.')

    invoice_id = fields.Many2one('account.move', string='Invoice', ondelete='cascade', copy=False)
    physician_id = fields.Many2one('hms.physician', ondelete='restrict', string='Physician', 
        index=True, states=STATES, required=True, tracking=True)
    move_id = fields.Many2one('stock.move', string='Stock Move')
    company_id = fields.Many2one('res.company', ondelete='restrict', states=STATES,
        string='Hospital', default=lambda self: self.env.user.company_id.id)

    @api.onchange('patient_id')
    def onchange_patient(self):
        if self.patient_id:
            self.partner_id = self.patient_id.partner_id.id
            self.blood_group = self.patient_id.blood_group
        else:
            self.partner_id = False

    @api.model
    def create(self, values):
        if values.get('name', '/') == '/':
            values['name'] = self.env['ir.sequence'].next_by_code('acs.blood.requisition') or ''
        return super(AcsBloodRequisition, self).create(values)

    def unlink(self):
        for data in self:
            if data.state in ['done']:
                raise UserError(('You can not delete record in done state'))
        return super(AcsBloodRequisition, self).unlink()

    def action_running(self):
        self.state = 'running'

    def action_done(self):
        if self.env.user.company_id.acs_blood_requisition_invoicing:
            self.state = 'to_invoice'
        else:
            self.state = 'done'

        self.lot_id.requisition_id = self.id
        self.lot_id.donor_partner_id = self.partner_id.id
        self.partner_id.is_donor = True

    def action_cancel(self):
        self.state = 'cancel' 

    def action_create_invoice(self):
        product_id = self.service_product_id or self.env.user.company_id.acs_blood_requisition_product_id
        if not product_id:
            raise UserError(_("Please Set Service Product first for Blood Requisition in Configuration."))
        product_data = [{'product_id': product_id}]
        inv_data = {
            'physician_id': self.physician_id and self.physician_id.id or False,
        }
        invoice = self.acs_create_invoice(partner=self.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        self.invoice_id = invoice.id
        if self.state == 'to_invoice':
            self.state = 'done'

    def view_invoice(self):
        invoices = self.mapped('invoice_id')
        return self.acs_action_view_invoice(invoices)


class AcsBloodIssuance(models.Model):
    _name = 'acs.blood.issuance'
    _description = 'Blood Issuance'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin']

    STATES = {'to_invoice': [('readonly', True)], 'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    @api.model
    def _get_service_id(self):
        service_product = False
        if self.env.user.company_id.acs_blood_issuance_product_id:
            service_product = self.env.user.company_id.acs_blood_issuance_product_id.id
        return service_product

    name = fields.Char(size=256, string='Name', copy=False, readonly=True, default="/")
    partner_id = fields.Many2one('res.partner', ondelete='cascade', string='Contact', required=True, states=STATES)
    patient_id = fields.Many2one('hms.patient', ondelete='cascade', string='Patient', states=STATES)
    lot_id = fields.Many2one('stock.production.lot', ondelete='restrict', string='Blood Bag Serial', states=STATES)
    state = fields.Selection([
        ('draft','Draft'),
        ('to_invoice', 'To Invoice'),
        ('done','Issued'),
        ('cancel','Cancel')], default="draft", string="State", states=STATES)
    user_id = fields.Many2one('res.users', ondelete='restrict', string='Responsible', 
        help="Responsible Person", default=lambda self: self.env.user, states=STATES, required=True)
    date = fields.Datetime('Date', default=fields.Datetime.now, states=STATES, required=True)
    is_outside = fields.Boolean('Is Outside', states=STATES)
    location = fields.Char('Location', states=STATES)
    remark = fields.Text('Remark', states=STATES)

    service_product_id = fields.Many2one('product.product', ondelete='restrict', 
        string='Blood Issuance Service', help="Blood Process Charge Service", 
        domain=[('type', '=', "blood")], default=_get_service_id, states=STATES)
    product_id = fields.Many2one('product.product', 'Blood Bag', required=True, 
        domain=[('hospital_product_type', '=', "blood")], states=STATES,
        help='Blood Bag Name. Make sure that the Blood Bag (product) has all the'\
        ' proper information at product level.')
    invoice_id = fields.Many2one('account.move', string='Invoice', ondelete='cascade')
    physician_id = fields.Many2one('hms.physician', ondelete='restrict', string='Physician', 
        index=True, states=STATES, required=True)
    move_id = fields.Many2one('stock.move', string='Stock Move')
    company_id = fields.Many2one('res.company', ondelete='restrict', states=STATES,
        string='Hospital', default=lambda self: self.env.user.company_id.id)
    blood_group = fields.Selection([
        ('A+', 'A+'),('A-', 'A-'),
        ('B+', 'B+'),('B-', 'B-'),
        ('AB+', 'AB+'),('AB-', 'AB-'),
        ('O+', 'O+'),('O-', 'O-')], string='Blood Group', states=STATES, required=True)

    @api.onchange('patient_id')
    def onchange_patient(self):
        if self.patient_id:
            self.partner_id = self.patient_id.partner_id.id
        else:
            self.partner_id = False

    @api.model
    def create(self, values):
        if values.get('name', '/') == '/':
            values['name'] = self.env['ir.sequence'].next_by_code('acs.blood.issuance') or ''
        return super(AcsBloodIssuance, self).create(values)

    def unlink(self):
        for data in self:
            if data.state in ['done']:
                raise UserError(('You can not delete record in done state'))
        return super(AcsBloodIssuance, self).unlink()

    def consume_product(self):
        for rec in self:
            if not rec.company_id.blood_stock_location:
                raise UserError(_('Please define a Blood Bank Stock Usage Location where the consumables will be used.'))
            if not rec.company_id.blood_usage_location:
                raise UserError(_('Please define a Blood Bank Stock Location from where the product will be taken.'))

            dest_location_id  = rec.company_id.blood_usage_location.id
            source_location_id  = rec.company_id.blood_stock_location.id
            move = self.consume_material(source_location_id, dest_location_id,
                {
                    'product': rec.product_id,
                    'qty': 1,
                    'lot_id': rec.lot_id.id,
                })
            move.issuance_id = rec.id
            rec.move_id = move.id

    def action_done(self):
        if self.env.user.company_id.acs_blood_requisition_invoicing:
            self.state = 'to_invoice'
        else:
            self.state = 'done'
        if not self.move_id:
            self.consume_product()
        self.lot_id.issuance_id = self.id
        self.lot_id.receiver_partner_id = self.partner_id.id
        self.partner_id.is_receiver = True

    def action_cancel(self):
        self.state = 'cancel'

    def action_create_invoice(self):
        service_product_id = self.service_product_id or self.env.user.company_id.acs_blood_issuance_product_id
        if not service_product_id:
            raise UserError(_("Please Set Service Product first for Blood issuance in Configuration."))
        product_data = [{'product_id': service_product_id}]
        inv_data = {
            'physician_id': self.physician_id and self.physician_id.id or False,
        }
        invoice = self.acs_create_invoice(partner=self.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        self.invoice_id = invoice.id
        if self.state == 'to_invoice':
            self.state = 'done'

    def view_invoice(self):
        invoices = self.mapped('invoice_id')
        return self.acs_action_view_invoice(invoices)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: 