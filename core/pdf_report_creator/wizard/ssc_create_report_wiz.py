# -*- coding: utf-8 -*-
##############################################################################
#
# developed by Shilal Software Center 
# Email : shilalgroup@gmail.com
# Phones : +249902605920 
# whatsapp : +249902605920
#    
##############################################################################

from odoo import api, fields, models, _

class SsccreatoreportWiz(models.TransientModel):
    _inherit = 'mail.compose.message'
    _description = 'SSC Create Report Wiz'

    check_value = fields.Boolean(string="Check")
    orientation = fields.Selection([
        ('Landscape', 'Landscape'),
        ('Portrait', 'Portrait')
        ], 'Orientation', default='Landscape')

    def print_pdf_created_report(self):
        """
        Function Get The Data to print pdf analytical report
        """
        data = {}

        if self.orientation == 'Landscape':
        	return self.env.ref('pdf_report_creator.landscape_report_creator_report_action').report_action(self)
        if self.orientation == 'Portrait':
        	return self.env.ref('pdf_report_creator.portrait_report_creator_report_action').report_action(self)