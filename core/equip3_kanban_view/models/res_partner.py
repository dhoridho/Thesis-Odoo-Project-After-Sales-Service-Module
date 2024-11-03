import json
from odoo import models, fields, api, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def return_action_to_open(self):
        self.ensure_one()
        action_xml_id = self.env.context.get('xml_id')
        field_name = self.env.context.get('field_name')

        action = self.env['ir.actions.actions']._for_xml_id(action_xml_id)
        context = eval(action.get('context', '').strip() or '{}', self.env.context)

        new_context = {}
        for key, value in context.items():
            if not key.startswith('search_default_'):
                new_context[key] = value
        
        action['context'] = json.dumps(new_context, default=str)
        action['domain'] = [(field_name, '=', self.id)]
        return action
