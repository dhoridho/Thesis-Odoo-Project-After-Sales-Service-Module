# -*- coding: utf-8 -*-
# Copyright (C) Softhealer Technologies.

from odoo import fields, models, _
from odoo.exceptions import UserError

FIELD_TYPES = [(key, key) for key in sorted(fields.Field.by_type)]


class ShCreateAction(models.Model):
    _name = 'sh.activity.dynamic.action'
    _description = 'Sh Activity Create Action'

    name = fields.Char("Action Name", required=True, index=True)
    model_id = fields.Many2one('ir.model', string='Applies To', required=True, index=True, ondelete='cascade',
                               help="The model this field belongs to")
    sh_group_ids = fields.Many2many('res.groups', string='Groups')
    action_id = fields.Many2one(
        'ir.actions.act_window', string="Related Action")

    def add_action_to_model(self):
        if not self.model_id:
            raise UserError(_("Please Select Model."))
        vals = {}
        vals['type'] = 'ir.actions.act_window'
        vals['name'] = self.name
        vals['res_model'] = 'sh.mail.activity'
        vals['binding_model_id'] = self.model_id.id
        vals['binding_type'] = 'action'
        vals['target'] = 'new'
        vals['view_mode'] = 'form'
        vals['domain'] = "[]"
        if self.sh_group_ids:
            vals['groups_id'] = [(6,0,self.sh_group_ids.ids)]
        action_id = self.env['ir.actions.act_window'].sudo().create(vals)
        self.write({'action_id': action_id.id})

    def remove_action_to_model(self):
        if self.action_id:
            self.action_id.unlink()
