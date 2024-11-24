odoo.define('equip3_inventory_masterdata.UoMFormView', function(require){
    "use strict";

    var { BooleanToggle } = require('web.basic_fields');
    var registry = require('web.field_registry');
    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var view_registry = require('web.view_registry');

    var UomBooleanToggle = BooleanToggle.extend({

        _onClick: function (event) {
            event.stopPropagation();
            if (!this.$input.prop('disabled')) {
                this._setValue(!this.value, {force_save: this.res_id !== undefined});
            }
        },

        _setValue: function (value, options) {
            // we try to avoid doing useless work, if the value given has not changed.
            if (this._isLastSetValue(value)) {
                return Promise.resolve();
            }
            this.lastSetValue = value;
            try {
                value = this._parseValue(value);
                this._isValid = true;
            } catch (e) {
                this._isValid = false;
                this.trigger_up('set_dirty', {dataPointID: this.dataPointID});
                return Promise.reject({message: "Value set is not valid"});
            }
            if (!(options && options.forceChange) && this._isSameValue(value)) {
                return Promise.resolve();
            }

            var force_save = options && options.force_save === true ? true : false;

            var self = this;
            return new Promise(function (resolve, reject) {
                var changes = {};
                changes[self.name] = value;
                self.trigger_up('field_changed', {
                    dataPointID: self.dataPointID,
                    changes: changes,
                    viewType: self.viewType,
                    doNotSetDirty: options && options.doNotSetDirty,
                    notifyChange: !options || options.notifyChange !== false,
                    allowWarning: options && options.allowWarning,
                    onSuccess: resolve,
                    onFailure: reject,
                    uom_force_save: force_save
                });
            });
        },
    });

    var UoMFormController = FormController.extend({
        _onFieldChanged: function (ev) {
            if (ev.data.uom_force_save){
                ev.data.force_save = true;
                this.should_force_mode = true;
            }
            this._super.apply(this, arguments);
        },

        _confirmSave: function(id){
            if (id === this.handle && this.should_force_mode){
                this.should_force_mode = undefined;
                return this._setMode('edit');
            }
            return this._super.apply(this, arguments);
        }
    });

    var UomFormView = FormView.extend({
        config: _.extend(FormView.prototype.config, {
            Controller: UoMFormController
        })
    });

    registry.add('uom_boolean_toggle', UomBooleanToggle);
    view_registry.add('uom_form_view', UomFormView);


    return {
        UomBooleanToggle: UomBooleanToggle,
        UoMFormController: UoMFormController,
        UomFormView: UomFormView
    };
});``