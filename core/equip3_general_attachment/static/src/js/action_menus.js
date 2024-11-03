odoo.define('equip3_general_attachment.ActionMenus', function (require) {
"use strict";

    var core = require('web.core');
    var Dialog = require('web.Dialog');
    const {patch} = require("web.utils");
    var framework = require('web.framework');
    var ActionMenus = require('web.ActionMenus');
    var field_utils = require('web.field_utils');
    var rpc = require('web.rpc');

    var _t = core._t;

    patch(ActionMenus, "equip3_general_attachment.ActionMenus", {
        /**
         * @override
         */
        async willStart() {
            this._super.apply(this, arguments);
            var self = this;
            this.hasAttachments = this.env.view.type === "form";
            this.attachment_item = []
            if (this.hasAttachments) {
                var attachment_item_list = await rpc.query({
                    model: 'ir.attachment',
                    method: 'search_read',
                    domain:[ ['res_model', '=', self.env.view.model], ['res_id', '=', self.props.activeIds[0]], ['type', '=', 'binary'] ],
                    fields: ['name', 'id'],
                }).then(function (result_search) {
                    return result_search
                })
                this.attachment_item.push({description:'Add Attachment',key:'add_attachment',callback:function(data, callbackId) {
                    $('#input_file_attachment_top').unbind('change');
                    $('#input_file_attachment_top').change(self._onAddAttachment.bind(self))
                    $('#input_file_attachment_top').click()
                }})
                for (var i = 0; i < attachment_item_list.length; ++i) {
                    var attach_id = attachment_item_list[i].id
                    this.attachment_item.push({removable:true,description:attachment_item_list[i].name,id:attach_id,callback:function(data, callbackId) {
                        window.open('/attachment/download?attachment_id='+data[0].id, '_blank')
                    }})
                }
                
                this.name_attachment = 'Attachments';
            }
        },

        _onAttachmentRemoved(ev) {
            ev.stopPropagation();
            framework.blockUI();
            var self = this;
            const { item } = ev.detail;

            rpc.query({
                model: 'ir.attachment',
                method: 'unlink',
                args: [parseInt(item.id)],
            }).then(function (result_create) {
                self.trigger('reload');
                $('.o_form_refresh_cp').click()
            })
        },

        _onAddAttachment: function (event) {
            var self = this;
            framework.blockUI();
            var detail_input_binary = $('#input_file_attachment_top')[0].files[0];
            var fr = new FileReader();
            fr.onload = function () {
            var datas = fr.result.split(',')[1];
            var data_create = {
                    'name':detail_input_binary.name,
                    'type':'binary',
                    'mimetype':detail_input_binary.type,
                    'res_model':self.env.view.model ,
                    'res_id':self.props.activeIds[0] ,
                    'datas':datas,
                    'public':true
                }
                
                rpc.query({
                    model: 'ir.attachment',
                    method: 'create',
                    args: [data_create],
                }).then(function (result_create) {
                    self.trigger('reload');
                    $('.o_form_refresh_cp').click()
                })

            };
            fr.readAsDataURL(detail_input_binary);
        }
    });

});
