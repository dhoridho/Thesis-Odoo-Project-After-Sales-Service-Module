from odoo import api, fields, models, _


class PosSession(models.Model):
    _inherit = "pos.session"

    def ph_vat_breakdown(self):
        ph_vat_breakdown = {'VATable':0,'VAT zero rate':0,'VAT exempt':0,'total':0}
        for order in self.order_ids:
            for line in order.lines:
                if line.product_id.ph_vat_type == 'VATable':
                    ph_vat_breakdown['VATable'] += line.untax_amount
                if line.product_id.ph_vat_type == 'VAT zero rate':
                    ph_vat_breakdown['VAT zero rate'] += line.untax_amount
                if line.product_id.ph_vat_type == 'VAT exempt':
                    ph_vat_breakdown['VAT exempt'] += line.untax_amount
                ph_vat_breakdown['total'] += line.untax_amount
        return ph_vat_breakdown