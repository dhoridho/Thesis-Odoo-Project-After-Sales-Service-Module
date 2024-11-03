from odoo import models, fields, api


class InternalTransfer(models.Model):
    _inherit = 'internal.transfer'

    def action_confirm(self):
        res = super(InternalTransfer, self).action_confirm()
        assembly_id = self.env.context.get('assembly_pop_back')
        if assembly_id and isinstance(assembly_id, int):
            assembly_object = self.env['assembly.production.record'].with_context(itr_pop_back=self.id)
            return assembly_object.browse(assembly_id).action_view_transfer_request()
        return res
