odoo.define('equip3_manuf_operations.form_controller', function(require){

    var FormController = require('web.FormController');
    var dialogs = require('web.view_dialogs');
    var core = require('web.core');
    var _t = core._t;


    var customFormController = FormController.include({

        _onOpenOne2ManyRecord: async function (ev) {
            ev.stopPropagation();
            var data = ev.data;
            var context = data.context;
            if (!context){
                context = {};
            }
            if (!context.force_readonly){
                this._super(ev);
                return;
            }

            var record;
            if (data.id) {
                record = this.model.get(data.id, {raw: true});
            }
    
            // Sync with the mutex to wait for potential onchanges
            await this.model.mutex.getUnlockedDef();
            
            let buttons = [{
                text: _t("Close"),
                classes: "btn-secondary o_form_button_cancel",
                close: true,
            }];
            new dialogs.FormViewDialog(this, {
                context: data.context,
                domain: data.domain,
                fields_view: data.fields_view,
                model: this.model,
                on_saved: data.on_saved,
                on_remove: data.on_remove,
                parentID: data.parentID,
                readonly: true,
                deletable: record ? data.deletable : false,
                recordID: record && record.id,
                res_id: 100,
                res_model: data.field.relation,
                shouldSaveLocally: true,
                title: (record ? _t("Open: ") : _t("Create ")) + (ev.target.string || data.field.string),
                buttons: buttons
            }).open();
        },

    });

    return customFormController;
});