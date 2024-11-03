from datetime import datetime
from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError, Warning


class MaterialRequestWiz(models.TransientModel):
    _inherit = 'material.request.wiz'

    def _prepare_material_bd(self, val):
        res = super(MaterialRequestWiz, self)._prepare_material_bd(val)
        res['finish_good_id'] = val.finish_good_id.id

        return res

    def _prepare_material_cs(self, val):
        res = super(MaterialRequestWiz, self)._prepare_material_cs(val)
        res['finish_good_id'] = val.finish_good_id.id

        return res

    def _prepare_labour_bd(self, val):
        res = super(MaterialRequestWiz, self)._prepare_labour_bd(val)
        res['finish_good_id'] = val.finish_good_id.id

        return res

    def _prepare_labour_cs(self, val):
        res = super(MaterialRequestWiz, self)._prepare_labour_cs(val)
        res['finish_good_id'] = val.finish_good_id.id

        return res

    def _prepare_overhead_bd(self, val):
        res = super(MaterialRequestWiz, self)._prepare_overhead_bd(val)
        res['finish_good_id'] = val.finish_good_id.id

        return res

    def _prepare_overhead_cs(self, val):
        res = super(MaterialRequestWiz, self)._prepare_overhead_cs(val)
        res['finish_good_id'] = val.finish_good_id.id

        return res

    def _prepare_equipment_bd(self, val):
        res = super(MaterialRequestWiz, self)._prepare_equipment_bd(val)
        res['finish_good_id'] = val.finish_good_id.id

        return res

    def _prepare_equipment_cs(self, val):
        res = super(MaterialRequestWiz, self)._prepare_equipment_cs(val)
        res['finish_good_id'] = val.finish_good_id.id

        return res
        
    def prepare_product_lines(self, Job_cost_sheet, product_ids):
        res = super(MaterialRequestWiz, self).prepare_product_lines(Job_cost_sheet, product_ids)
        res['is_engineering'] = Job_cost_sheet.is_engineering

        return res

    
   