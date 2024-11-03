odoo.define('awesome.CalendarController', function (require) {
    "use strict";

    var core = require('web.core');
    var CalendarController = require('web.CalendarController')
    var config = require('web.config')

    var _t = core._t;
    var QWeb = core.qweb;

    CalendarController.include({

        start: function() {
            var self = this
            return this._super.apply(this, arguments).then(function(){
                config.device.bus.on('size_changed', self, self._onDeviceSizeChanged);
                self._set_button_text();
            })
        },

        _renderButtonsParameters() {
            return {
                scales: this.scales,
                isMobile: config.device.isMobile
            };
        },

        _set_button_text: function() {
            if (config.device.isMobile) {
                this.$buttons.find('.o_calendar_button_day').text('D')
                this.$buttons.find('.o_calendar_button_week').text('W')
                this.$buttons.find('.o_calendar_button_month').text('M')
                this.$buttons.find('.o_calendar_button_year').text('Y')
            } else {
                this.$buttons.find('.o_calendar_button_day').text('day')
                this.$buttons.find('.o_calendar_button_week').text('week')
                this.$buttons.find('.o_calendar_button_month').text('month')
                this.$buttons.find('.o_calendar_button_year').text('year')
            }
        },

        /**
         * extend to support mobile device
         */
        _onDeviceSizeChanged: function() {
            
            if (!this.$buttons) {
                return
            }
            this._set_button_text()
        }
    })
})