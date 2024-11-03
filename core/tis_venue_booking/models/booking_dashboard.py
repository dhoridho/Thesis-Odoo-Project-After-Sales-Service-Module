# -*- coding: utf-8 -*-
# This module and its content is copyright of Technaureus Info Solutions Pvt. Ltd.
# - © Technaureus Info Solutions Pvt. Ltd 2020. All rights reserved.

from odoo import models, api, _
import datetime


class BookingDashboard(models.Model):
    _name = "booking.dashboard"
    _description = 'Booking Dashboard'

    @api.model
    def get_booking_info(self):
        currency = self.env.user.company_id.currency_id.symbol
        cr = self.env.cr
        month = datetime.datetime.now().strftime("%m")
        month_name = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
                      "November", "December"]
        current_month_name = month_name[int(month) - 1]
        year = datetime.datetime.now().strftime("%Y")


        query = """
                    SELECT count(b.name) as bo
                    FROM booking_booking b
                    WHERE DATE_TRUNC('month',b.from_date) = DATE_TRUNC('month', CURRENT_DATE)
                    AND b.company_id = %s """ % self.env.user.company_id.id
        cr.execute(query)
        this_month_booking = cr.dictfetchall()
        this_month_booking_dataset = []
        for data in this_month_booking:
            this_month_booking_dataset.append(data['bo'])


        query = """
                    SELECT count(b.name) as bo
                    FROM booking_booking b
                    WHERE DATE_TRUNC('month',b.from_date) = DATE_TRUNC('month', CURRENT_DATE) AND b.state = 'confirm'
                    AND b.company_id = %s """ % self.env.user.company_id.id
        cr.execute(query)
        this_month_confirmed_booking = cr.dictfetchall()
        this_month_confirmed_booking_dataset = []
        for data in this_month_confirmed_booking:
            this_month_confirmed_booking_dataset.append(data['bo'])


        query = """
                    SELECT count(b.name) as bo
                    FROM booking_booking b
                    WHERE DATE_TRUNC('month',b.from_date) = DATE_TRUNC('month', CURRENT_DATE) 
                    AND b.state = 'cancel' 
                    AND b.company_id = %s """ % self.env.user.company_id.id
        cr.execute(query)
        this_month_cancelled_booking = cr.dictfetchall()
        this_month_cancelled_booking_dataset = []
        for data in this_month_cancelled_booking:
            this_month_cancelled_booking_dataset.append(data['bo'])


        query = """
                    SELECT sum(b.amount_total)::numeric as total_revenue
                    FROM booking_booking b
                    WHERE DATE_TRUNC('month',b.from_date) = DATE_TRUNC('month', CURRENT_DATE) 
                    AND b.state = 'confirm'
                    AND b.company_id = %s """ % self.env.user.company_id.id
        cr.execute(query)
        this_month_revenue = cr.dictfetchall()
        this_month_revenue_dataset = []
        for data in this_month_revenue:
            if data['total_revenue']:
                this_month_revenue_dataset.append(format(data['total_revenue'], ',.2f'))
            else:
                this_month_revenue_dataset.append(format(0, ',.2f'))


        query = """ SELECT partner_name as name,sum(amount_total) as sum
                    FROM booking_booking as b 
                    WHERE DATE_TRUNC('year',b.from_date) = DATE_TRUNC('year', CURRENT_DATE)
                    AND b.company_id = %s
                    GROUP BY partner_name 
                    ORDER BY sum(amount_total) DESC LIMIT 5 """ % self.env.user.company_id.id

        cr.execute(query)
        top_customers_piechart_data = cr.dictfetchall()
        top_customers_piechart_label = []
        top_customers_piechart_dataset = []
        for data in top_customers_piechart_data:
            top_customers_piechart_label.append(data['name'])
            top_customers_piechart_dataset.append(data['sum'])


        query = """ SELECT v.name as name,count(b.name) as count 
                    FROM booking_booking as b
                    LEFT JOIN venue_venue v on (v.id = b.venue_id )
                    WHERE b.state = 'confirm'
                    AND b.company_id = %s
                    GROUP BY v.name ORDER BY count(b.name) DESC LIMIT 5 
                    """ % self.env.user.company_id.id
        cr.execute(query)
        top_venues_piechart_data = cr.dictfetchall()
        top_venues_piechart_label = []
        top_venues_piechart_dataset = []
        for data in top_venues_piechart_data:
            top_venues_piechart_label.append(data['name'])
            top_venues_piechart_dataset.append(data['count'])


        query = """ SELECT v.name as name,count(b.name) as count 
                    FROM booking_booking as b
                    LEFT JOIN venue_venue v on (v.id = b.venue_id )
                    WHERE b.state = 'confirm' AND DATE_TRUNC('month',b.from_date) = DATE_TRUNC('month', CURRENT_DATE)
                    AND b.company_id = %s  
                    GROUP BY v.name ORDER BY count(b.name) DESC LIMIT 5 
                    """ % self.env.user.company_id.id
        cr.execute(query)
        top_venues_month_piechart_data = cr.dictfetchall()
        top_venues_month_piechart_label = []
        top_venues_month_piechart_dataset = []
        for data in top_venues_month_piechart_data:
            top_venues_month_piechart_label.append(data['name'])
            top_venues_month_piechart_dataset.append(data['count'])

        query = """ SELECT to_char(to_timestamp (date_part('month', b.from_date)::text, 'MM'), 'Month') as month,
                    EXTRACT(MONTH FROM b.from_date) as Mon,sum(b.amount_total) as amount FROM booking_booking b
                    WHERE DATE_TRUNC('year',b.from_date) = DATE_TRUNC('year', CURRENT_DATE) 
                    AND b.state='confirm'
                    AND b.company_id = %s
                    GROUP BY Mon 
                    ORDER BY Mon 
                    """ % self.env.user.company_id.id
        cr.execute(query)
        month_booking_barchart_data = cr.dictfetchall()
        month_booking_label = []
        month_booking_dataset = []
        for data in month_booking_barchart_data:
            month_booking_label.append(data['month'])
            if data['amount']:
                month_booking_dataset.append(data['amount'])
            else:
                month_booking_dataset.append(0)


        query = """ SELECT sum(b.amount_total) as amount , EXTRACT( day FROM b.from_date ) as date
                        FROM booking_booking b
                        WHERE  date_trunc('month', b.from_date) = date_trunc('month', CURRENT_DATE) 
                        AND b.state='confirm'
                        AND b.company_id = %s
                        GROUP BY  date
                        ORDER BY  date
                            """ % self.env.user.company_id.id
        cr.execute(query)
        date_booking_linechart_data = cr.dictfetchall()
        date_booking_label = []
        date_booking_dataset = []
        for data in date_booking_linechart_data:
            date_booking_label.append(data['date'])
            if data['amount']:
                date_booking_dataset.append(data['amount'])
            else:
                date_booking_dataset.append(0)
        return currency, current_month_name, year, this_month_booking_dataset, this_month_confirmed_booking_dataset, \
               this_month_cancelled_booking_dataset, this_month_revenue_dataset, \
               top_customers_piechart_label, top_customers_piechart_dataset, top_venues_piechart_label, \
               top_venues_piechart_dataset, top_venues_month_piechart_label, top_venues_month_piechart_dataset, \
               month_booking_label, month_booking_dataset, date_booking_label, date_booking_dataset
