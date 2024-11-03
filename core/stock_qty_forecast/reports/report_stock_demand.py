# -*- coding: utf-8 -*-


from odoo import fields, models

class report_stock_demand(models.TransientModel):
    """
    The model to reflect real and forecast stock demand time series
    """
    _name = 'report.stock.demand'
    _description = 'Stock Demand'

    date_datetime = fields.Date(string="Demand Period")
    quantity = fields.Float(string="Demand", readonly=True)
    forecast = fields.Boolean(string="Forecast", readonly=True)
