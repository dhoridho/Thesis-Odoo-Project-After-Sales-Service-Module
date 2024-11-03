from odoo import models, fields, api
from collections import defaultdict
import itertools
import logging

_logger = logging.getLogger(__name__)


def name_boolean_group(id):
    return 'in_group_' + str(id)

def name_selection_groups(ids):
    return 'sel_groups_' + '_'.join(str(it) for it in ids)


class UsersView(models.Model):
    _inherit = 'res.users'

    @api.model
    def action_update_res_groups_views(self):
        self.env['res.groups'].sudo()._update_user_groups_view()
        return {
		    'type': 'ir.actions.client',
		    'tag': 'reload',
		}

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super(UsersView, self).fields_get(allfields, attributes=attributes)
        # add reified groups fields
        Group = self.env['res.groups'].sudo()
        delete_central_kitchen = False
        delete_simple_manuf = False
        delete_manufacturing = False
        for app, kind, gs, category_name in Group.get_groups_by_application():
            if kind == 'selection':
                # 'User Type' should not be 'False'. A user is either 'employee', 'portal' or 'public' (required).
                selection_vals = [(False, '')]
                if app.xml_id == 'base.module_category_user_type':
                    selection_vals = []

                # FIXME: in Accounting, the groups in the selection are not
                # totally ordered, and their order therefore partially depends
                # on their name, which is translated!  So we generate all the
                # possible field names according to the partial order.
                gs_list = [gs]
                if app.xml_id == 'base.module_category_accounting_accounting':
                    # ranks = {0: [A, B], 2: [C], 3: [D]}
                    ranks = defaultdict(list)
                    for g in gs:
                        ranks[len(g.trans_implied_ids & gs)].append(g)
                    # perms = [[AB, BA], [C], [D]]
                    perms = [
                        [Group.concat(*perm) for perm in itertools.permutations(rank)]
                        for k, rank in sorted(ranks.items())
                    ]
                    # gs_list = [ABCD, BACD]
                    gs_list = [Group.concat(*perm) for perm in itertools.product(*perms)]

                for gs in gs_list:
                    field_name = name_selection_groups(gs.ids)
                    if allfields and field_name not in allfields:
                        continue

                    if self.env.company.central_kitchen and app.xml_id == 'equip3_kitchen_accessright_settings.module_simple_manufacturing':
                        delete_central_kitchen = field_name
                        continue
                    elif self.env.company.simple_manufacturing and app.xml_id == 'equip3_kitchen_accessright_settings.module_central_kitchen':
                        delete_simple_manuf = field_name
                        continue
                    elif app.xml_id == 'base.module_category_manufacturing_manufacturing':
                        delete_manufacturing = field_name
                        continue

                    # selection group field
                    tips = ['%s: %s' % (g.name, g.comment) for g in gs if g.comment]
                    res[field_name] = {
                        'type': 'selection',
                        'string': app.name or _('Other'),
                        'selection': selection_vals + [(g.id, g.name) for g in gs],
                        'help': '\n'.join(tips),
                        'exportable': False,
                        'selectable': False,
                    }
            else:
                # boolean group fields
                for g in gs:
                    field_name = name_boolean_group(g.id)
                    if allfields and field_name not in allfields:
                        continue
                    res[field_name] = {
                        'type': 'boolean',
                        'string': g.name,
                        'help': g.comment,
                        'exportable': False,
                        'selectable': False,
                    }
        if delete_central_kitchen and delete_central_kitchen in res:
            del res[delete_central_kitchen]
        if delete_simple_manuf and delete_simple_manuf in res:
            del res[delete_simple_manuf]
        if delete_manufacturing and delete_manufacturing in res:
            del res[delete_manufacturing]

        return res
