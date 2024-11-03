# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) 2016 GRIMMETTE,LLC <info@grimmette.com>

import base64
import copy
from datetime import date, datetime, timedelta
from itertools import chain
import logging
import os
import re
import shutil
import tempfile
from zipfile import ZipFile, ZIP_DEFLATED, BadZipfile
from lxml import etree
from random import randint
from odoo import api, fields, models, tools, SUPERUSER_ID, _
from odoo.exceptions import AccessError, UserError
from odoo.tools.mimetypes import guess_mimetype
from odoo.tools.safe_eval import safe_eval
from odoo.tools import float_round
_logger = logging.getLogger(__name__)
SUPPORTED_FORMATS = ('.xlsx', '.xlsm')
class ReportExcelExportGen(models.TransientModel):
    _name = 'report_excel_export_gen'
    _description = " "
    def create_conf(self, datas=None):
        datas = datas if datas is not None else {}
        tmp_dir = tempfile.gettempdir()
        zip_tmp_dir = tempfile.mkdtemp(prefix='conf.tmp.', dir=tmp_dir)        
        active_ids_all = datas['ids']
        for active_id in active_ids_all:
            active_ids = [active_id]
            tmpfile_wfd, tmpfile_wpath = tempfile.mkstemp(suffix='.conf', prefix='conf.tmpl.tmp.')
            base_template_fp = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'export_template.conf')
            self.copyFile(base_template_fp,tmpfile_wpath)        
            module_dependencies = []
            ReportExcel_Array = (
                                        'out_file_name',
                                        'name', 
                                        'sheet_reference', 
                                        'description',
                                        'description_report',
                                        'root_model_id',
                                        )
            ReportExcelParam_Array = (
                                        'sequence',
                                        'report_excel_id',
                                        'name',
                                        'code',
                                        'type_param',
                                        'param_ir_model_id',
                                        'param_required',
                                        )
            ReportExcelSection_Array = (
                                        'report_excel_id',
                                        'root_model_id',
                                        'sequence',
                                        'name',
                                        'parent_id',
                                        'type_data',
                                        'level',
                                        'root_model_related_field_id',
                                        'root_model_name',
                                        'check_root_model',
                                        'section',
                                        'section_level',
                                        'section_start',
                                        'section_end',
                                        'domain',
                                        'description',
                                        )
            ReportExcelFields_Array = (
                                        'sequence',
                                        'cell',
                                        'report_excel_section_id',
                                        'group_by',
                                        'aggregate',
                                        'aggregate_id',
                                        'having_operator',
                                        'having_selection',
                                        'having_param_id',
                                        'having_value_type',
                                        'having_value_float',
                                        'having_value_date',
                                        'having_value_datetime',
                                        'sort_by',
                                        'formula',
                                        'formulas',
                                        'check_root_model',
                                        'root_model_id',
                                        'root_model_name',
                                        'model_field_selector',
                                        'field_type',
                                        'image_bool',
                                        'colOff',
                                        'rowOff',
                                        'cx',
                                        'cy',
                                        'locked_canvases_bool',
                                        'description',
                                        )
            ReportExcelTemlateFields_Array = (
                                        'name',
                                        'type',
                                        'datas',
                                        'res_id',
                                        'res_model',
                                        )
            parser = etree.XMLParser(remove_blank_text=True) 
            template_xml =  etree.parse(tmpfile_wpath, parser)
            node_data = template_xml.xpath('data')[0]
            if len(self.env[datas['active_model']].search([('id', 'in', active_ids)])):        
                report_obj = self.env[datas['active_model']].search([('id', 'in', active_ids)])[0]
            else:
                raise UserError('THE REPORT IS ARCHIVED! TO EXPORT, YOU NEED TO MAKE IT ACTIVE!')
            node_record_ReportExcel = etree.Element('record')
            node_data.append(node_record_ReportExcel)
            node_record_ReportExcel.attrib['id'] = ''.join([report_obj._name.replace('.', '_'),'_', str(randint(100000000, 999999999))])
            node_record_ReportExcel.attrib['model'] = report_obj._name
            for f in ReportExcel_Array:
                field = report_obj.fields_get(f)[f]    
                if f == 'root_model_id':
                    eval_str = "obj().env['ir.model'].search([('model', '=', '%s')], limit=1).id" % (report_obj.root_model_id.model,)             
                    node_field = etree.Element('field')
                    node_record_ReportExcel.append(node_field)
                    node_field.attrib['name'] = f
                    node_field.attrib['model'] = "report.excel"
                    node_field.attrib['eval'] = eval_str
                    field_relation = field['relation']
                    module_name = self.env['ir.model.data'].search([('res_id', '=', report_obj[f].id),('model', '=', field_relation)], limit=1).module
                    module_dependencies.append(module_name)                
                    continue
                if field['type'] == 'many2one':
                    field_relation = field['relation']
                    external_id = self.env['ir.model.data'].search([('res_id', '=', report_obj[f].id),('model', '=', field_relation)], limit=1).name
                    module_name = self.env['ir.model.data'].search([('res_id', '=', report_obj[f].id),('model', '=', field_relation)], limit=1).module
                    module_dependencies.append(module_name)
                    params_str = ''.join([module_name,'.', external_id,])             
                    node_field = etree.Element('field')
                    node_record_ReportExcel.append(node_field)
                    node_field.attrib['name'] = f
                    node_field.attrib['ref'] = params_str
                else:
                    node_field = etree.Element('field')
                    node_record_ReportExcel.append(node_field)
                    node_field.attrib['name'] = f
                    if report_obj[f] != False:
                        node_field.text = str(report_obj[f])
                    else:
                        node_field.attrib['eval'] = str(report_obj[f])                
                    if f == 'name':
                        node_field.text = str(report_obj[f])
            list_external_id_params = ()
            for report_excel_param_obj in report_obj.report_excel_param_ids:
                node_record_param = etree.Element('record')
                node_data.append(node_record_param)
                node_record_param.attrib['id'] = ''.join([report_excel_param_obj._name.replace('.', '_'),'_', str(randint(100000000, 999999999))])
                node_record_param.attrib['model'] = report_excel_param_obj._name
                list_external_id_params += ((report_excel_param_obj.code, node_record_param.attrib['id'],),) 
                for f in ReportExcelParam_Array:
                    field = report_excel_param_obj.fields_get(f)[f]    
                    if field['type'] == 'many2one':
                        field_relation = field['relation']
                        external_id = self.env['ir.model.data'].search([('res_id', '=', report_excel_param_obj[f].id),('model', '=', field_relation)], limit=1).name
                        module_name = self.env['ir.model.data'].search([('res_id', '=', report_excel_param_obj[f].id),('model', '=', field_relation)], limit=1).module
                        module_dependencies.append(module_name)
                        if f == 'report_excel_id':
                            params_str = node_record_ReportExcel.attrib['id']
                        else:
                            if external_id:
                                params_str = ''.join([module_name,'.', external_id,])
                            else:
                                node_field = etree.Element('field')
                                node_record_param.append(node_field)
                                node_field.attrib['name'] = f
                                node_field.attrib['eval'] = '[]'
                                continue
                        if params_str:
                            node_field = etree.Element('field')
                            node_record_param.append(node_field)
                            node_field.attrib['name'] = f
                            node_field.attrib['ref'] = params_str
                    else:
                        node_field = etree.Element('field')
                        node_record_param.append(node_field)
                        node_field.attrib['name'] = f
                        if report_excel_param_obj[f] != False:
                            node_field.text = str(report_excel_param_obj[f])
                        else:
                            node_field.attrib['eval'] = str(report_excel_param_obj[f])                
            for section_obj in report_obj.report_excel_section_ids:
                self.get_report_section(node_record_ReportExcel.attrib['id'], node_data, section_obj, ReportExcelSection_Array, ReportExcelFields_Array, None, module_dependencies, list_external_id_params)
            if len(list_external_id_params):
                node_record_ReportExcel_update_1 = etree.Element('record')
                node_data.append(node_record_ReportExcel_update_1)
                node_record_ReportExcel_update_1.attrib['id'] = node_record_ReportExcel.attrib['id']
                node_record_ReportExcel_update_1.attrib['model'] = report_obj._name
                node_field = etree.Element('field')
                node_record_ReportExcel_update_1.append(node_field)
                node_field.attrib['name'] = "report_excel_param_ids"
                eval_str = ''
                for ex_id in list_external_id_params:
                    eval_str = eval_str + "[4, ref('%s'), False]," % (ex_id[1])
                eval_str = '[' + eval_str + ']'
                node_field.attrib['eval'] = eval_str   
            comment_template_version = etree.Comment(' ====== Odoo V.14 ====== ')
            module_dependencies_txt = 'Module Dependencies: ' +  str(list(set(module_dependencies)))
            node_odoo = template_xml.getroot()
            comment_module_dependencies = etree.Comment(module_dependencies_txt)
            node_odoo.insert(0, comment_template_version)  
            node_odoo.insert(1, comment_module_dependencies)  
            with open(tmpfile_wpath, 'wb') as Content_Types_out:
                template_xml.write(Content_Types_out,
                                    xml_declaration=True, 
                                    encoding="UTF-8", 
                                    standalone="yes", 
                                    )        
            out_file_name_xml = report_obj.display_name + '.conf'
            out_file_name_xml = out_file_name_xml.replace(' - ','_')
            out_file_name_xml = out_file_name_xml.replace(', ','_')
            out_file_name_xml = out_file_name_xml.replace(',','_')
            out_file_name_xml = out_file_name_xml.replace(' ','_')
            out_file_name_xml = out_file_name_xml.replace('/','_')
            out_file_name_xml = out_file_name_xml.replace('\\','_')
            out_file_name_xml = out_file_name_xml.replace('(','')
            out_file_name_xml = out_file_name_xml.replace(')','')
            out_file_name_xml = out_file_name_xml.lower()
            if datas['multiple_export']:
                self.copyFile(tmpfile_wpath, os.path.join(zip_tmp_dir, out_file_name_xml))
            else:
                with open(tmpfile_wpath,'rb') as m:
                    data_attach = {
                        'res_name': '',
                        'name': out_file_name_xml,
                        'datas': base64.b64encode(m.read()),
                        'type': "binary",
                        'res_model': 'report.excel',
                        'res_id': datas['ids'][0],
                    }
                    try:
                        new_attach = self.env['ir.attachment'].create(data_attach)
                    except AccessError:
                        _logger.info("Cannot save %r as attachment", out_file_name_xml)
                    else:
                        _logger.info('The attachment %s is now saved in the database', out_file_name_xml)
                new_attach_fpath = ''
                new_attach_fname = ''
                if new_attach: 
                    new_attach_fname = new_attach['name']
                    store_fname = new_attach['store_fname']
                    new_attach_fpath = new_attach._full_path(store_fname)
                file_obj = {
                    'type': 'ir.actions.act_url',
                    'url': '/report_excel_export?id=%s' % (new_attach.id,),
                    'target': 'self',
                }
                return file_obj
        z_tmpfile_wfd, z_tmpfile_wpath = tempfile.mkstemp(suffix='.zip', prefix='zip.tmp.')
        zip_file = ZipFile(z_tmpfile_wpath, 'w')        
        for root, dirs, files in os.walk(zip_tmp_dir): 
            for file in files:
                zip_file.write(os.path.join(root,file), arcname = file)          
        zip_file.close()        
        out_file_name_zip = 'report_excel_configurations.zip'
        with open(z_tmpfile_wpath,'rb') as m:
            data_attach = {
                'res_name': '',
                'name': out_file_name_zip,
                'datas': base64.b64encode(m.read()),
                'type': "binary",
                'res_model': 'report.excel',
                'res_id': datas['ids'][0],
            }
            try:
                new_attach = self.env['ir.attachment'].create(data_attach)
            except AccessError:
                _logger.info("Cannot save %r as attachment", out_file_name_zip)
            else:
                _logger.info('The attachment %s is now saved in the database', out_file_name_zip)
        new_attach_fpath = ''
        new_attach_fname = ''
        if new_attach: 
            new_attach_fname = new_attach['name']
            store_fname = new_attach['store_fname']
            new_attach_fpath = new_attach._full_path(store_fname)
        file_obj = {
            'type': 'ir.actions.act_url',
            'url': '/report_excel_export?id=%s' % (new_attach.id,),
            'target': 'self',
        }
        return file_obj
    def get_report_section(self, report_excel_ref, node_data, section_obj, ReportExcelSection_FieldsArray, ReportExcelFields_FieldsArray, parent_ref=None, module_dependencies=[], list_external_id_params=()):
        node_record_section = etree.Element('record')
        node_data.append(node_record_section)
        node_record_section.attrib['id'] = ''.join([section_obj._name.replace('.', '_'),'_', str(randint(100000000, 999999999))])
        node_record_section.attrib['model'] = section_obj._name
        for f in ReportExcelSection_FieldsArray:
            field = section_obj.fields_get(f)[f]    
            if f == 'root_model_id':
                eval_str = "obj().env['ir.model'].search([('model', '=', '%s')], limit=1).id" % (section_obj.root_model_id.model,)             
                node_field = etree.Element('field')
                node_record_section.append(node_field)
                node_field.attrib['name'] = f
                node_field.attrib['model'] = "report.excel.section"
                node_field.attrib['eval'] = eval_str
                field_relation = field['relation']
                module_name = self.env['ir.model.data'].search([('res_id', '=', section_obj[f].id),('model', '=', field_relation)], limit=1).module
                module_dependencies.append(module_name)                
                continue
            if field['type'] == 'many2one':
                field_relation = field['relation']
                external_id = self.env['ir.model.data'].search([('res_id', '=', section_obj[f].id),('model', '=', field_relation)], limit=1).name
                module_name = self.env['ir.model.data'].search([('res_id', '=', section_obj[f].id),('model', '=', field_relation)], limit=1).module
                module_dependencies.append(module_name)
                if f == 'report_excel_id':
                    if len(section_obj.report_excel_id):
                        params_str = report_excel_ref
                    else:
                        continue
                elif f == 'parent_id': 
                    if len(section_obj.parent_id):
                        params_str = parent_ref
                    else:
                        node_field = etree.Element('field')
                        node_record_section.append(node_field)
                        node_field.attrib['name'] = f
                        node_field.attrib['eval'] = '[]'
                        continue
                else:
                    if f == 'root_model_related_field_id': 
                        if len(section_obj.parent_id):
                            params_str = parent_ref
                        else:
                            node_field = etree.Element('field')
                            node_record_section.append(node_field)
                            node_field.attrib['name'] = f
                            node_field.attrib['eval'] = '[]'
                            continue
                    params_str = ''.join([module_name,'.', external_id,])             
                if params_str:
                    node_field = etree.Element('field')
                    node_record_section.append(node_field)
                    node_field.attrib['name'] = f
                    node_field.attrib['ref'] = params_str
            else:
                node_field = etree.Element('field')
                node_record_section.append(node_field)
                node_field.attrib['name'] = f
                if section_obj[f] != False:
                    node_field.text = str(section_obj[f])
                else:
                    node_field.attrib['eval'] = str(section_obj[f])                
        for excel_field_obj in section_obj.report_excel_fields_ids:
            node_record = etree.Element('record')
            node_data.append(node_record)
            node_record.attrib['id'] = ''.join([excel_field_obj._name.replace('.', '_'),'_', str(randint(100000000, 999999999))])
            node_record.attrib['model'] = excel_field_obj._name
            for f in ReportExcelFields_FieldsArray:
                if f == 'root_model_id':
                    eval_str = "obj().env['ir.model'].search([('model', '=', '%s')], limit=1).id" % (section_obj.root_model_name,)             
                    node_field = etree.Element('field')
                    node_record.append(node_field)
                    node_field.attrib['name'] = f
                    node_field.attrib['model'] = "report.excel.fields"
                    node_field.attrib['eval'] = eval_str
                    continue
                field = excel_field_obj.fields_get(f)[f]    
                if field['type'] == 'many2one':
                    field_relation = field['relation']
                    external_id = self.env['ir.model.data'].search([('res_id', '=', excel_field_obj[f].id),('model', '=', field_relation)], limit=1).name
                    module_name = self.env['ir.model.data'].search([('res_id', '=', excel_field_obj[f].id),('model', '=', field_relation)], limit=1).module
                    module_dependencies.append(module_name)
                    if f == 'report_excel_section_id':
                        params_str = node_record_section.attrib['id']
                    elif f == 'having_param_id':
                        if excel_field_obj.having_param_id.id:
                            for i in list_external_id_params:
                                if excel_field_obj.having_param_id.code == i[0]:
                                    params_str = i[1]
                        else:
                            node_field = etree.Element('field')
                            node_record.append(node_field)
                            node_field.attrib['name'] = f
                            node_field.attrib['eval'] = '[]'
                            continue
                    elif not external_id:
                        node_field = etree.Element('field')
                        node_record.append(node_field)
                        node_field.attrib['name'] = f
                        node_field.attrib['eval'] = '[]'
                        continue
                    else:
                        params_str = ''.join([module_name,'.', external_id,])             
                    if params_str:
                        node_field = etree.Element('field')
                        node_record.append(node_field)
                        node_field.attrib['name'] = f
                        node_field.attrib['ref'] = params_str
                else:
                    node_field = etree.Element('field')
                    node_record.append(node_field)
                    node_field.attrib['name'] = f
                    if excel_field_obj[f] != False:
                        node_field.text = str(excel_field_obj[f])      
                    else:
                        node_field.attrib['eval'] = str(excel_field_obj[f])          
        for child_section_obj in section_obj.children_ids:
            self.get_report_section(report_excel_ref, node_data, child_section_obj, ReportExcelSection_FieldsArray, ReportExcelFields_FieldsArray, node_record_section.attrib['id'], module_dependencies, list_external_id_params)
    def copyFile(self, src, dest):
        try:
            shutil.copy(src, dest)
        except shutil.Error as e:
            _logger.info('Error: %s' % e)
        except IOError as e:
            _logger.info('Error: %s' % e.strerror)
