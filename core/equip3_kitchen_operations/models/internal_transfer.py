from odoo import models, fields, api, _


class InternalTransfer(models.Model):
    _inherit = 'internal.transfer'

    @api.model
    def create(self, vals):
        if vals.get('is_outlet_order') is True:
            vals['name'] = self.env['ir.sequence'].next_by_code('internal.transfer.outlet')
        return super(InternalTransfer, self).create(vals)

    is_outlet_order = fields.Boolean(string="Is Outlet Order", default=False)

    def action_confirm(self):
        outlet_transfer = self.filtered(lambda o: o.is_outlet_order)

        for outlet in outlet_transfer:
            company = outlet.company_id
            branch = outlet.branch_id
            source_location = outlet.source_location_id
            destination_location = outlet.destination_location_id
            scheduled_date = outlet.scheduled_date
            analytic_account_group_ids = outlet.analytic_account_group_ids
            next_sequence = len(outlet.product_line_ids) + 1

            product_line_values = []
            for line in outlet.product_line_ids:
                bom = self.env['mrp.bom'].with_context(
                    equip_bom_type='kitchen',
                    branch_id=branch.id
                )._bom_find(product=line.product_id, company_id=company.id, bom_type='normal')

                for bom_line in bom.bom_line_ids:
                    if bom_line.product_id.produceable_in_kitchen:
                        child_product_qty = line.qty * bom_line.product_qty
                        vals = {
                            'sequence': next_sequence,
                            'source_location_id': source_location.id,
                            'destination_location_id': destination_location.id,
                            'product_id': bom_line.product_id.id,
                            'description': bom_line.product_id.display_name,
                            'qty': child_product_qty,
                            'uom': bom_line.product_id.uom_id.id,
                            'scheduled_date': scheduled_date,
                            'analytic_account_group_ids': [(6, 0, analytic_account_group_ids.ids)]
                        }
                        product_line_values += [(0, 0, vals)]
                        next_sequence += 1
            
            if product_line_values:
                outlet.product_line_ids = product_line_values

        res = super(InternalTransfer, self).action_confirm()

        kitchen_id = self.env.context.get('kitchen_pop_back')
        if kitchen_id and isinstance(kitchen_id, int):
            kitchen_object = self.env['kitchen.production.record'].with_context(itr_pop_back=self.id)
            return kitchen_object.browse(kitchen_id).action_view_transfer_request()

        return res
