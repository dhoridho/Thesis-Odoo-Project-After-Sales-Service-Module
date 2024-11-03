
from crypt import methods
import string,os,xlsxwriter
from odoo.http import Controller, request, route
from .authentication import APIAuthentication
from odoo.modules import get_module_path
from random import randint
from pytz import timezone
from datetime import datetime,timedelta
import random
from odoo.exceptions import AccessDenied
from ...equip3_general_features.models.email_wa_parameter import waParam
from .helper import *


class HashmicroApiExportExcel(APIAuthentication):
    @http.route(['/api/download_excel/<string:object_model>/<int:id>','/api/download_excel/<string:object_model>',],type="http", auth="user")
    def export_excel(self, object_model, id=None, **kw):
        auth, user, invalid = self.valid_authentication(kw)
        if not user or invalid:
            return self.get_response(401, '401', {'code': 401, 'message': 'Authentication required'})
        record_model  = request.env['ir.model'].sudo().search([('model','=',object_model)]).field_id.filtered(lambda line:line.name in kw.get('fields') and line.name != 'id')
        module_path = get_module_path('restapi')
        fpath = module_path + '/generated_files/'
        csv_filename = 'exported-record.xlsx'
        workbook = xlsxwriter.Workbook(module_path + '/generated_files/' +csv_filename)
        worksheet = workbook.add_worksheet()
        if not os.path.isdir(fpath):
            os.mkdir(fpath)         
        bold = workbook.add_format({
            'bold': True, 'border': 1, 'align': 'center', 'valign': 'vcenter'})   
        worksheet.set_column(0, 19, 22)
        col_header = 0
        row_header = 0
        for data in eval(kw.get('fields')):
            record_model  = request.env['ir.model'].sudo().search([('model','=',object_model)]).field_id.filtered(lambda line:line.name == data and line.name != 'id')
            worksheet.write(row_header, col_header, record_model.field_description, bold)
            self.write_record(object_model,worksheet,record_model,row_header,col_header,kw,workbook)
            col_header += 1 
        workbook.close()
        with open(module_path + '/generated_files/' + csv_filename, 'rb') as opened_file:
            base64_csv_file = base64.b64encode(opened_file.read())
            attachment = request.env['ir.attachment'].create({
                'name': csv_filename,
                'type': 'binary',
                'datas': base64_csv_file,
            })

            
        return self.get_response(200, '200', {"code":200,
                                              "attachment_id":attachment.id,
                                              "filename":attachment.name,
                                              "datas":attachment.datas.decode("utf-8"),
                                              "data":"Export  Successful"
                                              })
        
        
        
    def write_record(self,object_model,worksheet,field,row,col,kw,workbook):
        domain = []
        if kw.get('ids'):
            domain.append(('id','in',eval(kw.get('ids'))))
        currency_format = workbook.add_format({
            'align': 'center',
            'num_format': '_(* #,##0_);_(* (#,##0);_(* "-"??_);_(@_)',
            'valign': 'vcenter'
        })
        centerformmat = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
        })
        dateformmat = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'num_format': 'dd/mm/yy'
        })
        dateformmat_time = workbook.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'num_format': 'dd/mm/yy HH:MM:SS'
        })
        merge_format = workbook.add_format({
            'bold': 1,
            'align': 'center',
            'valign': 'vcenter',
            'text_wrap': 'true',
            'border': 1
        })
        record_data = request.env[object_model].sudo().search(domain)
        if not record_data:
            return self.record_not_found()
        row = row+1
        for data in record_data:
            if field.ttype in ['char','text']:
                worksheet.write(row,col,data[field.name],centerformmat)
            elif field.ttype in ['many2one']:
                model = request.env[field.relation].sudo().search([],limit=1)        
                worksheet.write(row,col,data[field.name][model._rec_name],centerformmat)
            elif field.ttype in ['many2many']:
                model = request.env[field.relation].sudo().search([],limit=1)
                data_to_write = ','.join(str(rec[model._rec_name]) for rec in data[field.name])        
                worksheet.write(row,col,data_to_write,centerformmat)
            elif field.ttype in ['date']:
                worksheet.write(row,col,data[field.name],dateformmat)
            elif field.ttype in ['datetime']:
                worksheet.write(row,col,data[field.name],dateformmat_time)
            elif field.ttype in ['integer','float']:
                worksheet.write(row,col,data[field.name],currency_format)
            elif field.ttype in ['selection']:
                worksheet.write(row,col,dict(request.env[object_model].fields_get(allfields=[field.name])[field.name]['selection'])[data[field.name]] if data[field.name] != False else '-',centerformmat)
            row +=1