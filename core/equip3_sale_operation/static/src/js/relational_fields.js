odoo.define('equip3_sale_operation.relational_fields', function (require) {
    "use strict";

    var relational_fields = require('web.relational_fields');
    var FieldMany2One = relational_fields.FieldMany2One;
    var dialogs = require('web.view_dialogs');

    var core = require('web.core');
    var _t = core._t;

    FieldMany2One.include({
        _onExternalButtonClick: function () {
        if (
            (this.model === 'sale.order' &&
            this.name === "brand")
        ){
            if (!this.value) {
                this.activate();
                return;
            }
            var self = this;
            var context = this.record.getContext(this.recordParams);
            this._rpc({
                model: this.field.relation,
                method: 'get_formview_id',
                args: [[this.value.res_id]],
                context: context,
            })
            .then(function (view_id) {
                new dialogs.FormViewDialog(self, {
                    res_model: self.field.relation,
                    res_id: self.value.res_id,
                    context: context,
                    title: _t("Open: ") + self.string,
                    view_id: view_id,
                    readonly: true,
                    on_saved: function (record, changed) {
                        if (changed) {
                            const _setValue = self._setValue.bind(self, self.value.data, {
                                forceChange: true,
                            });
                            self.trigger_up('reload', {
                                db_id: self.value.id,
                                onSuccess: _setValue,
                                onFailure: _setValue,
                            });
                        }
                    },
                }).open();
            });
        } else {
            return this._super.apply(this, arguments);
        }
        },
    });
});