#-*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date, datetime, timedelta as td
from odoo.exceptions import UserError


class VaccinationGroupLine(models.Model):
    _name = 'vaccination.group.line'
    _description = "Vaccination Group Line"

    group_id = fields.Many2one('vaccination.group', 'Group')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    date_due_day = fields.Integer('Days to add',help="Days to add for next date")


class VaccinationGroup(models.Model):
    _name = 'vaccination.group'
    _description = "Vaccination Group"

    name = fields.Char(string='Group Name', required=True)
    group_line = fields.One2many('vaccination.group.line', 'group_id', string='Medicament line')


class ACSVaccination(models.Model):
    _name = 'acs.vaccination'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin']
    _description = "Vaccination"

    STATES = {'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    name = fields.Char(size=256, string='Name', tracking=True)
    vaccine_lot = fields.Char(size=256, string='Lot Number', states=STATES, tracking=True,
        help='Please check on the vaccine (product) production lot numberand'\
        ' tracking number when available !')
    patient_id = fields.Many2one('hms.patient', string='Patient', required=True, states=STATES, tracking=True)
    product_id = fields.Many2one('product.product', 'Vaccination', required=True, 
        domain=[('hospital_product_type', '=', "vaccination")], states=STATES,
        help='Vaccine Name. Make sure that the vaccine (product) has all the'\
        ' proper information at product level. Information such as provider,'\
        ' supplier code, tracking number, etc.. This  information must always'\
        ' be present. If available, please copy / scan the vaccine leaflet'\
        ' and attach it to this record')
    dose = fields.Integer(string='Dose #', states=STATES)
    observations = fields.Char(string='Observations', states=STATES)
    next_dose_date = fields.Datetime(string='Next Dose Date', states=STATES)
    due_date = fields.Date('Due Date', states=STATES)
    given_date = fields.Date('Given Date', states=STATES)
    batch_image = fields.Binary('Batch Photo', states=STATES)
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('to_invoice', 'To Invoice'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='State', default='scheduled', tracking=True)
    invoice_id = fields.Many2one('account.move', string='Invoice', ondelete='cascade', copy=False)
    physician_id = fields.Many2one('hms.physician', ondelete='restrict', string='Physician', 
        index=True, states=STATES, tracking=True)
    move_id = fields.Many2one('stock.move', string='Stock Move')
    company_id = fields.Many2one('res.company', ondelete='restrict', states=STATES,
        string='Hospital', default=lambda self: self.env.user.company_id.id)

    def action_done(self):
        if self.env.user.company_id.vaccination_invoicing:
            self.state = 'to_invoice'
        else:
            self.state = 'done'
        self.given_date = fields.Date.today()
        if not self.move_id:
            self.consume_vaccine()

    def action_cancel(self):
        self.state = 'cancel'

    def action_shedule(self):
        self.state = 'scheduled'

    def unlink(self):
        for rec in self:
            if rec.state not in ['cancel']:
                raise UserError(_('Record can be deleted only in Cancelled state.'))
        return super(ACSVaccination, self).unlink()
 
    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('acs.vaccination') or 'New Vaccination'
        return super(ACSVaccination, self).create(values)

    def action_create_invoice(self):
        product_id = self.product_id
        if not product_id:
            raise UserError(_("Please Set Product first."))
        product_data = [{'product_id': product_id}]
        inv_data = {
            'physician_id': self.physician_id and self.physician_id.id or False,
        }
        invoice = self.acs_create_invoice(partner=self.patient_id.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        self.invoice_id = invoice.id
        if self.state == 'to_invoice':
            self.state = 'done'

    def view_invoice(self):
        invoices = self.mapped('invoice_id')
        action = self.acs_action_view_invoice(invoices)
        return action

    def consume_vaccine(self):
        for rec in self:
            if not rec.company_id.vaccination_usage_location:
                raise UserError(_('Please define a Vaccination location where the consumables will be used.'))
            if not rec.company_id.vaccination_stock_location:
                raise UserError(_('Please define a Vaccination location from where the consumables will be taken.'))

            dest_location_id  = rec.company_id.vaccination_usage_location.id
            source_location_id  = rec.company_id.vaccination_stock_location.id
            move = self.consume_material(source_location_id, dest_location_id,
                {
                    'product': rec.product_id,
                    'qty': 1,
                })
            move.vaccination_id = rec.id
            rec.move_id = move.id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: