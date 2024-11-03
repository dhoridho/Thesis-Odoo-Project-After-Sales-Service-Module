from odoo import models, fields, api
from odoo.osv import expression


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def _boom(self, quantity, level=1, id=1, parent_id=0, data=None):
        self.ensure_one()

        if not data:
            data = []

        def _find(bom_line):
            for d in data:
                if d['bom_line_id'] == bom_line.id:
                    return self.env['mrp.bom'].browse(d['bom_id'])
            return bom_line.child_bom_id
        
        boms, lines = self.explode(self.product_id, quantity / self.product_qty, picking_type=self.picking_type_id)

        material_values = []
        next_id = id
        for bom_line, line_data in lines:
            child_bom_id = _find(bom_line)

            if child_bom_id and child_bom_id.type == 'phantom' or bom_line.product_id.type not in ['product', 'consu']:
                continue

            operation_id = bom_line.operation_id.id or line_data['parent_line'] and line_data['parent_line'].operation_id.id

            material_values += [{
                'id': next_id,
                'level': level,
                'parent_id': parent_id,
                'bom_line_id': bom_line.id,
                'product_id': bom_line.product_id.id,
                'product_qty': line_data['qty'],
                'product_uom': bom_line.product_uom_id.id,
                'operation_id': operation_id,
                'bom_id': child_bom_id.id
            }]

            if child_bom_id:
                qty = bom_line.product_uom_id._compute_quantity(line_data['qty'], child_bom_id.product_uom_id)
                child_values = child_bom_id._boom(qty, level=level+1, id=next_id+1, parent_id=next_id, data=data)
                material_values += child_values
                next_id += len(child_values)

            next_id += 1

        return material_values
