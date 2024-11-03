# -*- coding: utf-8 -*-

from odoo import fields, models, api, SUPERUSER_ID

class ResPartner(models.Model):
    _inherit = "res.partner"

    commission_role_id = fields.Many2one('acs.commission.role', string='Role')
    commission_ids = fields.One2many('acs.hms.commission', 'partner_id', 'Business Commission')
    provide_commission = fields.Boolean('Give Commission')
    commission_percentage = fields.Float('Commission Percentage')
    commission_rule_ids = fields.One2many("acs.commission.rule", "partner_id", string="Commission Rules")

    def commission_action(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_commission.acs_hms_commission_action")
        action['domain'] = [('partner_id','=',self.id)]
        action['context'] = {'default_partner_id': self.id, 'search_default_not_invoiced': 1}
        return action


class Physician(models.Model):
    _inherit = "hms.physician"

    def commission_action(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_hms_commission.acs_hms_commission_action")
        action['domain'] = [('partner_id','=',self.partner_id.id)]
        action['context'] = {'default_partner_id': self.partner_id.id, 'search_default_not_invoiced': 1}
        return action


class Appointment(models.Model):
    _inherit = "hms.appointment"

    def create_invoice(self):
        res = super(Appointment, self).create_invoice()
        for rec in self:
            rec.invoice_id.onchange_total_amount()
            rec.invoice_id.onchange_ref_physician()
            rec.invoice_id.onchange_physician()
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: