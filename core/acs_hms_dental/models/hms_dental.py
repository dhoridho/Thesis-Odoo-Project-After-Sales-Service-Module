# -*- coding: utf-8 -*-

from odoo import api, fields, models ,_
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta


class AcsDentalProcedure(models.Model):
    _name="acs.dental.procedure"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'acs.hms.mixin']
    _description = "Dental Procedure"
    _order = "id desc"

    STATES = {'cancel': [('readonly', True)], 'done': [('readonly', True)]}

    name = fields.Char(string="Name", states=STATES, tracking=True)
    patient_id = fields.Many2one('hms.patient', string='Patient', required=True, states=STATES, tracking=True)
    product_id = fields.Many2one('product.product', string='Procedure', domain=[('hospital_product_type','=','dental')], 
        change_default=True, ondelete='restrict', states=STATES, required=True)
    price_unit = fields.Float("Price", states=STATES)
    tooth_surface_ids = fields.Many2many('acs.tooth.surface', string='Surface', states=STATES)
    tooth_id = fields.Many2one('acs.hms.tooth', string='Tooth', required=True, states=STATES)
    invoice_id = fields.Many2one('account.move', string='Invoice', ondelete='cascade', states=STATES, copy=False)
    physician_id = fields.Many2one('hms.physician', ondelete='restrict', string='Physician', 
        index=True, states=STATES)
    state = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('running', 'Running'),
        ('done', 'Done'),
        ('cancel', 'Canceled'),
    ], string='State', default='scheduled', tracking=True)
    company_id = fields.Many2one('res.company', ondelete='restrict', states=STATES,
        string='Hospital', default=lambda self: self.env.user.company_id.id)
    date = fields.Datetime("Date")
    diseas_id = fields.Many2one('hms.diseases', 'Disease', states=STATES)
    description = fields.Text(string="Description")
    treatment_id = fields.Many2one('hms.treatment', 'Treatment', states=STATES)
    appointment_ids = fields.Many2many('hms.appointment', 'appointment_procedure_ids_rel', 'appointment_id', 'procedure_id', 'Appointments', states=STATES)

    @api.onchange('product_id')
    def product_id_change(self):
        if self.product_id:
            self.name = self.product_id.name_get()[0][1]
            self.price_unit = self.product_id.list_price

    def action_running(self):
        self.state = 'running'

    def action_schedule(self):
        self.state = 'scheduled'

    def action_done(self):
        self.state = 'done'

    def action_cancel(self):
        self.state = 'cancel'

    def unlink(self):
        for rec in self:
            if rec.state not in ['cancel']:
                raise UserError(_('Record can be deleted only in Canceled state.'))
        return super(AcsDentalProcedure, self).unlink()
 
    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].next_by_code('acs.dental.procedure') or 'New Dental Procedure'
        return super(AcsDentalProcedure, self).create(values)

    def action_create_invoice(self):
        product_id = self.product_id
        if not product_id:
            raise UserError(_("Please Set Product first."))
        product_data = [{
            'product_id': product_id, 
            'price_unit': self.price_unit
        }]
        inv_data = {
            'physician_id': self.physician_id and self.physician_id.id or False,
        }
        invoice = self.acs_create_invoice(partner=self.patient_id.partner_id, patient=self.patient_id, product_data=product_data, inv_data=inv_data)
        self.invoice_id = invoice.id

    def view_invoice(self):
        invoices = self.mapped('invoice_id')
        action = self.acs_action_view_invoice(invoices)
        return action

    def action_show_details(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_dental.action_acs_dental_procedure")
        action['context'] = {'default_patient_id': self.id}
        action['res_id'] = self.id
        action['views'] = [(self.env.ref('acs_hms_dental.view_acs_dental_procedure_form').id, 'form')]
        action['target'] = 'new'
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:   