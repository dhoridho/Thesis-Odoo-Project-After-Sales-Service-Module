odoo.define('equip3_inventory_masterdata.ReplenishReport', function (require) {
"use strict";

    const core = require('web.core');
    const AbstractAction = require('web.AbstractAction');
    const session = require('web.session');
    const utils = require('report.utils');
    const time = require('web.time');

    const StandaloneFieldManagerMixin = require('web.StandaloneFieldManagerMixin');
    const { FieldMany2One, FieldMany2ManyTags } = require('web.relational_fields');
    
    const dom = require('web.dom');
    const GraphView = require('web.GraphView');

    const qweb = core.qweb;
    const _t = core._t;

    const ProductForecastAction = AbstractAction.extend(StandaloneFieldManagerMixin, {
        template: "ProductForecast",
        hasControlPanel: true,

        events: {
            'click .o_report_replenish': '_onClickReplenish'
        },

        custom_events:  Object.assign({}, StandaloneFieldManagerMixin.custom_events, {
            field_changed: '_onFieldChanged',
        }),

        init: function (parent, action, options) {
            this._super.apply(this, arguments);
            StandaloneFieldManagerMixin.init.call(this);
            this.context = action.context;
            this.resModel = 'product.template';
        },

        willStart: function(){
            this.filters = {
                warehouse_id: {widget: undefined, value: undefined},
                product_ids: {widget: undefined, value: []}
            }
            const warehouseIdSetup = this.model.makeRecord('report.equip3_inventory_masterdata.report_product_tmpl_forecast', [{
                name: 'warehouse_id',
                type: 'many2one',
                relation: 'stock.warehouse'
            }]).then(recordID => {
                const record = this.model.get(recordID);
                this.filters.warehouse_id.widget = new FieldMany2One(this, 'warehouse_id', record, {
                    mode: 'edit',
                    attrs: {
                        can_create: false,
                        can_write: false,
                        options: {no_open: true},
                    },
                });
                this._registerWidget(recordID, 'warehouse_id', this.filters.warehouse_id.widget);
            });

            const productIdsSetup = this.model.makeRecord('report.equip3_inventory_masterdata.report_product_tmpl_forecast', [{
                name: 'product_ids',
                type: 'many2many',
                relation: 'product.template',
                domain: [['type', '=', 'product']]
            }]).then(recordID => {
                var record = this.model.get(recordID);
                this.filters.product_ids.widget = new FieldMany2ManyTags(this, 'product_ids', record, {
                    mode: 'edit',
                    attrs: {
                        can_create: false,
                        can_write: false,
                        options: {no_open: true},
                    },
                });
                this._registerWidget(recordID, 'product_ids', this.filters.product_ids.widget);
            });

            return Promise.all([warehouseIdSetup, productIdsSetup, this._super()]);
        },

        start: function(){
            var self = this;
            this.iframe = this.$('iframe')[0];
            this.$content = this.$('.o_product_forecast_content');
            return this._super.apply(this, arguments).then(() => {
                self.$filters = $(qweb.render('ProductForecastFilters'));
                self.$filters.appendTo(self.$el.find('.o_control_panel'));
                _.each(self.filters, (filter, name) => {
                    filter.widget.appendTo(self.$filters.find('.o_filter_' + name));
                });
                self._loadContent();
            });
        },

        _getFilter: function(name){
            return _.find(this.filters, (filter) => filter.name === name);
        },

        _getReportContext: function(){
            let context = Object.assign({}, this.context);
            Object.assign(context, {
                active_id: this.filters.product_ids.value[0],
                active_ids: this.filters.product_ids.value,
                active_model: this.resModel,
                warehouse: this.filters.warehouse_id.value
            });
            return context;
        },

        _getReportName: function(){
            let isTemplate = this.resModel === 'product.template';
            return `report_product_${isTemplate ? 'tmpl_' : ''}forecast`;
        },

        _getReportUrl: function(){
            const reportName = this._getReportName();
            const context = this._getReportContext();
            return `/report/html/equip3_inventory_masterdata.${reportName}/${this.filters.product_ids.value.join(',')}?context=${JSON.stringify(context)}`;
        },

        _createGraphView: async function () {
            let viewController;
            const appendGraph = () => {
                promController.then(() => {
                    this.iframe.removeEventListener('load', appendCharts);
                    const $reportGraphDiv = $(this.iframe).contents().find('.o_report_graph');
                    dom.append(this.$el, viewController.$el, {
                        in_DOM: true,
                        callbacks: [{widget: viewController}],
                    });
                    const renderer = viewController.renderer;
                    $('.o_control_panel:last').remove();
                    const $graphPanel = $('.o_graph_controller');
                    $graphPanel.appendTo($reportGraphDiv);

                    if (!renderer.state.dataPoints.length) {
                        const graphHelper = renderer.$('.o_view_nocontent');
                        const newMessage = qweb.render('View.NoContentHelper', {
                            description: _t("Try to add some incoming or outgoing transfers."),
                        });
                        graphHelper.replaceWith(newMessage);
                    } else {
                        this.chart = renderer.chart;
                        setTimeout(() => {
                            this.chart.canvas.height = 300;
                            this.chart.canvas.style.height = "300px";
                            this.chart.resize();
                        }, 1);
                    }
                });
            };

            const appendBar = () => {
                promReport.then((results) => {
                    const $reportBarDiv = $(this.iframe).contents().find('.o_report_bar_forecast');
                    let datesMoveIn = [];
                    let datesMoveOut = [];
                    _.each(results.docs.lines, (line) => {
                        if (line.move_in){
                            datesMoveIn.push(line.receipt_date);
                        }
                        if (line.move_out){
                            datesMoveOut.push(line.delivery_date);
                        }
                    });
                    let dates = _.unique(_.map(datesMoveIn.concat(datesMoveOut), (date) => moment(date, time.getLangDatetimeFormat()).format('DD MMM YYYY')));
                    
                    dates.sort(function (left, right) {
                        return moment.utc(left).diff(moment.utc(right))
                    });

                    let qtyIn = [];
                    let qtyOut = [];
                    _.each(dates, (date) => {
                        let moveIn = _.filter(results.docs.lines, (line) => moment.utc(line.receipt_date).format('DD MMM YYYY') === date);
                        let moveOut = _.filter(results.docs.lines, (line) => moment.utc(line.delivery_date).format('DD MMM YYYY') === date);
                        qtyIn.push(_.map(moveIn, (move) => move.move_in_qty).reduce((a, b) => a + b, 0));
                        qtyOut.push(_.map(moveOut, (move) => move.move_out_qty).reduce((a, b) => a + b, 0));
                    });

                    var canvas = document.createElement('canvas');
                    canvas.height = 300;
                    $reportBarDiv.html($(canvas));

                    setTimeout(() => {
                        var ctx = canvas.getContext('2d');
                        this.barChart = new Chart(ctx, {
                            type: 'bar',
                            data: {
                                labels: dates,
                                datasets: [{
                                    label: _t('Incoming Quantity'),
                                    data: qtyIn,
                                    backgroundColor: '#FE7F0E',
                                    borderWidth: 0,
                                    barPercentage: 1.0
                                }, {
                                    label: _t('Outgoing Quantity'),
                                    data: qtyOut,
                                    backgroundColor: '#1F78B4',
                                    borderWidth: 0,
                                    barPercentage: 1.0
                                }]
                            },
                            options: {
                                responsive: true,
                                maintainAspectRatio: false,
                                scales: {     
                                    yAxes: [{
                                        ticks: {
                                            min: 0,
                                            stepSize: 10,
                                        }
                                    }],
                                },
                                title: {
                                    display: true,
                                    text: _t('Forecast Incoming vs Forecast Outgoing'),
                                    fontSize: 20
                                }
                            }
                        })
                    }, 1);
                });
            }

            const appendCharts = () => {
                appendGraph();
                appendBar();
            }

            this.iframe.addEventListener('load', appendCharts);

            const model = 'report.stock.quantity';
            const promController = this._rpc({
                model: model,
                method: 'fields_view_get',
                kwargs: {
                    view_type: 'graph',
                }
            }).then(viewInfo => {
                const params = {
                    modelName: model,
                    domain: this._getReportDomain(),
                    hasActionMenus: false,
                };
                const graphView = new GraphView(viewInfo, params);
                return graphView.getController(this);
            }).then(res => {
                viewController = res;
                if (location.href.indexOf('active_model') === -1) {
                    const url = window.location.href + `&active_model=${this.resModel}`;
                    window.history.pushState({}, "", url);
                }
                const fragment = document.createDocumentFragment();
                return viewController.appendTo(fragment);
            });

            const reportName = this._getReportName();
            const context = this._getReportContext();
            const promReport = this._rpc({
                model: `report.equip3_inventory_masterdata.${reportName}`,
                method: 'get_report_values_public',
                args: [this.filters.product_ids.value],
                kwargs: {data: {
                    context: context,
                    report_type: 'html'
                }}
            });
        },

        _getReportDomain: function () {
            const domain = [
                ['state', '=', 'forecast'],
                ['warehouse_id', '=', this.filters.warehouse_id.value],
            ];
            if (this.resModel === 'product.template') {
                domain.push(['product_tmpl_id', 'in', this.filters.product_ids.value]);
            } else if (this.resModel === 'product.product') {
                domain.push(['product_id', 'in', this.filters.product_ids.value]);
            }
            return domain;
        },

        _renderIframe: function(){
            var web_base_url = session['web.base.url'];
            var trusted_host = utils.get_host_from_url(web_base_url);
            var trusted_protocol = utils.get_protocol_from_url(web_base_url);
            this.trusted_origin = utils.build_origin(trusted_protocol, trusted_host);
            this.iframe.src = this._getReportUrl();
        },

        _loadContent: function(){
            if (this.filters.warehouse_id.value && this.filters.product_ids.value.length){
                let $noContent = this.$el.find('.o_view_nocontent');
                if ($noContent.length){
                    $noContent.remove();
                }
                $(this.iframe).removeClass('d-none');
                this._createGraphView();
                this._renderIframe();
                this.$el.find('.o_report_replenish').removeClass('d-none');
            } else {
                let $noContent = qweb.render('ProductForecastNoContent');
                $(this.iframe).addClass('d-none');
                this.$content.append($noContent);
                this.$el.find('.o_report_replenish').addClass('d-none');
            }
        },

        _onFieldChanged: function(ev){
            var self = this;
            StandaloneFieldManagerMixin._onFieldChanged.apply(this, arguments);
            _.each(ev.data.changes, function(value, name){
                let filter = self.filters[name];
                if (filter.widget.formatType === 'many2one'){
                    filter.value = value.id;
                } else if (filter.widget.formatType === 'many2many'){
                    if (value.operation === 'ADD_M2M'){
                        filter.value.push(value.ids.id);
                    } else if (value.operation === 'FORGET'){
                        _.each(value.ids, function(id){
                            var res_id = _.find(filter.widget.value.data, (d) => d.id === id).res_id;
                            var index = filter.value.indexOf(res_id);
                            filter.value.splice(index, 1);
                        });
                    }
                }
            });
            this._loadContent();
        },

        _onClickReplenish: function () {
            const context = this._getReportContext();
            context.default_warehouse_id = this.filters.warehouse_id.value;

            var action;
            if (this.filters.product_ids.value.length === 1){
                if (this.resModel === 'product.product') {
                    context.default_product_id = this.filters.product_ids.value[0];
                } else if (this.resModel === 'product.template') {
                    context.default_product_tmpl_id = this.filters.product_ids.value[0];
                }
                
                action = {
                    res_model: 'product.replenish',
                    name: _t('Product Replenish'),
                    type: 'ir.actions.act_window',
                    views: [[false, 'form']],
                    target: 'new',
                    context: context,
                };
            } else {
                if (this.resModel === 'product.product') {
                    context.domain_product_ids = this.filters.product_ids.value;
                } else if (this.resModel === 'product.template') {
                    context.domain_product_tmpl_ids = this.filters.product_ids.value;
                }

                action = {
                    res_model: 'pick.product.replenish',
                    name: _t('Pick Product To Replenish'),
                    type: 'ir.actions.act_window',
                    views: [[false, 'form']],
                    target: 'new',
                    context: context,
                };
            }

            const on_close = function (res) {
                if (res && res.special) {
                    return;
                }
                return this._loadContent();
            };

            return this.do_action(action, {
                on_close: on_close.bind(this),
            });
        },

        on_attach_callback: function () {
            this._super.apply(this, arguments);
            this.$content.css('height', 'calc(100% - ' + this.$el.find('.o_control_panel').outerHeight() + 'px)');
        },
    });

    core.action_registry.add('product_forecast', ProductForecastAction);

});