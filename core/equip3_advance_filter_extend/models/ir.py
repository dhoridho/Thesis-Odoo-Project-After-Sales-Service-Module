from odoo import fields, models, api, _


class IrModelFields(models.Model):
    _inherit = "ir.model.fields"


    def name_get(self):
        if self._context.get('show_detail_field'):
            res = []
            for field in self:
                name_model = field.model
                if self._context.get('show_detail_field_relation') and field.relation:
                    name_model = field.relation
                res.append((field.id, '%s (%s) (%s)' % (field.field_description,field.name, name_model )))
        else:
            res = super(IrModelFields, self).name_get()
        return res


class IrFilters(models.Model):
    _inherit = "ir.filters"


    is_filter_pending_my_approval = fields.Boolean()
    approving_matrix_field_id = fields.Many2one('ir.model.fields','Approving Matrix Field')
    approving_matrix_line_related_field_id = fields.Many2one('ir.model.fields','Approving Matrix Line - Related Field')
    approving_matrix_line_user_field_id = fields.Many2one('ir.model.fields','Approving Matrix Line - User Field')
    approving_matrix_line_state_field_id = fields.Many2one('ir.model.fields','Approving Matrix Line - State Field')
    approving_matrix_line_state_is_equal_to_ids = fields.Many2many('ir.model.fields.selection',relation='approving_matrix_line_state_is_equal_to_rel',string='Approving Matrix Line - State Is Equal To')
    approving_related_model_id = fields.Many2one('ir.model','Approving Matrix Related Model')
    new_model_id = fields.Many2one('ir.model','New Model')


    @api.model
    def create(self, vals):
        if vals.get('is_filter_pending_my_approval') and 'user_ids' in vals:
            vals['user_ids'] = False
        fields_obj = self.env['ir.model.fields']
        model_obj = self.env['ir.model']
        result = super(IrFilters, self).create(vals)
        for data in result:
            if data.is_filter_pending_my_approval:
                model = model_obj.sudo().search([('model','=',data.model_id)],limit=1)
                data.domain = '[("x_is_include_filter_pending_my_approval","=",'+str(data.id)+')]'
                check_field = fields_obj.sudo().search([('name','=','x_is_include_filter_pending_my_approval'),('model_id','=',model.id)],limit=1)
                if not check_field and model:
                    dict_create = {
                        'name':'x_is_include_filter_pending_my_approval',
                        'ttype':'boolean',
                        'selection':False,
                        'field_description':'x_is_include_filter_pending_my_approval',
                        'model_id':model.id,
                    }
                    fields_obj.sudo().create(dict_create)
        return result


    def write(self, vals):
        fields_obj = self.env['ir.model.fields']
        model_obj = self.env['ir.model']
        res =  super(IrFilters, self).write(vals)
        for data in self:
            if data.is_filter_pending_my_approval:
                model = model_obj.sudo().search([('model','=',data.model_id)],limit=1)
                check_field = fields_obj.sudo().search([('name','=','x_is_include_filter_pending_my_approval'),('model_id','=',model.id)],limit=1)
                if not check_field and model:
                    dict_create = {
                        'name':'x_is_include_filter_pending_my_approval',
                        'ttype':'boolean',
                        'selection':False,
                        'field_description':'x_is_include_filter_pending_my_approval',
                        'model_id':model.id,
                    }
                    fields_obj.sudo().create(dict_create)
        return res



    @api.onchange('new_model_id')
    def _onchange_new_model_id(self):
        if self.new_model_id:
            self.model_id = self.new_model_id.model

    # @api.onchange('approving_matrix_field_id')
    # def _onchange_approving_matrix_field_id(self):
    #     model_obj = self.env['ir.model']
    #     fields_obj = self.env['ir.model.fields']
    #     for data in self:
    #         approving_related_model_id = False
    #         approving_matrix_line_related_field_id = False
    #         if data.approving_matrix_field_id.relation:
    #             model = model_obj.sudo().search([('model','=',data.approving_matrix_field_id.relation)],limit=1)
    #             if model:
    #                 approving_related_model_id = model.id
    #                 field = fields_obj.sudo().search([('name','=',data.approving_matrix_field_id.relation_field),('model_id','=',model.id)],limit=1)
    #                 if field:
    #                     approving_matrix_line_related_field_id = field.id
    #         data.approving_related_model_id = approving_related_model_id
    #         data.approving_matrix_line_related_field_id = approving_matrix_line_related_field_id