from datetime import date, datetime

from odoo import api, fields, models, _


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    @staticmethod
    def _get_empty_widget_lines(domain):
        empty_widget_lines = [
            {'name': _('Purchase Request'), 'states': ('draft', 'sent'), 'count': 0, 'amount': 0.0},
            {'name': _('Under Approval'), 'states': ('to approve',), 'count': 0, 'amount': 0.0},
            {'name': _('Purchase Order'), 'states': ('purchase', 'done'), 'count': 0, 'amount': 0.0},
            {'name': _('Cancelled PO'), 'states': ('cancel',), 'count': 0, 'amount': 0.0}
        ]
        for empty_widget_line in empty_widget_lines:
            empty_widget_line['domain'] = str(domain + [('state', 'in', empty_widget_line['states'])])
        return empty_widget_lines

    def _append_dashboard_widgets(self, dashboard_widgets, line, res_model, group_by_field, year):
        res_id = line[group_by_field]
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))
        default_domain = [
            (group_by_field, '=', res_id),
            ('date_calendar_start', '>=', year_start),
            ('date_calendar_start', '<=', year_end),
        ]
        if res_id not in dashboard_widgets:
            dashboard_widgets[res_id] = {
                'image': '/web/image/{}/{}/image_128'.format(res_model, res_id),
                'name': line['name'],
                'currency_symbol': self.env.company.currency_id.symbol,
                'lines': self._get_empty_widget_lines(domain=default_domain),
            }
        self._prepare_widget_lines(dashboard_widgets, line, res_id)

    def _prepare_widget_lines(self, dashboard_widgets, line, res_id):
        for widget_line in dashboard_widgets[res_id]['lines']:
            if line['state'] in widget_line['states']:
                widget_line['count'] += line['count']
                widget_line['amount'] += round(line['amount'], line['decimal_places'])

    def _retrieve_dashboard_data_by_users(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))

        query = """
        SELECT
        po.user_id,
        partner.name,
        po.state,
        COUNT(1) as count,
        SUM(COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total)) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_order po
        JOIN res_users users ON (po.user_id = users.id)
        JOIN res_partner partner ON (users.partner_id = partner.id)
        JOIN res_company comp ON (po.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE po.company_id = %s AND po.date_calendar_start >= %s AND po.date_calendar_start <= %s
        GROUP BY po.user_id, partner.name, po.state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    def _retrieve_dashboard_data_by_partners(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))
        query = """
        SELECT
        po.partner_id,
        partner.name,
        po.state,
        COUNT(1) as count,
        SUM(COALESCE(po.amount_total / NULLIF(po.currency_rate, 0), po.amount_total)) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_order po
        JOIN res_partner partner ON (po.partner_id = partner.id)
        JOIN res_company comp ON (po.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE po.company_id = %s AND po.date_calendar_start >= %s AND po.date_calendar_start <= %s
        GROUP BY po.partner_id, partner.name, po.state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    def _retrieve_dashboard_data_by_products(self, year):
        year_start = fields.Date.to_string(date(year, 1, 1))
        year_end = fields.Date.to_string(date(year, 12, 31))
        query = """
        SELECT
        pol.product_id,
        product_template.name,
        pol.state,
        COUNT(1) as count,
        SUM(COALESCE(pol.price_total / NULLIF(po.currency_rate, 0), pol.price_total)) as amount,
        MIN(curr.decimal_places) as decimal_places
        FROM purchase_order_line pol
        JOIN purchase_order po ON (pol.order_id = po.id)
        JOIN product_product product ON (pol.product_id = product.id)
        JOIN product_template product_template ON (product.product_tmpl_id = product_template.id)
        JOIN res_company comp ON (po.company_id = comp.id)
        JOIN res_currency curr ON (comp.currency_id = curr.id)
        WHERE po.company_id = %s AND po.date_calendar_start >= %s AND po.date_calendar_start <= %s
        GROUP BY pol.product_id, product_template.name, pol.state;
        """
        self._cr.execute(query, (self.env.company.id, year_start, year_end))
        return self.env.cr.dictfetchall()

    @api.model
    def get_dashboard_widgets(self, year, group_by='user_id'):

        if group_by == 'partner_id':
            res_model = 'res.partner'
            res = self._retrieve_dashboard_data_by_partners(year)
        elif group_by == 'product_id':
            res_model = 'product.product'
            res = self._retrieve_dashboard_data_by_products(year)
        else:
            group_by = 'user_id'
            res_model = 'res.users'
            res = self._retrieve_dashboard_data_by_users(year)

        dashboard_widgets = {}
        for line in res:
            self._append_dashboard_widgets(dashboard_widgets, line, res_model, group_by, year)

        return dashboard_widgets

    @api.model
    def get_dashboard_years(self):
        po_from = self.search([('date_calendar_start', '!=', False)], order='date_calendar_start ASC', limit=1)
        po_to = self.search([('date_calendar_start', '!=', False)], order='date_calendar_start DESC', limit=1)
        if po_from and po_to:
            year_from = fields.Date.from_string(po_from.date_calendar_start).year
            year_to = fields.Date.from_string(po_to.date_calendar_start).year
            return list(range(year_from, year_to + 1))
        return [datetime.now().year]
