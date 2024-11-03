odoo.define('equip3_manuf_other_operations.MPSPeriodWidget', function(require){
    "use strict";

    var AbstractField = require('web.AbstractField');
    var registry = require('web.field_registry');
    var core = require('web.core');
    var QWeb = core.qweb;

    var FieldMPSPeriod = AbstractField.extend({
        className: 'o_field_mps_period',

        events: _.extend({}, AbstractField.prototype.events, {
            'change select': '_onChange',
        }),

        _renderEdit(){
            this._renderPeriodSelection('edit');
        },

        _renderReadonly(){
            this._renderPeriodSelection('readonly');
        },

        _renderPeriodSelection(mode){
            var periods = JSON.parse(this.record.data.period);
            var $el = QWeb.render('MPSPeriodWidget', {
                periods: periods
            });
            this.$el.html($el);
        },

        _onChange(ev){
            var $target = $(ev.target);
            var periods = JSON.parse(this.record.data.period);
            periods.selected = $target.val();
            this._setValue(JSON.stringify(periods));
        },

    });

    registry.add('mps_period', FieldMPSPeriod);

    return {
        FieldMPSPeriod: FieldMPSPeriod
    };

});