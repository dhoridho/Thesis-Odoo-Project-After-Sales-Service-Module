odoo.define('equip3_inventory_reports.ExpiringProductCalendar', function(require){
    "use strict";

    const core = require('web.core');
    const Widget = require('web.Widget');
    const { DateWidget } = require('web.datepicker');
    const AbstractAction = require('web.AbstractAction');

    const QWeb = core.qweb;
    const _t = core._t;

    function arrayRotate(arr, reverse) {
        if (reverse) arr.unshift(arr.pop());
        else arr.push(arr.shift());
        return arr;
    }

    function groupBy(quants, fieldName){
        let data = {};
        _.each(quants, (quant) => {
            let fieldValue = quant[[fieldName]];
            if (fieldValue in data){
                data[[fieldValue]].push(quant);
            } else {
                data[[fieldValue]] = [quant];
            }
        });
        return data;
    }

    function createWheelStopListener(element, callback, timeout) {
        var handle = null;
        var onScroll = function() {
            if (handle) {
                clearTimeout(handle);
            }
            handle = setTimeout(callback, timeout || 200);
        };
        element.addEventListener('wheel', onScroll);
        return function() {
            element.removeEventListener('wheel', onScroll);
        };
    }

    const expDateWidget = DateWidget.extend({
        init: function(params, options){
            this._super.apply(this, arguments);
            this.options = _.extend({
                format : 'dddd, MMM DD, YYYY',
                calendarWeeks: false,
            }, options || {});
        },

        _onDateTimePickerShow: function () {
            let $table = $('.bootstrap-datetimepicker-widget').find('.datepicker-days table');
            if ($table.length){
                $table.addClass('o_expiring_table');
            }
            this._super.apply(this, arguments);
        },

        _formatClient: function (value) {
            if (value === false || isNaN(value)) {
                return "";
            }
            return value.format(this.options.format);
        },
        
        _parseClient: function (value) {
            var self = this;
            if (!value) {
                return false;
            }
            var datetime = moment(value, this.options.format);
            if (datetime.isValid()) {
                if (datetime.year() === 0) {
                    datetime.year(moment().year());
                }
                if (datetime.year() >= 1000) {
                    datetime.toJSON = function () {
                        return this.clone().locale('en').format(self.options.format);
                    };
                    return datetime;
                }
            }
            throw new Error(_.str.sprintf(core._t("'%s' is not a correct datetime"), value));
        },

        changeDatetime: function () {
            this._super.apply(this, arguments);
            this.trigger_up('calendar_date_change');
        }
    });

    const expWeekWidget = expDateWidget.extend({

        init: function(params, options){
            this._super.apply(this, arguments);
            this.options = _.extend({
                format : '[Week] Wo DD/MM/YY',
                calendarWeeks: true,
            }, options || {});
        },

        _onDateTimePickerShow: function () {
            let $table = $('.bootstrap-datetimepicker-widget').find('.datepicker-days table');
            $table.addClass('o_datepicker_week');
            this._super.apply(this, arguments);
        }
    });

    const expMonthWidget = expDateWidget.extend({
        init: function(params, options){
            this._super.apply(this, arguments);
            this.options = _.extend({
                format : 'MMMM YYYY',
            }, options || {});
        }
    });

    const Filter = Widget.extend({
        template: 'ExpiringFilter',

        events: {
            'input .o_search_input': '_onInput',
            'click .o_label': '_onClick',
            'change .o_checkbox': '_onChange',
            'click .o_remove_icon': '_onDeselect'
        },

        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.parentClass = params.parentClass;
            this.name = params.name;
            this.label = params.label;
            this.model = params.model;
            this.records = params.records || [];
            this.activeIds = _.map(this.records, (record) => record.id);
        },

        start: function(){
            this.$el = $(this.el);
            var self = this;
            _.each(this.records, function(record){
                record.$el = self.$el.find('.o_record[data-name="'+ self.name + '_' + record.id +'"]');
                record.$checkbox = record.$el.find('.o_checkbox');
            });
            return this._super.apply(this, arguments);
        },

        _computeActiveIds: function(){
            let activeIds = _.map(_.filter(this.records, (record) => record.$checkbox.is(':checked')), (filtered) => filtered.id);
            if (!activeIds.length){
                activeIds = _.map(this.records, (record) => record.id);
            }
            this.activeIds = activeIds;
        },

        _getRecord: function(recordId){
            return _.find(this.records, (record) => record.id === recordId);
        },

        _onInput: function(ev){
            ev.stopPropagation();
            let query = $(ev.target).val().toLowerCase();
            this._searchRecord(query);
        },

        _onClick: function(ev){
            let $target = $(ev.target);
            this.$el.find('[data-id="' + $target.attr('for') + '"]').click();
        },

        _onChange: function(ev){
            this._computeActiveIds();
            this.trigger_up('filter_change');
        },

        _onDeselect: function(ev){
            ev.stopPropagation();
            _.each(this.records, (record) => {
                record.$checkbox.prop('checked', false);
            });
            this._computeActiveIds();
            this.trigger_up('filter_change');
        },

        _searchRecord: function(query){
            if (query === ''){
                _.each(this.records, (record) => {
                    record.$el.removeClass('d-none');
                });
            } else {
                _.each(this.records, (record) => {
                    if (record.name.toLowerCase().includes(query)){
                        record.$el.removeClass('d-none');
                    } else {
                        record.$el.addClass('d-none');
                    }
                });
            }
        },

        _getActiveFilters: function(){
            return _.filter(this.records, (record) => record.$checkbox.is(':checked'));
        },
    });

    const updatebleWidget = Widget.extend({
        updateble: true,

        init: function(parent, params){
            this._super.apply(this, arguments);
            this.parent = parent;
            this.parentClass = params.parentClass;
            this.active = params.active || false;
            this.now = this.parent.now;
        },

        willStart: function(){
            if (this.active){
                this._updateData();
            }
            return this._super.apply(this, arguments);
        },

        start: function(){
            this.$el = $(this.el);
            var self = this;
            return this._super.apply(this, arguments).then(() => {
                self._updateElements();
            });
        },

        _updateData: function(){
            let locationIds = this.parent.filters.locations.activeIds;
            let categIds = this.parent.filters.categories.activeIds;
            let result = _.filter(this.parent.quants, (q) => locationIds.includes(q.location_id) && categIds.includes(q.categ_id));
            this._buildData(result);
        },

        _updateElements: function(){},

        _buildData: function(result){
            this.data = result;
        },

        _update: function(){
            this._updateData();
            if (this.$el){
                this._updateElements();
            }
        },

        now: function(){
            return this.parent.now;
        }
    });

    const NearlyExpire = updatebleWidget.extend({
        template: 'ExpiringNearlyExpire',

        jsLibs: [
            '/web/static/lib/Chart/Chart.js',
        ],

        events: {
            'click .o_button_date': '_toggleDropdown',
            'click .o_input_date': '_toggleDropdown',
            'click .o_item:not(".o_custom_range")': '_onSelect',
            'click .o_custom_range': '_toggleCustomRange',
            'click .o_button_apply_custom': '_onApplyCustomDate',
            'change input[name="chart_options"]': '_onChangeChart'
        },

        custom_events: {
            calendar_date_change: '_onCustomDateChange'
        },

        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.value = 'today'
            this.chartType = 'horizontalBar'
            this.startDate = this.now.startOf('day');
            this.endDate = this.now.endOf('day');
            this.label = 'Nearly Expire';
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self.$dropdown = self.$el.find('.o_nearly_dropdown');
                self.$inputDate = self.$el.find('.o_input_date');
                self.$customRange = self.$el.find('.o_item_custom');

                self.buttons = {
                    apply_custom_date: self.$el.find('.o_button_apply_custom')
                };
                self._renderChart();
            });
        },

        _buildData: function(result){
            let internalQuants = _.filter(result, (quant) => quant.is_internal);
            let startDate = moment.max([this.startDate, moment()]);

            var self = this;
            let quants = _.filter(internalQuants, (q) => q.alert_date >= startDate && q.expiration_date <= self.endDate);
            let colors = ['#57c845', '#efa146', '#1270b0', '#df3333'];
            let productGroups = groupBy(quants, 'product_id');
            let data = [];
            _.each(Object.keys(productGroups), (productId, index) => {
                data.push({
                    id: productId,
                    name: productGroups[[productId]][0].product_name,
                    quantity: _.map(productGroups[[productId]], (quant) => quant.quantity).reduce((a, b) => a + b, 0),
                    color: colors[index % colors.length]
                });
            });
            this.data = data;
        },

        _update: function(){
            this._super.apply(this, arguments);
            this._renderChart();
        },

        _getChartOptions: function(){
            if (this.chartType === 'pie'){
                if (this.data.length > 5){
                    return {
                        legend: {
                            display: false
                        }
                    };
                }
                return {};
            }
            return {
                scales: {
                    xAxes: [{
                        ticks: {
                            beginAtZero: true
                        }
                    }],
                },
                legend: {
                    labels: {
                        boxWidth: 0
                    }
                }
            };
        },

        _renderChart: function(){
            if (this.chart){
                this.chart.destroy();
            }

            let data = this.data || {}
            this.chart = new Chart(this.$el.find('#o_nearly_expired_chart'), {
                type: this.chartType,
                data: {
                    labels: _.map(data, function(record){return record.name}),
                    datasets: [
                        {
                            label: 'Quantity',
                            data: _.map(data, function(record){return record.quantity}),
                            backgroundColor: _.map(data, function(record){return record.color}),
                            borderWidth: 0
                        }
                    ]
                },
                options: this._getChartOptions()
            });
        },

        _getValue: function(){
            let start = moment();
            let end = moment();
            if (this.value === 'tommorow'){
                start.add(1, 'days');
                end.add(1, 'days');
            } else if (this.value === 'next_7_days'){
                start.add(1, 'days');
                end.add(8, 'days');
            } else if (this.value === 'this_month'){
                start = start.startOf('month');
                end = end.endOf('month');
            } else if (this.value === 'next_month'){
                start.add(1, 'months').startOf('month');
                end.add(1, 'months').endOf('month');
            } else if (this.value === 'this_year'){
                start.startOf('year');
                end.endOf('year');
            } else if (this.value === 'next_year'){
                start.add(1, 'years').startOf('year');
                end.add(1, 'years').endOf('year');
            } else if (this.value === 'custom'){
                start = this.customStart.getValue();
                end = this.customEnd.getValue();
            }
            return {
                start: start.startOf('day'),
                end: end.endOf('day')
            }
        },

        _setValue: function(value){
            this.value = value;
            let {start, end} = this._getValue();
            this.startDate = start;
            this.endDate = end;

            this._updateData();
            this._renderChart();
        },

        _formatDate: function(date){
            return date.format('MMM DD, YYYY');
        },

        _renderDate: function(){
            let {start, end} = this._getValue();
            this.$inputDate.html(this._formatDate(start) + ' - ' + this._formatDate(end));
        },

        _toggleDropdown: function(ev){
            if (ev){
                ev.stopPropagation();
            }
            this.$dropdown.toggleClass('d-none');
        },

        _toggleCustomRange: function(ev){
            if (ev){
                let $target = $(ev.target);
                if ($target.parents('.o_item_custom').length){
                    return;
                }
            }
            this.$customRange.toggleClass('d-none');
            if (!this.customEnd){
                this.customEnd = new expDateWidget(this);
                this.customEnd.prependTo(this.$customRange);
            }
            if (!this.customStart){
                this.customStart = new expDateWidget(this);
                this.customStart.prependTo(this.$customRange);
            }
        },

        _onSelect: function(ev){
            ev.stopPropagation();
            this._setValue($(ev.target).data('value'));
            this._toggleDropdown();
            this._renderDate();
        },

        _onApplyCustomDate: function(ev){
            ev.stopPropagation();
            this._setValue('custom');
            this._toggleCustomRange();
            this._toggleDropdown();
            this._renderDate();
        },

        _onCustomDateChange: function(ev){
            let start = this.customStart ? this.customStart.getValue() : false;
            let end = this.customEnd ? this.customEnd.getValue() : false;
            if (start && end && end >= start){
                this.buttons.apply_custom_date.prop('disabled', false);
            } else {
                this.buttons.apply_custom_date.prop('disabled', true);
            }
        },

        _onChangeChart: function(ev){
            let $target = $(ev.target);
            this.chartType = $target.data('name');
            this._renderChart();
        }
    });

    const Info = updatebleWidget.extend({
        template: 'ExpiringInfo',

        events: {
            'click': '_onClick'
        },

        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.name = params.name;
            this.label = params.label;
            this.icon = params.icon;
        },

        _buildData: function(result){
            let now = moment();
            let internalQuants = _.filter(result, (quant) => quant.is_internal);

            let quants = []
            if (this.name === 'current'){
                quants = _.filter(internalQuants, (quant) => quant.expiration_date > now);
            } else if (this.name === 'notify'){
                quants = _.filter(internalQuants, (quant) => quant.alert_date <= now && quant.expiration_date >= now);
            } else {
                quants = _.filter(internalQuants, (quant) => quant.expiration_date <= now);
            }
            this.data = {
                count: _.map(quants, (quant) => quant.quantity).reduce((a, b) => a + b, 0),
                lot_ids: _.unique(_.map(quants, (quant) => quant.lot_id))
            };
        },

        _update: function(){
            this._super.apply(this, arguments);
            this.renderElement();
        },

        _onClick: function(ev){
            ev.stopPropagation();
            this.do_action({
                res_model: 'stock.production.lot',
                name: _t('Lots/Serial Numbers'),
                views: [[false, 'list'], [false, 'form']],
                domain: [['id', 'in', this.data.lot_ids]],
                type: 'ir.actions.act_window',
                context: {
                    'search_default_group_by_product': 1
                }
            });
        },
    });

    const ExpirationForecast = updatebleWidget.extend({
        template: 'ExpiringExpirationForecast',

        events: {
            'click td:not(.o_year)': '_onClickCell'
        },

        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.nYear = params.nYear || 2;
            this.label = 'Expiration Forecast';
            this.header = [''].concat(moment.monthsShort());
        },

        _buildData: function(result){
            let now = moment();
            let internalQuants = _.filter(result, (quant) => quant.is_internal);

            let years = [];
            let date, months, quants;
            for (let y=0; y < this.nYear; y++){
                date = now.clone().add(y, 'years');
                months = [];
                for (let m=0; m < 12; m++){
                    date.set('month', m);
                    quants = _.filter(internalQuants, (quant) => quant.expiration_date >= date.startOf('month') && quant.expiration_date <= date.endOf('month'));
                    months.push({
                        count: _.unique(_.map(quants, (quant) => quant.product_id)).length,
                        lot_ids: _.unique(_.map(quants, (quant) => quant.lot_id))
                    })
                }
                years.push({
                    year: date.year(),
                    lot_ids: _.unique(_.map(months, (month) => month.lot_ids).flat(1)),
                    months: months
                });
            }

            this.data = years;
        },

        _update: function(){
            this._super.apply(this, arguments);
            this.renderElement();
        },

        _onClickCell: function(ev){
            ev.stopPropagation();
            let lotIds = $(ev.currentTarget).data('lots');
            if (typeof(lotIds) === 'string'){
                lotIds = _.map(lotIds.split(','), function(x){return parseInt(x);});
            } else {
                lotIds = [lotIds];
            }
            
            this.do_action({
                res_model: 'stock.production.lot',
                name: _t('Lots/Serial Numbers'),
                views: [[false, 'list'], [false, 'form']],
                domain: [['id', 'in', lotIds]],
                type: 'ir.actions.act_window',
                context: {
                    'search_default_group_by_product': 1
                }
            });
        },
    });

    const Status = updatebleWidget.extend({
        template: 'ExpiringStatus',

        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.label = 'Status'
        },

        _buildData: function(result){
            let now = moment();
            let quants = _.filter(result, (quant) => quant.is_internal);

            let quantities = {
                current: _.map(_.filter(quants, (q1) => q1.expiration_date > now), (q2) => q2.quantity).reduce((a, b) => a + b, 0),
                notify: _.map(_.filter(quants, (q1) => q1.alert_date <= now && q1.expiration_date >= now), (q2) => q2.quantity).reduce((a, b) => a + b, 0),
                expired: _.map(_.filter(quants, (q1) => q1.expiration_date <= now), (q2) => q2.quantity).reduce((a, b) => a + b, 0),
            };
            let total = _.map(Object.keys(quantities), (key) => quantities[[key]]).reduce((a, b) => a + b, 0);

            this.data = [
                {
                    name: 'current',
                    label: _t('Current'),
                    percentage: total > 0 ? Math.round((quantities.current / total) * 100, 2) : 0
                },
                {
                    name: 'notify',
                    label: _t('Notify'),
                    percentage: total > 0 ? Math.round((quantities.notify / total) * 100, 2) : 0
                },
                {
                    name: 'expired',
                    label: _t('Expired'),
                    percentage: total > 0 ? Math.round((quantities.expired / total) * 100, 2) : 0
                },
            ];
        },

        _updateElements: function(){
            var self = this;
            _.each(this.data, (record) => {
                record.$progressBar = self.$el.find('.o_status_progressbar.o_' + record.name);
                record.$percentage = self.$el.find('.o_status_percentage.o_' + record.name);
            });
        },

        _updateProgressBar: function(){
            _.each(this.data, (record) => {
                record.$progressBar.css('width', record.percentage + '%');
                record.$percentage.html(record.percentage + '%');
            });
        },

        _update: function(){
            this._super.apply(this, arguments);
            this._updateProgressBar();
        }
    });

    const RecentEvents = updatebleWidget.extend({
        template: 'ExpiringRecentEvents',

        events: {
            'click .o_event': '_onClickEvent'
        },

        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.event_type = params.event_type;
            this.label = params.label;
            this.data = [];
        },

        _buildData: function(result){
            let now = moment();
            let quants = _.filter(result, (quant) => quant.is_internal);
            if (this.event_type === 'notify'){
                quants = _.filter(quants, (quant) => quant.alert_date <= now && quant.expiration_date >= now);
            } else {
                quants = _.filter(quants, (quant) => quant.expiration_date < now);
            }
            let lots = groupBy(quants, 'lot_id');
            let data = [];
            var self = this;
            _.each(Object.keys(lots), (lotId) => {
                let quant = lots[[lotId]][0];
                data.push({
                    lot_id: lotId,
                    product_id: quant.product_id,
                    product_name: quant.product_name,
                    event_date: self.event_type === 'notify' ? quant.alert_date : quant.expiration_date,
                    removal_date: quant.removal_date,
                    lot_name: quant.lot_name
                });
            });
            data.sort((a, b) => b.event_date.toDate() - a.event_date.toDate());
            this.data = data;
        },

        _update: function(){
            this._super.apply(this, arguments);
            this.renderElement();
        },

        _onClickEvent: function(ev){
            ev.stopPropagation();
            let lotId = $(ev.currentTarget).data('lot');

            this.do_action({
                res_model: 'stock.production.lot',
                name: _t('Lots/Serial Numbers'),
                views: [[false, 'form']],
                res_id: lotId,
                type: 'ir.actions.act_window',
                context: {
                    'search_default_group_by_product': 1
                }
            });
        },
    });

    const Calendar = updatebleWidget.extend({
        template: 'ExpiringCalendar',

        events: {
            'click .o_button_prev': '_onClickPrev',
            'click .o_button_next': '_onClickNext',
            'click .o_button_print': '_onPrint',
            'change input[name="calendar_type"]': '_onChangeType',
            'click td.o_day': '_onClickDay',
            'click td.o_head': '_onClickHead',

            // tooltip events
            'mouseenter td.o_clickable': '_onMouseEnterCell',
            'mouseleave td.o_clickable': '_onMouseLeaveCell',
            'wheel tbody': '_onWheelTbody'
        },

        custom_events: {
            calendar_date_change: '_onDatetimeChanged'
        },

        init: function (parent, params) {
            this._super.apply(this, arguments);
            this.type = 'month';
            this.current = moment();
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self._setDatepicker().then(function(){
                    self._updateContent();
                });
            });
        },

        _buildData: function(result){
            let now = this.current.clone();
            let time_from = now.clone().startOf(this.type === 'week' ? 'isoWeek' : this.type);
            let time_to = now.clone().endOf(this.type === 'week' ? 'isoWeek' : this.type);
            let quants = _.filter(result, (q) => q.is_internal && (q.expiration_date.isBetween(time_from, time_to, 'days', '[]') || q.alert_date >= time_from));
            let lots = groupBy(quants, 'lot_id');
            let columnLength = this.type === 'day' ? 1 : 7;
            let format = this.type === 'month' ? 'YYYY-MM-DD' : 'YYYY-MM-DD HH'

            let rows = [];
            if (this.type === 'month'){
                let nextWeek = time_from.clone().startOf('isoWeek');
                while (nextWeek < time_to){
                    rows.push(nextWeek);
                    nextWeek = nextWeek.clone().add(1, 'weeks');
                }
            } else {
                for (let h=0; h < 24; h++){
                    rows.push(time_from.clone().add(h, 'hours'));
                }
            }
            
            var self = this;
            let data = [];
            for (let r=0; r < rows.length; r++){
                let startDate = rows[r].clone();
                let rowId = startDate.format(this.type === 'month' ? 'WW' : 'HH');

                let days = [];
                for (let c=0; c < columnLength; c++){
                    let date = startDate.clone().add(c, 'days');
                    let colId = rowId + '_' + date.format('DD')

                    let selectedLots = [];
                    _.each(Object.keys(lots), (lotId) => {
                        let lot = lots[[lotId]][0];
                        if ((lot.expiration_date && lot.expiration_date.date() === date.date()) || (lot.alert_date && lot.alert_date.date() === date.date())){
                            if (self.type === 'month' || lot.expiration_date.hour() === date.hour() || lot.alert_date.hour() === date.hour()){
                                selectedLots.push(lot);
                            }
                        }
                    });

                    let events = [];
                    _.each(selectedLots, (lot) => {
                        let event_type;
                        if (lot.expiration_date && lot.expiration_date.date() === date.date()){
                            if (self.type === 'month' || (self.type !== 'month' && lot.expiration_date.hour() === date.hour())){
                                event_type = 'expired';
                            }
                        } else if (lot.alert_date && lot.alert_date >= moment()){
                            event_type = 'notify';
                        }
                        if (event_type){
                            events.push({
                                event_type: event_type,
                                product_name: lot.product_name, 
                                lot_id: lot.lot_id,
                                lot_name: lot.lot_name,
                                alert_date: lot.alert_date,
                                expiration_date: lot.expiration_date,
                                removal_date: lot.removal_date
                            });
                        }
                    });

                    console.log(events)
                    
                    let inCurrentMonth = this.type === 'month' && now.month() === date.month();
                    let className = this.type !== 'month' || inCurrentMonth ? 'o_day o_clickable' : 'o_empty';
                    if (date.format(format) === moment().format(format)){
                        className += ' o_current';
                    }
                    let hasExpired = _.filter(events, (e) => e.event_type === 'expired').length > 0;
                    let hasNotify = _.filter(events, (e) => e.event_type === 'notify').length > 0;
                    let hasLines = this.type === 'month' ? inCurrentMonth && (hasExpired || hasNotify) : hasExpired || hasNotify;
                    let showValue = this.type === 'month' && inCurrentMonth;

                    days.push({
                        id: colId,
                        value: date.format('DD'),
                        class_name: className,
                        date: date,
                        events: events,
                        has_expired: hasExpired,
                        has_notify: hasNotify,
                        has_lines: hasLines,
                        show_value: showValue
                    })
                }
                data.push({
                    id: rowId,
                    value: days[0].date.format(this.type === 'month' ? 'WW' : 'HH:mm'),
                    class_name: 'o_head o_clickable',
                    dates: _.map(days, (day) => day.date),
                    events: _.map(days, (day) => day.events).flat(1),
                    has_expired: _.any(days, (day) => day.has_expired),
                    has_notify: _.any(days, (day) => day.has_notify),
                    has_lines: _.any(days, (day) => day.has_lines),
                    show_value: true,
                    cols: days
                });
            }
            this.data = data;
        },

        _update: function(){
            this._super.apply(this, arguments);
            this._updateCalendar();
        },

        _header: function(){
            let weekdays = arrayRotate(moment.weekdaysShort());
            if (this.type === 'month'){
                return [_t('Week')].concat(weekdays);
            } else if (this.type === 'week'){
                let firstDay = this.current.startOf('isoWeek');
                return [_t('Hour')].concat(_.map(weekdays, (name, index) => name + ', ' + firstDay.clone().add(index, 'days').format('DD')));
            } else {
                return [_t('Hour'), this.current.format('dddd, MMMM DD, YYYY')];
            }
        },

        _updateContent: function(){
            let $table = $(QWeb.render('ExpiringCalendarContent', {widget: this}));
            this._setTooltip();
            this.$el.find('.o_calendar_content').html($table);
            createWheelStopListener($table.find('tbody')[0], this._onWheelTbodyStop.bind(this));
        },

        _setTooltip: function(){

            function addTooltip(record, title, subtitle){
                let $tooltip = $(QWeb.render('ExpiringTooltip', {
                    events: record.events, 
                    title: title, 
                    subtitle: subtitle, 
                    tooltipId: record.id
                }));
                $tooltip.hide();
                self.$el.append($tooltip);
                self.tooltips.push({id: record.id, $el: $tooltip});
            }

            var self = this;
            _.each(this.tooltips || [], (tooltip) => { tooltip.$el.remove(); });

            this.tooltips = [];
            _.each(this.data, (row) => {
                let title = {};
                let subtitle = {};
                let dates = row.dates;
                let first = dates[0];
                let last = dates[dates.length - 1];

                if (self.type === 'month'){
                    title = {label: _t('Week') + ' ' + row.value};
                    subtitle = {label: first.format('MMMM DD, YYYY') + ' - ' + last.format('MMMM DD, YYYY'), icon: 'fa-calendar'};
                } else {
                    title = {label: first.format('HH:mm:ss') + ' - ' + first.clone().add(1, 'hours').format('HH:mm:ss'), icon: 'fa-clock-o'};
                    if (self.type === 'week'){
                        subtitle = {label: first.format('MMMM DD, YYYY') + ' - ' + last.format('MMMM DD, YYYY'), icon: 'fa-calendar'};
                    } else {
                        subtitle = {label: first.format('MMMM DD, YYYY'), icon: 'fa-calendar'};
                    }
                }
                addTooltip(row, title, subtitle)

                _.each(row.cols, (col) => {
                    let title = {};
                    let subtitle = {};
                    let date = col.date;
                    if (self.type === 'month'){
                        title = {label: date.format('dddd')};
                        subtitle = {label: date.format('MMMM DD, YYYY'), icon: 'fa-calendar'};
                    } else {
                        title = {label: date.format('dddd, MMMM DD, YYYY'), icon: 'fa-calendar'};
                        subtitle = {label: date.format('HH:mm:ss') + ' - ' + date.clone().add(1, 'hours').format('HH:mm:ss'), icon: 'fa-clock-o'};
                    }
                    addTooltip(col, title, subtitle)
                });
            });
        },

        _showTooltip: function(target){
            let rect = target.getBoundingClientRect();
            let tooltip = _.find(this.tooltips, (tooltip) => tooltip.id == $(target).data('col'));
            tooltip.$el.css('top', (rect.top - 300) + 'px');
            tooltip.$el.css('left', (rect.left - 150 + (rect.width / 2)) + 'px');

            this.$el.find('.o_expiring_tooltip_inner:not([data-col="' + tooltip.id + '"])').hide();
            tooltip.$el.on('mouseleave', () => { tooltip.$el.hide(); })
            tooltip.$el.show();
        },

        _onMouseEnterCell: function(ev){
            this._showTooltip(ev.currentTarget);
        },

        _onMouseLeaveCell: function(ev){
            let $relatedTarget = $(ev.relatedTarget);
            if (!$relatedTarget.hasClass('o_expiring_tooltip_inner') && $relatedTarget.parents('.o_expiring_tooltip_inner').length === 0){
                let $currentTarget = $(ev.currentTarget);
                let tooltip = _.find(this.tooltips, (tooltip) => tooltip.id == $currentTarget.data('col'));
                tooltip.$el.hide();
            }
        },

        _onWheelTbody: function(ev){
            this.$el.find('.o_expiring_tooltip_inner').hide();
        },

        _onWheelTbodyStop: function(){
            let target = _.find(document.querySelectorAll(':hover'), (el) => $(el).hasClass('o_clickable'));
            if (target){
                this._showTooltip(target);
            }
        },

        _setDatepicker: function(){
            if (this.datepicker){
                this.datepicker.destroy();
            }

            let Widget;
            if (this.type === 'month'){
                Widget = expMonthWidget;
            } else if (this.type === 'week'){
                Widget = expWeekWidget;
            } else {
                Widget = expDateWidget;
            }
            
            this.datepicker = new Widget(this, {defaultDate: this.current});
            let $container = this.$el.find('.o_button_selector_container');
            $container.html('');
            return this.datepicker.appendTo($container);
        },

        _onDatetimeChanged: function(ev){
            let value = this.datepicker.getValue();
            if (value){
                value = value.startOf('day');
            }
            this.current = value;
            this._updateData();
            this._updateContent();
        },

        _onClickPrev: function(ev){
            ev.stopPropagation();
            this.current.subtract(1, this.type + 's');
            this._updateCalendar();
        },

        _onClickNext: function(ev){
            ev.stopPropagation();
            this.current.add(1, this.type + 's');
            this._updateCalendar();
        },

        _onPrint: function(ev){
            ev.stopPropagation();
            this.trigger_up('print_calendar', {
                title: this.current.format(this.datepicker.options.format), 
                header: this._header(), 
                data: this.data,
                type: this.type
            });
        },

        _onClickHead: function(ev){
            if (this.type !== 'month'){
                return;
            }
            ev.stopPropagation();
            let $target = $(ev.currentTarget);
            let record = _.find(this.data, (row) => row.id == $target.data('col'));
            this.current = record.dates[0].clone();
            this.$el.find('[name="calendar_type"][data-name="week"]').click();
        },

        _onClickDay: function(ev){
            ev.stopPropagation();
            let $target = $(ev.currentTarget);
            let $parent = $target.parent('tr');
            let row = _.find(this.data, (row) => row.id == $parent.data('row'));
            let record = _.find(row.cols, (col) => col.id == $target.data('col'));

            if (this.type === 'day'){
                let lotIds = _.unique(_.map(record.events, (e) => e.lot_id));
                return this.do_action({
                    res_model: 'stock.production.lot',
                    name: _t('Lots/Serial Numbers'),
                    views: [[false, 'list'], [false, 'form']],
                    domain: [['id', 'in', lotIds]],
                    type: 'ir.actions.act_window'
                });
            }

            this.current = record.date.clone();
            this.$el.find('[name="calendar_type"][data-name="day"]').click();
        },

        _onChangeType: function(ev){
            let $target = $(ev.target);
            this.type = $target.data('name');
            this._updateCalendar();
        },

        _updateCalendar: function(){
            var self = this;
            this._updateData();
            this._setDatepicker().then(function(){
                self._updateContent();
            });
        }
    });

    const ExpiringProductCalendarAction = AbstractAction.extend({
        template: 'ExpiringProductCalendar',

        custom_events: {
            filter_change: '_onFilterChange',
            print_calendar: '_onPrintCalendar'
        },

        init: function (parent, action, options) {
            this._super.apply(this, arguments);
            this.now = moment();
        },

        willStart: function () {
            var self = this;
            var filterProm = this._rpc({
                model: 'expiring.product.calendar',
                method: 'get_quants'
            }).then(function(result){
                self.quants = result.quants;
                _.each(self.quants, (quant) => {
                    _.each(['expiration_date', 'alert_date', 'removal_date'], (dateName) => {
                        quant[[dateName]] = moment(quant[[dateName]], 'YYYY-MM-DD HH:mm:ss');
                    });
                });
                self.filters = {
                    categories: new Filter(self, {name: 'categ_id', label: 'Categories', records: result.categories, parentClass: 'o_categories_box'}),
                    locations: new Filter(self, {name: 'location_id', label: 'Locations', records: result.locations, parentClass: 'o_locations_box'})
                };
            });
            return Promise.all([this._super.apply(this, arguments), filterProm]);
        },

        start: async function () {
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self.widgets = {
                    nearlyExpire: new NearlyExpire(self, {active: true, parentClass: 'o_nearly_expire_box'}),
                    infoCurrent: new Info(self, {active: true, name: 'current', label: 'Current', icon: 'fa-send', parentClass: 'o_info_box.o_current'}),
                    infoNotify: new Info(self, {active: true, name: 'notify', label: 'Notify', icon: 'fa-bell', parentClass: 'o_info_box.o_notify'}),
                    infoExpired: new Info(self, {active: true, name: 'expired', label: 'Expired', icon: 'fa-hourglass-end', parentClass: 'o_info_box.o_expired'}),
                    expirationForecast: new ExpirationForecast(self, {active: true, nYear: 2, parentClass: 'o_expiration_forecast_box'}),
                    status: new Status(self, {active: true, parentClass: 'o_status_box'}),
                    recentEventsExpired: new RecentEvents(self, {active: true, label: 'Recent Events: Expired Product', parentClass: 'o_recent_events_expired_box', event_type: 'expired'}),
                    recentEventsNotify: new RecentEvents(self, {active: true, label: 'Recent Events: Expiring Product', parentClass: 'o_recent_events_notify_box', event_type: 'notify'}),
                    calendar: new Calendar(self, {active: true, parentClass: 'o_calendar_box'}),
                }

                _.each(self.filters, function(filter){
                    filter.appendTo(self.$el.find('.' + filter.parentClass));
                });

                _.each(self.widgets, function(widget){
                    if (widget.active){
                        widget.appendTo(self.$el.find('.' + widget.parentClass));
                    }
                });
            });
        },

        _getReportFilters: function(){
            let filters = [];
            _.each(this.filters, function(filter){
                filters.push({
                    name: filter.name,
                    label: filter.label,
                    active: filter._getActiveFilters()
                });
            });
            return filters;
        },

        _onFilterChange: function(ev){
            _.each(this.widgets, function(widget){
                if (widget.active && widget.updateble){
                    widget._update();
                }
            });
        },

        _onPrintCalendar: async function(ev){
            let data = ev.data || {};
            data.filters = this._getReportFilters();

            let values = {data: JSON.stringify(data)};
            if (!this.wizardId){
                this.wizardId = await this._rpc({
                    model: 'expiring.product.calendar',
                    method: 'create',
                    args: [values]
                });
            } else {
                await this._rpc({
                    model: 'expiring.product.calendar',
                    method: 'write',
                    args: [[this.wizardId], values]
                });
            }

            return this.do_action('equip3_inventory_reports.action_print_expiring_product_calendar_report', {
                additional_context: {
                    'active_id': this.wizardId,
                    'active_ids': [this.wizardId],
                    'active_model': 'expiring.product.calendar'
                }
            });
        },

    });

    core.action_registry.add('expiring_product_calendar', ExpiringProductCalendarAction);
    return ExpiringProductCalendarAction;
});