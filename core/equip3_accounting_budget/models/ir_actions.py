from odoo import api, fields, models, tools
from collections import defaultdict
from odoo.exceptions import MissingError, UserError, ValidationError, AccessError


class IrActions(models.Model):
    _inherit = 'ir.actions.actions'


    @api.model
    @tools.ormcache('frozenset(self.env.user.groups_id.ids)', 'model_name')
    def get_bindings(self, model_name):
        """ Retrieve the list of actions bound to the given model.

           :return: a dict mapping binding types to a list of dict describing
                    actions, where the latter is given by calling the method
                    ``read`` on the action record.
        """
        # DLE P19: Need to flush before doing the SELECT, which act as a search.
        # Test `test_bindings`
        self.flush()
        cr = self.env.cr
        query = """ SELECT a.id, a.type, a.binding_type
                    FROM ir_actions a, ir_model m
                    WHERE a.binding_model_id=m.id AND m.model=%s
                    ORDER BY a.id """
        cr.execute(query, [model_name])
        IrModelAccess = self.env['ir.model.access']

        # discard unauthorized actions, and read action definitions
        result = defaultdict(list)
        user_groups = self.env.user.groups_id
        for action_id, action_model, binding_type in cr.fetchall():
            try:
                action = self.env[action_model].sudo().browse(action_id)
                action_groups = getattr(action, 'groups_id', ())
                action_model = getattr(action, 'res_model', False)
                if action_groups and not action_groups & user_groups:
                    # the user may not perform this action
                    continue
                if action_model and not IrModelAccess.check(action_model, mode='read', raise_exception=False):
                    # the user won't be able to read records
                    continue
                if action.read():
                    result[binding_type].append(action.read()[0])
            except (AccessError, MissingError):
                continue

        # sort actions by their sequence if sequence available
        if result.get('action'):
            result['action'] = sorted(result['action'], key=lambda vals: vals.get('sequence', 0))
        return result