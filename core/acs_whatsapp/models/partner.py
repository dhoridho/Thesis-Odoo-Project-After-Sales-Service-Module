# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner','acs.whatsapp.mixin']

    def _count_whatsapp(self):
        Announcement = self.env['acs.whatsapp.announcement']
        for rec in self:
            rec.whatsapp_count = len(rec.whatsapp_ids.ids)
            rec.whatsapp_announcement_count = Announcement.search_count([('partner_ids','in',rec.id)])

    whatsapp_ids = fields.One2many('acs.whatsapp.message', 'partner_id', string='whatsapp')
    whatsapp_count = fields.Integer(compute="_count_whatsapp", string="#whatsapp Count")
    whatsapp_announcement_count = fields.Integer(compute="_count_whatsapp", string="#whatsapp Announcement Count")

    def action_acs_whatsapp(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_whatsapp.action_acs_whatsapp")
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {
            'default_partner_id': self.id,
            'default_mobile': self.mobile,
        }
        return action

    def action_acs_whatsapp_announcement(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_whatsapp.action_whatsapp_announcement")
        action['domain'] = [('partner_ids', 'in', self.id)]
        action['context'] = { 'default_partner_ids': [(6, 0, [self.id])] }
        return action

    def whatsapp_chat_history(self):
        if not self.mobile:
            raise UserError(_("No Mobile no linked with Record."))     
        return self.acs_whatsapp_chat_history(self, self.mobile)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: