# -*- coding: utf-8 -*-
##############################################################################
#
# developed by Shilal Software Center 
# Email : shilalgroup@gmail.com
# Phones : +249902605920 
# whatsapp : +249902605920
#    
##############################################################################

from datetime import datetime, timedelta
from odoo import models, api, fields, _
from odoo.exceptions import UserError, AccessError, ValidationError

PAPER_SIZES = [
    {
        'description': 'A0  5   841 x 1189 mm',
        'key': 'A0',
        'height': 1189.0,
        'width': 841.0,
    }, {
        'key': 'A1',
        'description': 'A1  6   594 x 841 mm',
        'height': 841.0,
        'width': 594.0,
    }, {
        'key': 'A2',
        'description': 'A2  7   420 x 594 mm',
        'height': 594.0,
        'width': 420.0,
    }, {
        'key': 'A3',
        'description': 'A3  8   297 x 420 mm',
        'height': 420.0,
        'width': 297.0,
    }, {
        'key': 'A4',
        'description': 'A4  0   210 x 297 mm, 8.26 x 11.69 inches',
        'height': 297.0,
        'width': 210.0,
    }, {
        'key': 'A5',
        'description': 'A5  9   148 x 210 mm',
        'height': 210.0,
        'width': 148.0,
    }, {
        'key': 'A6',
        'description': 'A6  10  105 x 148 mm',
        'height': 148.0,
        'width': 105.0,
    }, {
        'key': 'A7',
        'description': 'A7  11  74 x 105 mm',
        'height': 105.0,
        'width': 74.0,
    }, {
        'key': 'A8',
        'description': 'A8  12  52 x 74 mm',
        'height': 74.0,
        'width': 52.0,
    }, {
        'key': 'A9',
        'description': 'A9  13  37 x 52 mm',
        'height': 52.0,
        'width': 37.0,
    }, {
        'key': 'B0',
        'description': 'B0  14  1000 x 1414 mm',
        'height': 1414.0,
        'width': 1000.0,
    }, {
        'key': 'B1',
        'description': 'B1  15  707 x 1000 mm',
        'height': 1000.0,
        'width': 707.0,
    }, {
        'key': 'B2',
        'description': 'B2  17  500 x 707 mm',
        'height': 707.0,
        'width': 500.0,
    }, {
        'key': 'B3',
        'description': 'B3  18  353 x 500 mm',
        'height': 500.0,
        'width': 353.0,
    }, {
        'key': 'B4',
        'description': 'B4  19  250 x 353 mm',
        'height': 353.0,
        'width': 250.0,
    }, {
        'key': 'B5',
        'description': 'B5  1   176 x 250 mm, 6.93 x 9.84 inches',
        'height': 250.0,
        'width': 176.0,
    }, {
        'key': 'B6',
        'description': 'B6  20  125 x 176 mm',
        'height': 176.0,
        'width': 125.0,
    }, {
        'key': 'B7',
        'description': 'B7  21  88 x 125 mm',
        'height': 125.0,
        'width': 88.0,
    }, {
        'key': 'B8',
        'description': 'B8  22  62 x 88 mm',
        'height': 88.0,
        'width': 62.0,
    }, {
        'key': 'B9',
        'description': 'B9  23  33 x 62 mm',
        'height': 62.0,
        'width': 33.0,
    }, {
        'key': 'B10',
        'description': 'B10    16  31 x 44 mm',
        'height': 44.0,
        'width': 31.0,
    }, {
        'key': 'C5E',
        'description': 'C5E 24  163 x 229 mm',
        'height': 229.0,
        'width': 163.0,
    }, {
        'key': 'Comm10E',
        'description': 'Comm10E 25  105 x 241 mm, U.S. Common 10 Envelope',
        'height': 241.0,
        'width': 105.0,
    }, {
        'key': 'DLE',
        'description': 'DLE 26 110 x 220 mm',
        'height': 220.0,
        'width': 110.0,
    }, {
        'key': 'Executive',
        'description': 'Executive 4   7.5 x 10 inches, 190.5 x 254 mm',
        'height': 254.0,
        'width': 190.5,
    }, {
        'key': 'Folio',
        'description': 'Folio 27  210 x 330 mm',
        'height': 330.0,
        'width': 210.0,
    }, {
        'key': 'Ledger',
        'description': 'Ledger  28  431.8 x 279.4 mm',
        'height': 279.4,
        'width': 431.8,
    }, {
        'key': 'Legal',
        'description': 'Legal    3   8.5 x 14 inches, 215.9 x 355.6 mm',
        'height': 355.6,
        'width': 215.9,
    }, {
        'key': 'Letter',
        'description': 'Letter 2 8.5 x 11 inches, 215.9 x 279.4 mm',
        'height': 279.4,
        'width': 215.9,
    }, {
        'key': 'Tabloid',
        'description': 'Tabloid 29 279.4 x 431.8 mm',
        'height': 431.8,
        'width': 279.4,
    }, {
        'key': 'custom',
        'description': 'Custom',
    },
]


