odoo.define('equip3_manuf_operations.free_widget', function (require) {
    'use strict';
    
    const AbstractField = require('web.AbstractField');
    const fieldRegistry = require('web.field_registry');
    const field_utils = require('web.field_utils');
    const utils = require('web.utils');
    const core = require('web.core');
    const QWeb = core.qweb;
    
    const FreeWidgetField = AbstractField.extend({
        supportedFieldTypes: ['float'],
    
        _render: function () {
            var data = Object.assign({}, this.record.data, {
                availability_uom_qty_str: field_utils.format.float(
                    this.record.data.availability_uom_qty,
                    this.record.fields.availability_uom_qty,
                    this.nodeOptions
                ),
                reserved_availability_str: field_utils.format.float(
                    this.record.data.reserved_availability,
                    this.record.fields.reserved_availability,
                    this.nodeOptions
                ),
                product_uom_qty_str: field_utils.format.float(
                    this.record.data.product_uom_qty,
                    this.record.fields.product_uom_qty,
                    this.nodeOptions
                ),
            });
            data.available = utils.round_decimals(
                data.availability_uom_qty, this.record.fields.availability_uom_qty.digits[1]) + utils.round_decimals(
                    data.reserved_availability, this.record.fields.reserved_availability.digits[1]) >= data.product_qty;
            this.$el.html(QWeb.render('equip3_manuf_operations.freeWidget', data));
            this.$('.o_forecast_report_button').on('click', this._onOpenReport.bind(this));
        },
    
        isSet: function () {
            return true;
        },

        _onOpenReport: function (ev) {
            ev.preventDefault();
            ev.stopPropagation();
            if (!this.recordData.id) {
                return;
            }
            this._rpc({
                model: 'stock.move',
                method: 'action_product_forecast_report',
                args: [this.recordData.id],
            }).then(action => {
                action.context = Object.assign(action.context || {}, {
                    active_model: 'product.product',
                    active_id: this.recordData.product_id.res_id,
                });
                this.do_action(action);
            });
        },
    });
    
    fieldRegistry.add('free_widget', FreeWidgetField);
    return FreeWidgetField;
});
    