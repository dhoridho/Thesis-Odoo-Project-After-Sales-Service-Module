from odoo import fields, models, api, _


class remove_action(models.Model):
    _inherit = 'remove.action'

    model = fields.Char (related='model_id.model', store= True)
    view_ids = fields.Many2many('ir.ui.view', 'remove_action_ir_ui_view_rel_ah', 'remove_action_id', 'ir_ui_view_id', 'Views', 
                                domain="[('model','=',model),('type','in',['tree','form','kanban']),('inherit_id','=', False)]",
                                help="The action like create ,edit,delete will be hidden in added views on list of selected model from defined users")
