from odoo import models, api
import json


class KSDashboardNinja(models.Model):
    _inherit = 'ks_dashboard_ninja.board'
    
    @api.model
    def create(self, vals):
        record = super(KSDashboardNinja, self).create(vals)

        menu_mrp_root = self.env.ref('mrp.menu_mrp_root')
        if menu_mrp_root:
            if menu_mrp_root.id == record.ks_dashboard_top_menu_id.id and record.ks_gridstack_config:
                config = json.loads(record.ks_gridstack_config)
                new_config = {}
                for item_id, values in config.items():
                    if isinstance(item_id, str):
                        item_id = self.env.ref(item_id).id
                    new_config[item_id] = values
                record.ks_gridstack_config = json.dumps(new_config)
        return record
