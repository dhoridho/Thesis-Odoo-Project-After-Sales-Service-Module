from odoo import api, fields, models, _


class LandedCost(models.Model):
    _inherit = 'stock.landed.cost'

    base_sync = fields.Boolean("Base Sync", default=False)

    def generate_sequence(self):
        stock_landed_cost = self.env["stock.landed.cost"].search(
            [("base_sync", "=", True), ("id", "in", self.ids)]
        )
        for x in stock_landed_cost:
            if x.base_sync:
                seq = self.env['ir.sequence'].search([('code', '=', 'stock.landed.cost')])
                if len(seq) > 1:
                    seq = self.env['ir.sequence'].search([('code', '=', 'stock.landed.cost'), ('company_id','=', x.company_id.id)])
                x.name = seq.next_by_id()
                x.base_sync = False

        result = {
            "name": "Landed Cost Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "stock.landed.cost",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", stock_landed_cost.ids)],
            "target": "current",
        }
        return result

    @api.model
    def create(self,vals):
        res = super(LandedCost,self).create(vals)
        if vals.get('base_sync'):
            res['name'] = 'New'
            if vals.get('company_id'):
                seq = self.env['ir.sequence'].search([('code', '=', 'stock.landed.cost'),
                                                    ('company_id','=', vals['company_id'])])
            else:
                seq = self.env['ir.sequence'].search([('code', '=', 'stock.landed.cost')])
            if not seq.use_date_range:
                seq.number_next_actual = seq.number_next_actual - 1
            else:
                date_range = seq.date_range_ids.sorted('create_date', reverse=True)[0]
                date_range.number_next_actual = date_range.number_next_actual - 1
        return res
