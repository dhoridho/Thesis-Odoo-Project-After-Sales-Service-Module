from odoo import fields, models, api, _


class AccountAccount(models.Model):
    _inherit = 'account.account'
    _description = 'Chart Of Account'

    cash_forecast_tag = fields.Many2one("cash.forecast.tag", string="Cash Forecast Tag")

    def create_forecast_type(self):
        forecasting_type = self.env['setu.cash.forecast.type']

        account = self._context.get('active_ids')
        account_ids = self.browse(account)
        forecasting_tags = account_ids.mapped('cash_forecast_tag')
        account_without_tag = account_ids.filtered(lambda a: not a.cash_forecast_tag)

        for tag in forecasting_tags:
            vals = {'name': tag.name,
                    'account_ids': [(6, 0, tag.account_ids.ids)],
                    'company_id': tag.company_id.id,
                    'forecasting_tag': tag.id}

            forecasting_type = forecasting_type.search([('forecasting_tag', '=', tag.id),
                                                        ('company_id', '=', tag.company_id.id)])
            if forecasting_type:
                forecasting_type.update(vals)
            else:
                forecasting_type.create(vals)
                
        for account in account_without_tag:
            vals = {'name': account.name,
                    'account_ids': [(6, 0, account.ids)],
                    'company_id': account.company_id.id,
                    }

            forecasting_type = forecasting_type.search([('name', '=', account.name),
                                                        ('company_id', '=', account.company_id.id)])
            if forecasting_type:
                forecasting_type.update(vals)
            else:
                forecasting_type.create(vals)

        return {
            'name': _('Cash Forecast Type'),
            'view_mode': 'tree,form',
            'res_model': 'setu.cash.forecast.type',
            # 'view_id': self.env.ref('setu_cash_flow_forecasting.tree_setu_cash_forecast_type').id,
            'type': 'ir.actions.act_window',
        }
