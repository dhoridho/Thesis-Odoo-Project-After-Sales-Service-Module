from odoo import models, fields, api, _


class KsSalesForecast(models.Model):
    _name = 'ks.sales.forecast.result'
    _description = "Predicted Results"
    _rec_name = 'ks_forecast_id'

    ks_forecast_id = fields.Many2one('ks.sales.forecast', string=_('Sales Forecast'), ondelete="cascade")
    ks_date = fields.Date(string=_('Date'))
    ks_value = fields.Float(string=_('Sale'))
    ks_product_id = fields.Many2one('product.product', string=_('Product'))
    ks_partner_id = fields.Many2one('res.partner', string=_('Customer'))


class KsMessageWizard(models.TransientModel):
    _name = "ks.message.wizard"
    _description = "Message wizard to display warnings, alert ,success messages"

    name = fields.Text(string=_('Message'), readonly=True, default=lambda self: self.env.context.get("message", False))

    def ks_pop_up_message(self, names, message):
        """

        :param names: The title of wizard
        :param message: The content to be shown
        :return: open a wizard
        """
        view = self.env.ref('ks_sales_forecast.ks_message_wizard')
        context = dict(self._context or {})
        context['message'] = message
        return {
            'name': names,
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'ks.message.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'context': context
        }
