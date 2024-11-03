from odoo import api, fields, models


class Company(models.Model):
    _inherit = 'res.company'

    res_forecast_seq = fields.Boolean("Forecast Sequence", compute="_compute_seq", store=True)

    @api.model
    def create(self, vals):
        vals['res_forecast_seq'] = True
        res = super(Company, self).create(vals)
        res.create_seq_forecast()
        return res

    def create_seq_forecast(self):
        for res in self:
            seq2 = self.env['ir.sequence'].search([('code', '=', "ks.sales.forecast." + res.name)])
            if not seq2:
                self.env['ir.sequence'].create({
                    'name': "Sales Forecast" + " " + res.name,
                    'code': "ks.sales.forecast." + res.name,
                    'prefix': "SF",
                    'padding': 5,
                    'company_id': res.id,
                })

    def _compute_seq(self):
        i = 1
        for res in self:
            if not res.res_forecast_seq:
                if i == 1:
                    seq1 = self.env['ir.sequence'].search([('code', '=', "ks.sales.forecast")])
                    if seq1:
                        seq1.write({
                            'company_id': res.id
                        })
                else:
                    res.create_seq_forecast()
                res.res_forecast_seq = True
            i += 1