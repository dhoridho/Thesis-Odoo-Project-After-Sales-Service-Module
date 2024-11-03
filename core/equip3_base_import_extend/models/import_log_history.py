from odoo import fields,models,api, _
import json 

class Equip3ImportLogHistory(models.Model):
    _name = 'import.log.history'
    _order = 'id desc'
    _description = 'Import Log History'
    
    
    name = fields.Char()
    import_datetime = fields.Datetime()
    model_id = fields.Char()
    cron_running = fields.Datetime()
    completed_date = fields.Datetime()
    inserted_record = fields.Integer()
    skipped_record = fields.Integer()
    error_record = fields.Integer()
    file_error_records = fields.Binary()
    file_error_name = fields.Char()
    total_record = fields.Integer()
    total_progress_char = fields.Char()
    error_log  = fields.Text()
    total_line = fields.Integer()
    batch_count = fields.Integer()
    total_line_progress = fields.Integer()
    total_line_char = fields.Char()
    state = fields.Selection([('on_queue','Queue'),('running','Running'),('partially_done','Partially Done'),('done','Done')],default="on_queue")
    list_data = fields.Char(default="[]")

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
    
    
    
    
    
    