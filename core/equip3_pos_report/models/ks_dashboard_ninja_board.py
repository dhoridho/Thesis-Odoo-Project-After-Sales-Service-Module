# -*- coding: utf-8 -*-

import json 
from odoo import fields, models, api

class KSDashboardNinja(models.Model):
    _inherit = 'ks_dashboard_ninja.board'

    ks_dashboard_menu_icon_class = fields.Char(string="Equip Icon Class")

    @api.model
    def create(self, vals):
        record = super(KSDashboardNinja, self).create(vals)
        if 'ks_dashboard_top_menu_id' in vals and 'ks_dashboard_menu_name' in vals:
            if record.ks_dashboard_menu_id:
                record.ks_dashboard_menu_id.write({
                        'equip_icon_class': vals.get('ks_dashboard_menu_icon_class',''),
                    })
        return record

    def write(self, vals):
        record = super(KSDashboardNinja, self).write(vals)
        for rec in self:
            if 'ks_dashboard_menu_icon_class' in vals:
                rec.ks_dashboard_menu_id.sudo().equip_icon_class = vals['ks_dashboard_menu_icon_class']
        return record


    @api.model
    def ks_fetch_dashboard_data(self, ks_dashboard_id, ks_item_domain=False):
        ks_dashboard_rec = self.browse(ks_dashboard_id)
        xml_data = ks_dashboard_rec.get_external_id()
        if xml_data.get(ks_dashboard_rec.id) == 'equip3_pos_report.pos_dashboard':
            template_data = json.loads(ks_dashboard_rec.ks_gridstack_config)
            ks_gridstack_config = {}
            for item_data in template_data:
                if type(item_data) is dict:
                    try:
                        dashboard_item = self.env.ref(item_data['item_id'])
                        ks_gridstack_config[dashboard_item.id] = item_data['data']
                    except:
                        break
            if ks_gridstack_config:
                ks_gridstack_config = json.dumps(ks_gridstack_config)
                ks_dashboard_rec.sudo().write({'ks_gridstack_config':ks_gridstack_config})
        record = super(KSDashboardNinja, self).ks_fetch_dashboard_data(ks_dashboard_id,ks_item_domain)
        return record