class SscReportTemplate(models.Model):
    _name = 'ssc.create.template'
    _description = "Model Contain all importanat data design demplates"

    name = fields.Char(string="Name", translate=True, required=True)
    body = fields.Html(string="Body", translate=True, required=True)
    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete="cascade", help="The type of document this template can be used with", 
        domain="[('model','in',['account.move','hr.contract','hr.employee','res.partner','product.pricelist','purchase.order','sale.order','stock.picking','stock.inventory','account.payment'])]")
    field_ids = fields.Many2many('ir.model.fields', string="Fields", compute='get_field_ids')
    lang = fields.Char('Language', help="Use this field to either force a specific language (ISO code) (e.g. ${object.partner_id.lang})")
    apply_to_models = fields.Boolean(string="Apply To Models")
    applied_models = fields.Boolean(string="Applied To Models")
    apply_models = fields.Many2many('ir.model', string="Models", domain="[('model','in',['account.move','hr.contract','hr.employee','res.partner','product.pricelist','purchase.order','sale.order','stock.picking','stock.inventory','account.payment'])]")
    sample_template = fields.Boolean(string="Use as Sample Template")
    sample_image = fields.Binary(string='Sample Image')
    apply_to_menu = fields.Boolean(string="Show In Menu")
    sample_template_id = fields.Many2one('ssc.create.template', string="Sample Template", domain="[('sample_template','=',True)]")
    checked_sample_image = fields.Binary(string='Sample Images')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('applied', 'Applied')
        ], 'State', default='draft')
    format = fields.Selection([(ps['key'], ps['description']) for ps in PAPER_SIZES], 'Paper size', default='A4', help="Select Proper Paper size")
    margin_top = fields.Float('Top Margin (mm)', default=40)
    margin_bottom = fields.Float('Bottom Margin (mm)', default=20)
    margin_left = fields.Float('Left Margin (mm)', default=7)
    margin_right = fields.Float('Right Margin (mm)', default=7)
    orientation = fields.Selection([
        ('Landscape', 'Landscape'),
        ('Portrait', 'Portrait')
        ], 'Orientation', default='Portrait')
    

    @api.onchange('sample_template_id')
    def get_sample_template_body(self):
        """
        Function to get the template body and put it in the current body
        """
        if self.sample_template_id:
            self.body = self.sample_template_id.body

    def action_to_apply(self):
        """
        Function to set teh current 
        """
        template_id = self.env['mail.template']
        template_id_fount = template_id.search([('name','=',self.name)])

        for rec in template_id_fount:
            rec.unlink()

        template_id.create({
                'name':self.name,
                'model_id':self.model_id.id,
                'body_html':self.body,
                'lang':'${object.lang}',
            })

        self.activate_report_in_menu()
        self.action_models_apply()
        self.edit_report_paper_format()
        self.state = 'applied'

    def edit_report_paper_format(self):
        """
        funtion to customize the paper format for the report
        """
        paper_formate_ids = self.env['report.paperformat'].search([])

        if self.orientation == 'Landscape':
            for rec in paper_formate_ids:
                if rec.name == 'Portrait Custom A4':
                    rec.write({
                        'format':self.format,
                        'margin_top':self.margin_top,
                        'margin_bottom':self.margin_bottom,
                        'margin_left':self.margin_left,
                        'margin_right':self.margin_right
                        })
        if self.orientation == 'Portrait':
            for rec in paper_formate_ids:
                if rec.name == 'Portrait Custom A4':
                    rec.write({
                        'format':self.format,
                        'margin_top':self.margin_top,
                        'margin_bottom':self.margin_bottom,
                        'margin_left':self.margin_left,
                        'margin_right':self.margin_right
                        })

    def action_models_apply(self):
        """
        Function to apply the current template for many models
        """
        if self.applied_models == False:
            if self.apply_to_models == True:
                self.applied_models = True
                for model in self.apply_models:
                    self.create({
                        'name':self.name+' / '+model.model,
                        'model_id':model.id,
                        'body':self.body
                        })

    def action_in_menu(self):
        """ 
        function to show report in any view for the model
        """
        ir_report_obj = self.env['ir.actions.report']
        ir_report_found = self.env['ir.actions.report'].search([(('name','=',self.name))])

        if self.apply_to_menu == True:
            for rec in ir_report_found:
                rec.unlink()
            ir_report_obj.create({
                'name':self.name,
                'model':self.model_id.model,
                'report_name':'pdf_report_creator.portrait_report_creator_report_temp',
                })

    def activate_report_in_menu(self):
        ir_report_found = self.env['ir.actions.report'].search([(('name','=',self.name))])
        view_obj = self.env['ir.ui.view']
        view_found = self.env['ir.ui.view'].search([(('name','=',self.name))])

        for rec in view_found:
            rec.unlink()

        ir_report_found.create_action()
            



    @api.onchange('model_id')
    def get_field_ids(self):
        """
        Function to compute fields that can be able to use in the report template 
        """
        field_ids = self.env['ir.model.fields']
        field_obj = False
        if self.model_id:
            field_obj = field_ids.search([('model','=',self.model_id.model)])
        self.field_ids = field_obj


    @api.onchange('name','model_id','body','orientation')
    def changes_must_applied(self):
        """
        Function to make user must apply the change to make this template usable
        """
        self.state = 'draft'

