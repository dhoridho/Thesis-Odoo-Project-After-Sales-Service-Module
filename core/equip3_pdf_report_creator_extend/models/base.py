
from odoo.exceptions import ValidationError
from odoo import models, api, fields, _
from lxml import etree

class Base(models.AbstractModel):
    """ The base model, which is implicitly inherited by all models. """
    _inherit = 'base'

    def ssc_custom_print(self):
        report_obj = self.env['ir.actions.report']
        xml_id = self._context.get('xml_id')
        rec_report = report_obj.search([('report_name','=',xml_id)],limit=1)
        if not rec_report:
            raise ValidationError(_( "Report not found, please try again to apply template report."))
        report = rec_report.report_action(self)
        return report

    @api.model
    def ssc_arch_preprocessing(self, arch):
        report_obj = self.env['ir.actions.report']
        model = self._name
        eview = etree.fromstring(arch)
        node_header = eview.xpath(".//header")
        node_sheet = eview.xpath(".//sheet")
        node_form = eview.xpath("//form")

        node_top = False
        reports = report_obj.search([('ssc_create_template_id.model_id.model','=',model)])
        if node_header:
            node_top = node_header
        elif node_sheet:
            node_sheet = node_sheet[0].getparent()
            node_sheet.insert(0, etree.SubElement(node_sheet, 'header'))
            node_header = eview.xpath(".//header")
            node_top = node_header
        else:
            node_form = node_form[0]
            node_form.insert(0, etree.SubElement(node_form, 'header'))
            node_header = eview.xpath(".//header")
            node_top = node_header

        if node_top and reports:
            node_top = node_top[0]
            count = 0
            for report in reports:
                name_report = report.ssc_create_template_id.name
                xml_id = report.report_name
                context = str({"xml_id": xml_id})
                node_top.insert(count, etree.SubElement(node_top, 'button', {'name': 'ssc_custom_print',  'string': name_report,  'type':'object', 'class':'oe_highlight btn-primary', 'context':context}))
                count+=1
        return etree.tostring(eview, encoding='unicode')


    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(Base, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form': 
            res['arch'] = self.ssc_arch_preprocessing(res['arch'])
        return res
