
##############################################################################

from odoo import models, api, fields, _
from random import randint
import re
from odoo.exceptions import ValidationError

class SscReportTemplate(models.Model):
    _inherit = 'ssc.create.template'


    model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete="cascade", help="The type of document this template can be used with", 
        domain="[]")


    def action_to_apply(self):
        self.write({'apply_to_menu':True})
        return super(SscReportTemplate, self).action_to_apply()

    def set_to_draft(self):
        self.write({'state':'draft'})
        self.unlink_report_in_view()
        return True


    def unlink_report_in_view(self):
        ir_report_obj = self.env['ir.actions.report']
        view_obj = self.env['ir.ui.view']
        model_data_obj = self.env['ir.model.data']
        paperformat_obj = self.env['report.paperformat']
        for data in self:
            if data.apply_to_menu == True:
                ir_report_found = ir_report_obj.search([(('ssc_create_template_id','=',data.id))])
                view_found = view_obj.search([(('ssc_create_template_id','=',data.id))])

                if view_found:
                    for view in view_found:
                        if view.model_data_id:
                            view.model_data_id.unlink()
                    view_found.with_context(force_delete=1).unlink()
                if ir_report_found:
                    for report in ir_report_found:
                        if report.paperformat_id:
                            report.paperformat_id.unlink()
                    ir_report_found.unlink()

        return True

    @api.onchange('name','model_id','body','orientation')
    def changes_must_applied(self):
        """
        Function to make user must apply the change to make this template usable
        """
        self.set_to_draft()
    

    def get_body_html(self,xml_id,record):
        ir_report_obj = self.env['ir.actions.report']
        report = ir_report_obj.search([('report_name','=',xml_id)],limit=1)
        if not report:
            raise ValidationError("Report not found, please start apply template report again in menu Reports Creator")
        ssc_create_template = report.ssc_create_template_id
        body = ssc_create_template.body
        ctx = {}
        body =  self.env['mail.render.mixin'].with_context(ctx)._render_template(body, report.model, record.ids)[record.id]

        return body


    def settle_template_to_views(self,xml_id):
        arch = '''<?xml version="1.0"?>
                    <t t-name="'''+xml_id+'''">
                            <t t-call="web.html_container">
                                <t t-foreach="docs" t-as="o">
                                    <t t-call="web.basic_layout">
                                        <div class="page"> 
                                            '''

        arch+= '''<span t-raw="request.env['ssc.create.template'].get_body_html('''+"'"+xml_id+"'"+''',o)"/>'''
        arch += '''

                                            
                                        </div>
                                    </t>
                                </t>
                            </t>
                        </t>
                '''
        return arch


    

    def activate_report_in_menu(self):
        ir_report_obj = self.env['ir.actions.report']
        view_obj = self.env['ir.ui.view']
        model_data_obj = self.env['ir.model.data']
        paperformat_obj = self.env['report.paperformat']
        for data in self:
            if data.apply_to_menu == True:
                data.unlink_report_in_view()
                uniq_number = randint(100, 999) 
                name = data.name.replace(' ','_').replace('/','_').lower() +'_'+str(uniq_number)
                module = 'equip3_pdf_report_creator_extend'
                xml_id = module+'.'+name

                if data.format and data.orientation:
                    paperformat = paperformat_obj.create({
                        'name':data.name +' '+'Paperformat',
                        'format':data.format,
                        'orientation':data.orientation,
                        'margin_top':data.margin_top,
                        'margin_left':data.margin_left,
                        'margin_right':data.margin_right,
                        'margin_bottom':data.margin_bottom,
                    })
                    paperformat_id = paperformat.id
                else:
                    paperformat_id = False
                name_model = data.model_id.model
        
                view_report = view_obj.create({
                    'ssc_create_template_id':data.id,
                    'name':name,
                    'type':'qweb',
                    'arch':self.settle_template_to_views(xml_id)
                })

                model_data = model_data_obj.create({
                    'module':module,
                    'name':name,
                    'model':'ir.ui.view',
                    'res_id':view_report.id,
                })

                ir_report = ir_report_obj.create({
                    'name':data.name,
                    'paperformat_id':paperformat_id,
                    'model':data.model_id.model,
                    'ssc_create_template_id':data.id,
                    'report_name':view_report.xml_id,
                    })
                ir_report.create_action()
                


