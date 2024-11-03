odoo.define('equip3_manuf_other_operations.MPSWidget', function(require){
    "use strict";

    var AbstractField = require('web.AbstractField');
    var registry = require('web.field_registry');
    var core = require('web.core');
    var field_utils = require('web.field_utils');

    var QWeb = core.qweb;
    var _t = core._t;

    var FieldMPS = AbstractField.extend({
        className: 'o_field_mps',

        events: _.extend({}, AbstractField.prototype.events, {
            'change .o_mps_input': '_onChange',
            'click .o_mps_reset': '_onReset',
            'click .o_mps_details': '_onViewDetails',
            'change .o_mps_select_inline': '_onChangeBoM'
        }),

        _formatFloat(value){
            return field_utils.format.float(value, false, {'digits': [false, 2]});
        },

        _renderEdit(){
            this._renderMPSTable('edit');
        },

        _renderReadonly(){
            this._renderMPSTable('readonly');
        },

        _renderMPSTable(mode){
            var data = JSON.parse(this.record.data.datas);
            var $el = QWeb.render('MPSWidget', {
                ranges: data.ranges === undefined ? [] : data.ranges, 
                states: data.states === undefined ? {} : data.states,
                moment: moment,
                formatFloat: this._formatFloat,
                mode: mode,
                isReproduce: this.attrs.options.is_reproduce,
                debug: data.debug
            });
            this.$el.html($el);
        },

        _onChange(ev){
            var $target = $(ev.target);
            var productId = $target.data('product_id');
            var date = $target.data('date');
            var qtyType = $target.data('qty_type');
            var datas = JSON.parse(this.record.data.datas);
            datas.states[productId].forecasts[date][qtyType] = parseFloat($target.val());
            datas.states[productId].forecasts[date]['is_' + qtyType + '_edited'] = true;
            this._setValue(JSON.stringify(datas));
        },

        _onReset(ev){
            var $target = $(ev.target);
            var productId = $target.data('product_id');
            var date = $target.data('date');
            var qtyType = $target.data('qty_type');
            var datas = JSON.parse(this.record.data.datas);
            datas.states[productId].forecasts[date]['is_' + qtyType + '_edited'] = false;
            this._setValue(JSON.stringify(datas));
        },

        _onViewDetails: function(ev){
            var $target = $(ev.target);
            var data = JSON.parse(this.record.data.datas);
            var productId = $target.data('product_id');
            var state = data.states[productId];
            var workcenterIds = _.map(state.workcenters, o => o.id);

            var dates = Object.keys(state.forecasts);
            var periods = {
                selection: _.map(dates, date => [date, moment(date, 'YYYY-MM-DD').format('MMM DD')]),
                selected: dates[0]
            }

            this.trigger_up('button_clicked', {
                attrs: {
                    name: 'action_view_detail', 
                    type: 'object',
                    context: {
                        create: false,
                        default_warehouse_id: this.record.data.warehouse_id.res_id,
                        default_company_id: this.record.data.company_id.res_id,
                        default_bom_id: state.bom.id,
                        default_product_id: state.product.id,
                        default_resource_id: state.resource.id,
                        default_workcenter_ids: [[6, 0, workcenterIds]],
                        default_forecasted_data: JSON.stringify(state.forecasts),
                        default_period: JSON.stringify(periods)
                    }
                },
                record: this.record,
            });
        },

        _onChangeBoM(ev){
            var $target = $(ev.target);
            var productId = $target.data('product_id');
            var datas = JSON.parse(this.record.data.datas);
            datas.states[productId].bom = {
                id: parseInt($target.val()),
                display_name: $target.find(':selected').text()
            };
            datas.states[productId].is_bom_edited = true;
            this._setValue(JSON.stringify(datas));
        }

    });

    registry.add('mps', FieldMPS);

    return {
        FieldMPS: FieldMPS
    };
});