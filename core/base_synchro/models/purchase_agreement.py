from odoo import api, fields, models, _


class PurchaseAgreement(models.Model):
    _inherit = "purchase.agreement"

    base_sync = fields.Boolean("Base Sync", default=False)

    @api.model
    def create(self, vals):
        if 'base_sync' in vals:
            if vals['base_sync']:
                if 'name' in vals:
                    vals['name'] = '/'
        res = super().create(vals)
        return res

    def write(self, vals):
        if 'name' in self.env.context:
            vals['name'] = self.env.context['name']
        res = super().write(vals)
        return res

    def generate_sequence(self):
        purchase_agreements = self.env["purchase.agreement"].search([
            ("base_sync", "=", True),
            ("id", "in", self.ids)
        ])
        for pa in purchase_agreements:
            if pa.base_sync:
                if pa.is_rental_orders:
                    if pa.tender_scope == 'open_tender':
                        name = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.r.open')
                    else:
                        name = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.r')
                elif pa.is_goods_orders:
                    if pa.tender_scope == 'open_tender':
                        name = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.g.open')
                    else:
                        name = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.g')
                elif pa.is_services_orders:
                    if pa.tender_scope == 'open_tender':
                        name = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.s.open')
                    else:
                        name = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.s')
                elif pa.is_assets_orders:
                    if pa.tender_scope == 'open_tender':
                        name = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.a.open')
                    else:
                        name = self.env['ir.sequence'].next_by_code('purchase.agreement.seqs.a')
                else:
                    name = self.env["ir.sequence"].next_by_code("purchase.agreement.seqs")
                # menggunakan context karna vals name ketika write selalu "/"
                pa.with_context(name=name).write({
                    'name': name
                })
                pa.base_sync = False

        result = {
            "name": "Purchase Agreement Resequence",
            "view_type": "form",
            "view_mode": "tree,form",
            "res_model": "purchase.agreement",
            "type": "ir.actions.act_window",
            "domain": [("id", "in", purchase_agreements.ids)],
            "target": "current",
        }
        return result
