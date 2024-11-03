from odoo import fields, models, api, _

class SetuRFMSegment(models.Model):
    _inherit = 'setu.rfm.segment'

    def open_customer(self):
        kanban_view_id = self.env.ref('equip3_sale_masterdata.equip_res_partner_kanban_view').id
        tree_view_id = self.env.ref('base.view_partner_tree').id
        form_view_id = self.env.ref('base.view_partner_form').id
        report_display_views = [(kanban_view_id, 'kanban'), (form_view_id, 'form'), (tree_view_id, 'tree')]
        return {
            'name': _('Customers'),
            'domain': [('id', 'in', self.partner_ids.ids)],
            'res_model': 'res.partner',
            'view_mode': "kanban,form,tree",
            'type': 'ir.actions.act_window',
            'context': {'search_default_customer': 1},
            'views': report_display_views,
        }
