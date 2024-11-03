from odoo import fields, models, api, _

class remove_action(models.Model):
    _name = 'remove.action'
    _description = "Models Right"


    access_management_id = fields.Many2one('access.management', 'Access Management')
    model_id = fields.Many2one('ir.model', 'Model')
    view_data_ids = fields.Many2many('view.data', 'remove_action_view_data_rel_ah', 'remove_action_id', 'view_data_id', 'Hide Views',
                                     help="The views are added on list will be hidden in selected model from the defined users.")
    server_action_ids = fields.Many2many('action.data' ,'remove_action_server_action_data_rel_ah', 'remove_action_id', 'server_action_id', 'Hide Actions', domain="[('action_id.binding_model_id','=',model_id),('action_id.type','!=','ir.actions.report')]",
                                         help="The actions are added on list will be hidden in selected model from the defined users.")
    report_action_ids = fields.Many2many('action.data' ,'remove_action_report_action_data_rel_ah', 'remove_action_id', 'report_action_id', 'Hide Reports', domain="[('action_id.binding_model_id','=',model_id),('action_id.type','=','ir.actions.report')]",
                                         help="The Reports are added on list will be hidden in selected model from the defined users.")
    restrict_export = fields.Boolean('Hide Export',
                                     help="Export Button will be hidden in selected model from the defined users.")
    restrict_import = fields.Boolean('Hide Import',
                                     help="Import Button will be hidden in selected model from the defined users.")
    restrict_upload_acc_move = fields.Boolean('Hide Upload / OCR ',  help="Hide Upload / OCR in account.move")
    readonly = fields.Boolean('Read-Only')

    restrict_create = fields.Boolean('Hide Create',help="Create Button will be hidden in selected model from the defined users.")
    restrict_edit = fields.Boolean('Hide Edit',
                                   help="Edit Button will be hidden in selected model from the defined users.")
    restrict_delete = fields.Boolean('Hide Delete',
                                     help="Delete Button will be hidden in selected model from the defined users.")
    restrict_archive_unarchive = fields.Boolean('Hide Archive/Unarchive',help="Archive and Unarchive action will be hidden in selected model from the defined users.")
    restrict_duplicate = fields.Boolean('Hide Duplicate',help="Duplicate action will be hidden in selected model from the defined users.")
    restrict_chatter = fields.Boolean('Hide Chatter',help="The Chatter will be hidden in selected model from the defined users.")
    model_name = fields.Char('Model Name',compute='_compute_model_name')

    def _compute_model_name(self):
        for data in self:
            data.model_name = data.model_id.model or ''

    @api.onchange('model_id')
    def _onchange_model_id(self):
        for rec in self:
            if rec.model_id:
                rec.model_name = rec.model_id.model 
