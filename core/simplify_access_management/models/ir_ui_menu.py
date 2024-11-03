from odoo import fields, models, api, _
from odoo.http import request

class ir_ui_menu(models.Model):
    _inherit = 'ir.ui.menu'

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        ids = super(ir_ui_menu, self).search(args, offset=0, limit=None, order=order, count=False)

        # value = self._cr.execute("""select state from ir_module_module where name = 'simplify_access_management'""")
        # value = self._cr.fetchone()
        # value = value and value[0] or False
        # value = self.env['ir.module.module'].sudo().search([('name', '=', 'simplify_access_management')], limit=1)
        
        # value = value.state
        try:
            value = self._cr.execute("""select state from ir_module_module where name = 'simplify_access_management'""")
            value = self._cr.fetchone()
            value = value and value[0] or False
        except:
            value = 'installed'
        if value == 'installed':
            user = self.env.user
            # user.clear_caches()
            cids = self.env.companies.ids
            for menu_id in user.access_management_ids.filtered(lambda line: any(l_c_id in cids for l_c_id in line.company_ids.ids)).mapped('hide_menu_ids'):
                if menu_id in ids:
                    ids = ids - menu_id
            if offset:
                ids = ids[offset:]
            if limit:
                ids = ids[:limit]
            return len(ids) if count else ids
        else:
            return ids

