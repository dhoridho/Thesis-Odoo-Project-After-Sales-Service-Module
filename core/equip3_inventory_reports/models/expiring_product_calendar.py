import json
import calendar
import datetime

from odoo.osv import expression
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse


class ExpiringProductCalendarReport(models.AbstractModel):
    _name = 'report.equip3_inventory_reports.expiring_product_calendar'
    _description = 'Expiring Product Calendar Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        return {
            'doc_ids': docids,
            'docs': self.env['expiring.product.calendar'].browse(docids),
            'doc_model': 'expiring.product.calendar',
            'today': fields.Date.today().strftime('YYYY-MM-DD'), 
            'loads': json.loads
        }


class ExpiringProductCalendar(models.TransientModel):
    _name = 'expiring.product.calendar'
    _description = 'Expiring Product Calendar'

    data = fields.Text()

    @api.model
    def get_quants(self):
        tz = self.env.user.tz or 'UTC'
        self.env.cr.execute('''SELECT 
            sq.id AS quant_id, 
            CASE
                WHEN sl.usage = 'internal' OR (sl.usage = 'transit' AND sl.company_id IS NOT NULL) THEN True
                ELSE False 
            END is_internal,
            sq.product_id AS product_id, 
            pp.product_display_name AS product_name, 
            pc.id AS categ_id, 
            pc.complete_name AS categ_name, 
            sq.location_id AS location_id, 
            sl.complete_name AS location_name, 
            sl.usage AS location_usage,
            sl.company_id as location_company_id,
            sq.lot_id AS lot_id, 
            spl.name AS lot_name, 
            sq.quantity AS quantity, 
            spl.alert_date AT TIME ZONE 'UTC' AT TIME ZONE '%s' AS alert_date, 
            spl.expiration_date AT TIME ZONE 'UTC' AT TIME ZONE '%s' AS expiration_date, 
            spl.removal_date AT TIME ZONE 'UTC' AT TIME ZONE '%s' AS removal_date 
        FROM 
            stock_quant sq 
        LEFT JOIN product_product pp ON (pp.id = sq.product_id) 
        LEFT JOIN product_category pc ON (pc.id = pp.categ_id) 
        LEFT JOIN stock_location sl ON (sl.id = sq.location_id) 
        LEFT JOIN stock_production_lot spl ON (spl.id = sq.lot_id) 
        WHERE 
            sq.lot_id IS NOT null''' % (tz, tz, tz)
        )
        quants = self.env.cr.dictfetchall()

        self.env.cr.execute('''SELECT
            categ.id AS id,
            categ.complete_name AS name,
            quant.expired AS expired
        FROM
            product_category categ
        LEFT JOIN
            (SELECT 
                pc.id AS categ_id,
                SUM(sq.quantity) AS expired 
            FROM 
                stock_quant sq 
            LEFT JOIN product_product pp ON (pp.id = sq.product_id) 
            LEFT JOIN product_category pc ON (pc.id = pp.categ_id) 
            LEFT JOIN stock_location sl ON (sl.id = sq.location_id) 
            LEFT JOIN stock_production_lot spl ON (spl.id = sq.lot_id) 
            WHERE 
                (sl.usage = 'internal' OR (sl.usage = 'transit' AND sl.company_id IS NOT NULL)) AND spl.expiration_date < CURRENT_DATE 
            GROUP BY 
                pc.id) quant
            ON (categ.id = quant.categ_id)
        ORDER BY
            categ.id''')
        categories = self.env.cr.dictfetchall()

        self.env.cr.execute('''SELECT 
            location.id,
            location.complete_name AS name,
            quant.expired AS expired 
        FROM 
            stock_location location
        LEFT JOIN
            (SELECT
                sl.id AS location_id,
                SUM(sq.quantity) AS expired
            FROM
                stock_quant sq
            LEFT JOIN stock_location sl ON (sl.id = sq.location_id)
            LEFT JOIN stock_production_lot spl ON (spl.id = sq.lot_id) 
            WHERE
                (sl.usage = 'internal' OR (sl.usage = 'transit' AND sl.company_id IS NOT NULL)) AND spl.expiration_date < CURRENT_DATE 
            GROUP BY
                sl.id) quant
            ON (location.id = quant.location_id)
        ORDER BY
            location.id''')
        locations = self.env.cr.dictfetchall()

        return {
            'categories': categories,
            'locations': locations,
            'quants': quants
        }
