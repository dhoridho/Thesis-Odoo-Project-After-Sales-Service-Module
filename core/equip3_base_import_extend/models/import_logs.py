import base64
from odoo import fields,models,api, _
from odoo.modules.module import get_module_path
import xlsxwriter
import os
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import json 

class Equip3ImportLogs(models.Model):
    _name = 'import.log'
    _order ='import_datetime desc, batch_count asc'
    _description = 'Import Log'
    
    name = fields.Char()
    cron_running = fields.Datetime()
    updated_record = fields.Integer()
    inserted_record = fields.Integer(compute="_compute_inserted_record")
    skipped_record = fields.Integer()
    error_record = fields.Integer()
    batch_count = fields.Integer(group_operator=False)
    file_error_records = fields.Binary()
    file_error_name = fields.Char()
    file = fields.Binary()
    total_progress = fields.Integer()
    total_record = fields.Integer()
    state = fields.Selection([('on_queue','Queue'),('running','Running'),('partially_done','Partially Done'),('done','Done')],default="on_queue")
    model_id = fields.Char()
    import_datetime = fields.Datetime()
    completed_date = fields.Datetime()
    field = fields.Char()
    column = fields.Char()
    options = fields.Char()
    file_name = fields.Char('File Name')
    file_type = fields.Char('File Type')
    error_log  = fields.Text()
    all_valid_record = fields.Integer()
    total_progress_char = fields.Char(compute='_compute_total_progress_char',string="Total Progress")
    list_data = fields.Char(default="[]")
    list_message_error = fields.Char(default="[]")
    log_history_id = fields.Many2one('import.log.history')
    excel_data = fields.Char()
    to_delete = fields.Char(default="[]")
    excel_fields = fields.Char()
    is_create_excel = fields.Boolean(default=False)
    total_line = fields.Integer()
    total_line_progress = fields.Integer()
    total_line_char = fields.Char(compute='_compute_total_line_char', string="Total Line Progress")
    count_empty_row = fields.Integer()
    count_child_line = fields.Char()
    fix_total_insert_record = fields.Integer()
    latest_count_total_line = fields.Integer()
    total_latest_count_total_line = fields.Integer()
    data_import = fields.Text()


    def act_view_records(self):
        self.ensure_one()
        list_data = json.loads(self.list_data)
        return {
                'name': _('View Records'),
                'res_model': self.model_id,
                'view_mode': 'tree',
                'domain': [('id','in',list_data)],
                'type': 'ir.actions.act_window',
            } 
    
    def create_excel(self):
        if eval(self.to_delete):
            to_write = [eval(self.excel_data)[i] for i in set(eval(self.to_delete))]
            excel_filename = f'error_data_import' + '.xlsx'
            module_path = get_module_path('equip3_base_import_extend')
            fpath = module_path + '/generated_files'
            if not os.path.isdir(fpath):
                os.mkdir(fpath)
            workbook = xlsxwriter.Workbook(module_path + '/generated_files/' + excel_filename)
            worksheet = workbook.add_worksheet()
            worksheet.set_column(0, 20, 17)
            col = -1    
            for header in range(len(eval(self.excel_fields))):
                col+=1
                worksheet.write(0,col,eval(self.excel_fields[header][0])) 
            row_err = 0
            row_data_len = -1
            for rec_error in to_write:
                row_err+=1
                row_data_len+=1
                col_err = -1
                for rec_error_data in range(len(rec_error)):
                    col_err+=1
                    worksheet.write(row_err,col_err,rec_error[rec_error_data])
            workbook.close()
            with open(module_path + '/generated_files/' + excel_filename, 'rb') as opened_file:
                base64_csv_file = base64.b64encode(opened_file.read())
                self.file_error_records = base64_csv_file
                self.file_error_name = excel_filename
            self.env.cr.commit()
            if self.log_history_id:
                self.log_history_id.file_error_records = self.file_error_records
                self.log_history_id.file_error_name = self.file_error_name
    
    
    
    
    # @api.depends('list_data')
    def _compute_inserted_record(self):
        for data in self:
            if data.fix_total_insert_record:
                data.inserted_record = data.fix_total_insert_record
            else:
                inserted = len(set(item for item in eval(data.list_data) if item is not False))
                if inserted > data.total_record:
                    inserted = data.total_record
                else:
                    data.inserted_record = inserted
    
    @api.depends('total_progress','total_record')
    def _compute_total_progress_char(self):
        for data in self:
            if data.total_progress > data.total_record:
                data.total_progress_char = f"{data.total_record} of {data.total_record}"
            else:
                data.total_progress_char = f"{data.total_progress} of {data.total_record}"

    @api.depends('total_line_progress','total_line')
    def _compute_total_line_char(self):
        for data in self:
            total_line_progress = data.total_line_progress
            if not data.count_empty_row and data.total_line == data.total_record and data.state == 'running':
                total_line_progress = data.total_progress
            if total_line_progress > data.total_line:
                data.total_line_char = f"{data.total_line} of {data.total_line}"
            else:
                data.total_line_char = f"{total_line_progress} of {data.total_line}"


    def update_execution_import_logs(self):
        cron_obj = self.env['ir.cron']
        log_obj = self.env['import.log']
        datetime_now = datetime.now()
        check_logs_on_queue = log_obj.search([('state','=','on_queue')],limit=1)
        check_logs_on_running = log_obj.search([('state','=','running')],limit=1)
        if check_logs_on_queue and not check_logs_on_running:
            self.env.ref('equip3_base_import_extend.hashmicro_action_import').sudo().write({'nextcall':datetime_now + relativedelta(minutes=2)})

        return True
        
    
    def acion_import(self):
        wizard_import_obj = self.env['base_import.import']
        if self and len(self) == 1:
            to_import = self
        else:
            to_import = self.sudo().search([('state','in',['running','on_queue'])],order='id asc',limit=1)
            if to_import:
                child_recs = self.sudo().search([('id','!=',to_import.id),('name','=',to_import.name),('state','in',['running','on_queue'])],order='id asc')
                if child_recs:
                    to_import |= child_recs
        for data in to_import:
            field = eval(data.field)
            column = eval(data.column)
            option = eval(data.options)
            action_context = option.get('action_context',{})

            if data.state == 'done':
                continue
            if data.state == 'running':
                ICPSudo = self.env['ir.config_parameter'].sudo()
                last_proggress_data = ICPSudo.get_param('equip3_base_import_extend.last_proggress_data')
                total_skip = data.inserted_record - int(last_proggress_data)
                if total_skip <= 0:
                    total_skip = 0
                
                option['skip'] = total_skip 
                data.total_progress = total_skip 
                data.total_latest_count_total_line += data.latest_count_total_line 
            if data.total_progress != data.total_record:
                action_context['import_from_log'] = data
                action_context['no_check_access'] = data
                action_context['tracking_disable'] = True
                
                result = wizard_import_obj.with_context(action_context).do_scheduler(field,column,option,data)
                # while result['nextrow'] != 0:
                #     option['skip'] = result['nextrow']
                #     result = data.base_import_id.do_scheduler(field,column,option,data)
                
                
                
    def acion_create_excel(self):
        ICPSudo = self.env['ir.config_parameter'].sudo()
        is_split_processing = ICPSudo.get_param('equip3_base_import_extend.is_split_processing')
        if is_split_processing:
            to_create = self.sudo().search([('is_create_excel','=',False),('state','in',['partially_done','done'])],order='id asc')
            for data in to_create:
                data.create_excel()
                data.is_create_excel = True

                
    