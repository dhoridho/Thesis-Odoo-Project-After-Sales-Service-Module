from odoo import models, fields, api, _
from odoo.addons.evo_bill_of_material_revised.models.mrp_production import MrpProduction as EvoMrpProduction


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    def _register_hook(self):
        def make_onchange_product_id():
            @api.onchange('product_id', 'picking_type_id', 'company_id')
            def onchange_product_id(self):
                return super(EvoMrpProduction, self).onchange_product_id()
            return onchange_product_id
        EvoMrpProduction._patch_method('onchange_product_id', make_onchange_product_id())
        return super(MrpProduction, self)._register_hook()
