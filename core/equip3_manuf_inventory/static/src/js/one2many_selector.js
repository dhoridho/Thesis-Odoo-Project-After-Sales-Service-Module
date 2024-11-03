odoo.define('equip3_manuf_inventory.One2manySelector', function(require){
    "use strict";

    var relational_fields = require('web.relational_fields');
    var registry = require('web.field_registry');
    var ListRenderer = require('web.ListRenderer');

    var ListRendererSelector = ListRenderer.extend({
        init: function (parent, state, params) {
            this._super.apply(this, arguments);
            this.hasSelectors = true;
            this.selection = _.map(_.filter(this.state.data, o => o.data.is_checked), record => record.id);
        },

        _renderRow: function (record, index) {
            record.res_id = record.id;
            var $row = this._super(record, index);
            $row.find(".o_list_record_selector input[type='checkbox']").prop('checked', this.selection.includes(record.id));
            return $row
        },

        _updateRecordSelection(){
            var self = this;
            var selection = this.selection;
            _.each(this.state.data, record => {
                var changes = {is_checked: selection.includes(record.id)};
                self.trigger_up('field_changed', {
                    dataPointID: record.id,
                    changes: changes,
                    viewType: self.viewType,
                });
            });
        },

        _disableRecordSelectors: function () {
            return;
        },

        _enableRecordSelectors: function () {
            return;
        },

        _onSelectRecord: function (ev) {
            this._super.apply(this, arguments);
            this._updateRecordSelection();
        },

        _onToggleSelection: function (ev) {
            this._super.apply(this, arguments);
            this._updateRecordSelection();
        }
    });

    var FieldOne2ManySelector = relational_fields.FieldOne2Many.extend({
        className: 'o_field_one2many o_field_one2many_selector',

        _getRenderer: function () {
            return ListRendererSelector;
        },
    });

    registry.add('one2many_selector', FieldOne2ManySelector);

    return {
        FieldOne2ManySelector: FieldOne2ManySelector
    };
});