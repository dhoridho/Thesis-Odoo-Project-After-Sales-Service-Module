odoo.define('equip3_inventory_control.ActivePeriod', function (require) {
"use strict";

    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var QWeb = core.qweb;
    var _lt = core._lt;
    var registry = require('web.field_registry');

    var ActivePeriodWidget = AbstractField.extend({
        supportedFieldTypes: ['char'],
        buttonTemplate: 'FieldActivePeriodButton',
        popoverTemplate: 'FieldActivePeriodContent',
        description: _lt("Active Period"),
        trigger: 'focus',
        placement: 'top',
        html: true,
        events: _.extend({}, AbstractField.prototype.events, {
            'click .calculate_active_period': '_onClick',
            'click .btn-discard-active-period': '_onBtnDiscard',
            'click .btn-save-active-period': '_onBtnSave',
        }),
        _render: function () {
            this.$el.css('max-width', '35px');
            this.$el.html(QWeb.render(this.buttonTemplate));
            this.$el.find('.calculate_active_period').prop('special_click', true);
            this.$popover = $(QWeb.render(this.popoverTemplate));
            this.$popover.on('change', 'select.o_input', this._onSelectChange.bind(this));
            this.$popover.on('click', '.btn-discard-active-period', this._onBtnDiscard.bind(this));
            this.$popover.on('click', '.btn-save-active-period', this._onBtnSave.bind(this));
            this.$popover.on('click', this._onModalClick.bind(this));
        },
        _onSelectChange: function(ev) {
            $(ev.target).prop('special_click', true);
        },
        _onModalClick: function(ev) {
            $(ev.target).prop('special_click', true);
        },
        _onClick: function (ev) {
            var self = this;
            $('.active_period_modal:not(.d-none)').addClass('d-none');
            if (this.$popover.hasClass('d-none')) {
                this.$popover.removeClass('d-none');
                if (this.$popover.prev().length == 0) {
                    this.$popover.insertAfter(this.$el);
                }
            } else {
                this.$popover.addClass('d-none');
            }
        },
        _onBtnDiscard: function(ev) {
            $(ev.target).prop('special_click', true);
            this.$popover.find('select[name="active_period_start_date"] option:selected').prop("selected", false);
            this.$popover.find('select[name="active_period_start_month"] option:selected').prop("selected", false);
            this.$popover.find('select[name="active_period_end_date"] option:selected').prop("selected", false);
            this.$popover.find('select[name="active_period_end_month"] option:selected').prop("selected", false);
            this.$popover.addClass('d-none');
        },
        _onBtnSave: function(ev) {
            $(ev.target).prop('special_click', true);
            var self = this;
            var dataPointID = this.dataPointID;
            var active_period_start_date = $('select[name="active_period_start_date"] option:selected');
            var active_period_start_month = $('select[name="active_period_start_month"] option:selected');
            var active_period_end_date = $('select[name="active_period_end_date"] option:selected');
            var active_period_end_month = $('select[name="active_period_end_month"] option:selected');
            if (this.getParent() !== undefined && 
                this.getParent().allFieldWidgets !== undefined &&
                active_period_start_date.val() !== 'false' &&
                active_period_start_month.val() !== 'false' &&
                active_period_end_date.val() !== 'false' &&
                active_period_end_month.val() !== 'false'
                ) {
                if (this.viewType == "list") {
                    var allFieldWidgets = this.getParent().allFieldWidgets[dataPointID];
                    var active_periods = allFieldWidgets.filter(k => k.name == 'periods');
                    this._rpc({
                        method: 'set_active_period',
                        model: this.model,
                        args: [this.res_id, {
                            'start_date': active_period_start_date.val(),
                            'start_month': active_period_start_month.val(),
                            'end_date': active_period_end_date.val(),
                            'end_month': active_period_end_month.val(),
                        }],
                    }).then(function (result) {
                        self.$popover.find('.btn-discard-active-period').click();
                        active_periods[0]._setValue(result);
                    });
                }
                else {
                    var allFieldWidgets = this.getParent().allFieldWidgets[dataPointID];
                    allFieldWidgets.filter(k => k.name == 'start_date')[0]._setValue(active_period_start_date.val());
                    allFieldWidgets.filter(k => k.name == 'start_month')[0]._setValue(active_period_start_month.val());
                    allFieldWidgets.filter(k => k.name == 'end_date')[0]._setValue(active_period_end_date.val());
                    allFieldWidgets.filter(k => k.name == 'end_month')[0]._setValue(active_period_end_month.val());
                    this._onBtnDiscard();
                }
            }
        },
    });

    registry.add('active_period_select', ActivePeriodWidget);

    return {
        ActivePeriodWidget: ActivePeriodWidget,
    };

});