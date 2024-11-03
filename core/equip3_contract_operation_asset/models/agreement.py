from odoo import models, fields, api, _


class Agreement(models.Model):
    _inherit = 'agreement'

    mro_count = fields.Integer(string="MRO Count", compute="_compute_mro_count")
    mwo_count = fields.Integer(string="MRO Count", compute="_compute_mwo_count")

    def _compute_mro_count(self):
        for agreement in self:
            agreement.mro_count = self.env["maintenance.repair.order"].search_count(
                [("agreement_id", "in", agreement.ids)]
            )

    def _compute_mwo_count(self):
        for agreement in self:
            agreement.mwo_count = self.env["maintenance.work.order"].search_count(
                [("agreement_id", "in", agreement.ids)]
            )

    def mwo_link(self):
        return {
            'name': 'Maintenance Work Order',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.work.order',
            'views': [
                (self.env.ref('equip3_contract_operation_asset.maintenance_wo_agreement_view_tree').id, 'tree'),
                (self.env.ref('equip3_asset_fms_operation.maintenance_work_order_view_form').id, 'form'),
            ],
            'domain': [('agreement_id', '=', self.id)],
            'context': {'default_agreement_id': self.id}
        }
    
    def mro_link(self):
        return {
            'name': 'Maintenance Repair Order',
            'type': 'ir.actions.act_window',
            'view_mode': 'tree,form',
            'res_model': 'maintenance.repair.order',
            'views': [
                (self.env.ref('equip3_contract_operation_asset.maintenance_ro_agreement_view_tree').id, 'tree'),
                (self.env.ref('equip3_asset_fms_operation.maintenance_repair_order_form_view').id, 'form'),
            ],
            'domain': [('agreement_id', '=', self.id)],
            'context': {'default_agreement_id': self.id}
        }
