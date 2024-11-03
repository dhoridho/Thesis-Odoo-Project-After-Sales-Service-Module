# -*- encoding: utf-8 -*-
from odoo import api, fields, models, _


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner','acs.sms.mixin']

    def _count_sms(self):
        Announcement = self.env['acs.sms.announcement']
        for rec in self:
            rec.sms_count = len(rec.sms_ids.ids)
            rec.announcement_count = Announcement.search_count([('partner_ids','in',rec.id)])

    sms_ids = fields.One2many('acs.sms', 'partner_id', string='SMS')
    sms_count = fields.Integer(compute="_count_sms", string="#SMS Count")
    announcement_count = fields.Integer(compute="_count_sms", string="#SMS Announcement Count")

    def action_acs_sms(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_sms.action_acs_sms")
        action['domain'] = [('partner_id', '=', self.id)]
        action['context'] = {
            'default_partner_id': self.id,
            'default_mobile': self.mobile,
        }
        return action

    def action_acs_sms_announcement(self):
        action = self.env["ir.actions.actions"]._for_xml_id("acs_sms.action_sms_announcement")
        action['domain'] = [('partner_ids', 'in', self.id)]
        action['context'] = { 'default_partner_ids': [(6, 0, [self.id])] }
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: