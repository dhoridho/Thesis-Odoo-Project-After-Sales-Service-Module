odoo.define('equip3_manuf_reports.MovingPlanCostReport', function(require){
    "use strict";

    var FormRenderer = require('web.FormRenderer');
    var FormController = require('web.FormController');
    var FormView = require('web.FormView');
    var viewRegistry = require('web.view_registry');

    var core = require('web.core');
    var Qweb = core.qweb;
    var field_utils = require('web.field_utils');

    var datepicker = require('web.datepicker');

    var ReportFormController = FormController.extend({
        events: _.extend({}, FormController.prototype.events, {
            'click .o_filter_date_custom_btn': 'toggleCustomDate',
            'click .o_apply_custom_date': 'onApplyCustomDate',
            'click .o_filter_date_item': 'onSelectDate',
            'click .o_open_record': '_onOpenRecord'
        }),

        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);

            this.filters = {
                date: {
                    'selection': [
                        ['last_30_days', 'Last 30 Days'], 
                        ['this_month', 'This Month'],
                        ['last_month', 'Last Month'],
                        ['this_year', 'This Year'],
                        ['last_year', 'Last Year'],
                        ['custom', 'Custom']
                    ]
                }
            }
            this.filterDate = 'last_30_days'; // default
            this.filters.date.active = _.find(this.filters.date.selection, o => o[0] === this.filterDate);
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                self.$el.addClass('o_moving_plan_report');
            });
        },

        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.$buttons){
                this.$buttons.append(Qweb.render('MovingPlanCostReportFilter', {filters: this.filters}));
            }
        },

        loadDatePicker: function(){
            var self = this;
            this.dateFromWidget = new datepicker.DateWidget(this);
            this.dateToWidget = new datepicker.DateWidget(this);

            this.dateFromWidget.appendTo('.o_custom_date_from').then(function(){
                self.dateFromWidget.setValue(moment.utc(moment.utc().startOf('year').format('DD-MM-YYYY'), 'DD-MM-YYYY'));
            });
            this.dateToWidget.appendTo('.o_custom_date_to').then(function(){
                self.dateToWidget.setValue(moment.utc(moment.utc().endOf('year').format('DD-MM-YYYY'), 'DD-MM-YYYY'));
            });
        },

        toggleCustomDate: function(e){
            e.preventDefault();
            var $target = $(e.currentTarget);
            var $customDate = $target.next('.collapse');
            $customDate.toggleClass('show');
            if ($customDate.hasClass('show') && !this.dateFromWidget && !this.dateToWidget){
                this.loadDatePicker();
            }
            e.stopPropagation();
        },

        onSelectDate: function(e){
            e.preventDefault();
            var $target = $(e.currentTarget);
            var value = $target.data('filter-date');
            var label = $target.html();
            this.setActiveFilterDate(value, label);

            var $customDate = $('.o_filter_date_custom_collapse');
            if ($customDate.hasClass('show')){
                $customDate.removeClass('show');
            }
        },

        onApplyCustomDate: function(e){
            e.preventDefault();
            if (!this.dateFromWidget || !this.dateToWidget){
                return;
            }
            var isValid = this.dateFromWidget.isValid() && this.dateToWidget.isValid();
            if (isValid){
                this.filterDateFrom = this.dateFromWidget.getValue();
                this.filterDateTo = this.dateToWidget.getValue();
                this.setActiveFilterDate('custom', 'Custom');
            }
        },

        setActiveFilterDate: function(value, label){
            var $parentId = $('.o_filter_date_btn');
            $parentId.data('filter-date', value);
            $parentId.html(label);
            this.filterDate = value;

            var date_from, date_to;
            if (this.filterDate == 'last_30_days'){
                date_from = moment().subtract(30, 'days');
                date_to = moment();
            } else if (this.filterDate == 'this_month'){
                date_from = moment().startOf('month');
                date_to = moment().endOf('month');
            } else if (this.filterDate == 'last_month'){
                date_from = moment().subtract(1, 'months').startOf('month');
                date_to = moment().subtract(1, 'months').endOf('month');
            } else if (this.filterDate == 'this_year'){
                date_from = moment().startOf('year');
                date_to = moment().endOf('year');
            } else if (this.filterDate == 'last_year'){
                date_from = moment().subtract(1, 'years').startOf('year');
                date_to = moment().subtract(1, 'years').endOf('year');
            } else {
                date_from = this.filterDateFrom;
                date_to = this.filterDateTo;
            }

            let state = this.model.get(this.handle);
            let context = state.getContext();
            context.date_from = date_from.format('YYYY-MM-DD');
            context.date_to = date_to.format('YYYY-MM-DD');

            this.reload({context: context});
        },

        _onOpenRecord: function(ev){
            ev.preventDefault();
            var $target = $(ev.currentTarget);

            return this.do_action({
                name: $target.data('title'),
                res_model: $target.data('res_model'),
                res_id: $target.data('res_id'),
                views: [[false, 'form']],
                view_mode: ['form'],
                type: 'ir.actions.act_window',
                target: 'new'
            });
        }
    });

    var ReportFormRenderer = FormRenderer.extend({
        _renderView: function(){
            var self = this;
            return this._super.apply(this, arguments).then(function(){
                var report_data = JSON.parse(self.state.data.report_data);
                self._renderBomTable(report_data);
                self._renderBomChart(report_data);
            });
        },

        _renderBomTable: function(report_data){
            var $content = Qweb.render('MovingPlanCostReport', {
                data: report_data,
                currency_id: this.state.data.currency_id.res_id,
                formatMonetary: this._formatMonetary.bind(this)
            });
            this.$el.find('.o_bom_material').html($content);
        },

        _renderBomChart: function(report_data){
            var self = this;

            var colors = [
                '#36A2EB',
                '#FF6384',
                '#4BC0C0',
                '#FF9F40',
                '#9966FF',
                '#FFCD56',
                '#C9CBCF'
            ];
            var nColor = colors.length;

            var data = {
                labels: _.map(report_data.plans, o => [o.display_name, o.date]),
                datasets: [{
                    label: report_data.primary_uom.product,
                    data: _.map(report_data.primary_uom.cost, o => o.value),
                    backgroundColor: 'transparent',
                    borderColor: colors[0]
                }]
            };

            _.each(report_data.materials, function(material, index){
                data.datasets.push({
                    label: material.product_id.display_name,
                    data: _.map(material.cost, o => o.value),
                    backgroundColor: 'transparent',
                    borderColor: colors[(index + 1) % nColor]
                });
            });

            var options = {
                legend: {
                    display: false
                },
                scales: {
                    yAxes: [
                        {
                            ticks: {
                                callback: function(value, index, values) {
                                    return self._formatMonetary(value);
                                }
                            }
                        }
                    ],
                },
                maintainAspectRatio: false
            }

            if (this.bomChart){
                this.bomChart.destroy();
            }

            var $canvas = this.$el.find('#o_bom_material_chart');
            $canvas.attr('height', 500);

            this.bomChart = new Chart($canvas, {
                type: 'line',
                data: data,
                options: options
            });
            
            var $legend = this.$el.find('.o_bom_material_chart_legend');
            var $legendContent = $(Qweb.render('MovingPlanCostReportLegend', {
                labels: _.map(data.datasets, o => o.label),
                colors: _.map(data.datasets, o => o.borderColor)
            }));
            $legendContent.find('li.o_legend').on('click', this._onChangeLegend.bind(this));
            $legend.html($legendContent);
        },

        _onChangeLegend: function(e){
            var $target = $(e.currentTarget);
            var index = $target.data('index');

            var obj = this.bomChart.getDatasetMeta(index);

            obj.hidden = !obj.hidden;
            $target.toggleClass('o_hide');
            this.bomChart.update();
        },

        _formatMonetary: function(value){
            return field_utils.format.monetary(value, undefined, {currency_id: this.state.data.currency_id.res_id, forceString: true});
        }
    });

    var ReportFormView = FormView.extend({
        config: _.extend({}, FormView.prototype.config, {
            Renderer: ReportFormRenderer,
            Controller: ReportFormController
        }),
    });
    
    viewRegistry.add('moving_plan_cost_report', ReportFormView);

    return {
        ReportFormRenderer: ReportFormRenderer,
        ReportFormController: ReportFormController,
        ReportFormView: ReportFormView
    }
});