odoo.define('ks_list_view_manager.KsEditableListRenderer', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        _onWindowClicked: function (event){
            var class_name_list = event.target.classList
            var self = this;
            if (this.ks_lvm_mode && self.ks_list_view_data){
                if (class_name_list[0] == 'btn' || class_name_list[0] == 'breadcrumb' || class_name_list[0] == 'o_cp_bottom_left' || class_name_list[0] == 'o_list_view'){
                    this.ks_list_view_data['ks_editable_mode'] = true;

                }else{
                    this.ks_list_view_data['ks_editable_mode'] = false;
                }
            }
            this._super.apply(this, arguments)

        },
    })

});