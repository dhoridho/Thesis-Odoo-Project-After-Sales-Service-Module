# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Appointment(models.Model):
    _inherit = 'hms.appointment'

    subscription_id = fields.Many2one("acs.hms.subscription", "Subscription", ondelete="restrict")

    @api.onchange("subscription_id")
    def onchange_subscription_id(self):
        if self.subscription_id:
            if self.subscription_id.acs_type=='full':
                self.no_invoice = True
            else:
                self.pricelist_id = self.subscription_id.pricelist_id and self.subscription_id.pricelist_id.id or False

    @api.onchange('patient_id')
    def onchange_patient_id(self):
        res = super(Appointment, self).onchange_patient_id()
        if self.patient_id:
            subscription = self.env['acs.hms.subscription'].sudo().search([('state','=','active'),('res_model_id.model','=','hms.appointment'),('patient_id','=',self.patient_id.id)], limit=1)
            self.subscription_id = subscription and subscription.id or False
        return res

    def appointment_done(self):
        res = super(Appointment, self).appointment_done()
        if self.subscription_id and self.subscription_id.remaining_service<=0:
            self.subscription_id.action_done()
        return res


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    subscription_id = fields.Many2one("acs.hms.subscription", "Subscription", ondelete="restrict")


class ACSPatient (models.Model):
    _inherit = "hms.patient"

    def _do_count(self):
        for rec in self: 
            rec.subscription_count = len(rec.subscription_ids)

    subscription_ids = fields.One2many("acs.hms.subscription", "patient_id", "Subscriptions")
    subscription_count = fields.Integer(string='# of Subscription', compute='_do_count', readonly=True)

    def action_view_subscriptions(self):
        subscriptions = self.subscription_ids
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_subscription.acs_hms_subscription_action")
        if len(subscriptions) > 1:
            action['domain'] = [('id', 'in', subscriptions.ids)]
        elif len(subscriptions) == 1:
            action['views'] = [(self.env.ref('acs_hms_subscription.acs_hms_subscription_form_view').id, 'form')]
            action['res_id'] = subscriptions.ids[0]
        action.update({'context': {'default_patient_id': self.id}})
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: