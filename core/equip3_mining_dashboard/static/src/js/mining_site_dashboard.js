odoo.define('equip3_mining_dashboard.MiningSiteDashboard', function(require){
    "use strict"

    const AbstractAction = require('web.AbstractAction');
    const Widget = require('web.Widget');
    const core = require('web.core');
    const { OpenWeather } = require('equip3_open_weather.openWeather');
    const { dateTimeMonthYearWidget } = require('equip3_date_year.month_year');
    const field_utils = require('web.field_utils');
    
    const _t = core._t;
    const formatFloatTime = field_utils.format.float_time;

    function toMoment(date){
        return moment.utc(date, 'YYYY-MM-DD');
    }

    const MiningWidget = Widget.extend({

        init: function(parent, params){
            this.parent = parent;
            this.parentClass = params.parentClass;
            this.siteId = parent.resId;
            this._super.apply(this, arguments);
        },

        willStart: function(){
            var self = this;
            var dataProm = this._getData().then(function(result){
                self._buildData(result);
            });
            return Promise.all([this._super.apply(this, arguments), dataProm]);
        },

        start: function(){
            this.$el = $(this.el);
            return this._super.apply(this, arguments);
        },

        _getData: function(){
            return Promise.resolve({});
        },

        _buildData: function(result){
            this.data = result;
        },

        _update: function(){
            var self = this;
            return this._getData().then((result) => {
                self._buildData(result);
            });
        },
    });

    const TotalProduction = MiningWidget.extend({
        template: 'DashboardTotalProduction',
        
        events: {
            'click .o_search': '_onClickOperationType',
            'click .o_operation_type': '_onSelectOperationType',
            'input .o_search_input': '_onInputOperationType',
            'click .o_this_month': '_onClickThisMonth',
            'click .o_last_month': '_onClickLastMonth',
        },

        willStart: function(){
            var _super = this._super.bind(this);
            var self = this;
            return this._rpc({
                model: 'ir.model.fields.selection',
                method: 'search_read',
                domain: [
                    ['field_id.name', '=', 'operation_type_id'], 
                    ['field_id.model', '=', 'mining.operations.two']
                ],
                fields: ['value', 'name']
            }).then((operationTypes) => {
                self.operationTypes = operationTypes;
                self.operationType = operationTypes[0];
                return _super();
            });
        },

        _getData: function(){
            let startOfLastMonth = moment.utc().subtract(1, 'months').startOf('month');
            let endOfThisMonth = moment.utc().endOf('month');
            return this._rpc({
                model: 'mining.production.record',
                method: 'search_read',
                domain: [
                    ['mining_site_id', '=', this.siteId],
                    ['selected_operation_type', '=', this.operationType.value],
                    ['prod_rec_date', '>=', startOfLastMonth],
                    ['prod_rec_date', '<=', endOfThisMonth]
                ],
                fields: ['prod_rec_date', 'nett_total']
            });
        },

        _buildData: function(result){
            let thisMonth = moment.utc().month();
            let thisMonthRecords = _.filter(result, (record) => toMoment(record.prod_rec_date).month() === thisMonth);
            let lastMonthRecords = _.filter(result, (record) => toMoment(record.prod_rec_date).month() !== thisMonth);

            let totalThisMonth = _.map(thisMonthRecords, (record) => record.nett_total).reduce((a, b) => a + b, 0);
            let totalLastMonth = _.map(lastMonthRecords, (record) => record.nett_total).reduce((a, b) => a + b, 0);
            this.data = {
                totalThisMonth: totalThisMonth,
                totalLastMonth: totalLastMonth,
                percentage: totalLastMonth > 0 ? Math.round((Math.abs(totalThisMonth - totalLastMonth) / totalLastMonth) * 100, 2) : 0.00,
                thisMonthIds: _.map(thisMonthRecords, (record) => record.id),
                lastMonthIds: _.map(lastMonthRecords, (record) => record.id),
                status: totalThisMonth > totalLastMonth ? 'up' : 'down',
                uomName: 'Ton' // need to set default
            }
        },

        _update: function(){
            var self = this;
            return this._super.apply(this, arguments).then(() => {
                self.renderElement();
            });
        },

        _toggleDropdown: function(){
            this.$el.find('.o_search_dropdown').toggleClass('d-none');
        },

        _onClickOperationType: function(ev){
            ev.stopPropagation();
            this._toggleDropdown();
        },

        _onSelectOperationType: function(ev){
            ev.stopPropagation();
            let value = $(ev.target).data('value');
            let operationType = _.find(this.operationTypes, (ot) => ot.value === value);
            this.operationType = {value: value, name: operationType.name};

            let $input = this.$el.find('.o_search_input');
            $input.data('value', operationType.value);
            $input.val(operationType.name);

            this._toggleDropdown();
            this._update();
        },

        _onInputOperationType: function(ev){
            var self = this;
            let query = $(ev.target).val().toLowerCase();
            if (query === ''){
                _.each(this.operationTypes, function(operationType){
                    let $el = self.$el.find('li[data-value="' + operationType.value + '"]');
                    $el.removeClass('d-none');
                });
            } else {
                _.each(this.operationTypes, function(operationType){
                    let $el = self.$el.find('li[data-value="' + operationType.value + '"]');
                    if (operationType.name.toLowerCase().includes(query)){
                        $el.removeClass('d-none');
                    } else {
                        $el.addClass('d-none');
                    }
                });
            }
        },

        _onClickThisMonth: function(ev){
            ev.stopPropagation();
            this._openRecords(this.data.thisMonthIds);
        },

        _onClickLastMonth: function(ev){
            ev.stopPropagation();
            this._openRecords(this.data.lastMonthIds);
        },

        _openRecords: function(ids){
            this.do_action({
                res_model: 'mining.production.record',
                name: _t(this.operationType.name + ' Production Record'),
                views: [[false, 'list'], [false, 'form']],
                domain: [['id', 'in', ids]],
                type: 'ir.actions.act_window'
            });
        }

    });

    const TotalVehicles = MiningWidget.extend({
        template: 'DashboardTotalVehicle',

        events: {
            'click .o_vehicle_count': '_onClickVehicle',
            'click .o_vehicle_maintenance_count': '_onClicMaintenancekVehicle',
        },

        willStart: function(){
            var _super = this._super.bind(this);
            var self = this;
            return this._rpc({
                model: 'mining.project.control',
                method: 'search_read',
                domain: [['mining_site_id', '=', this.siteId], ['facilities_area_id', '!=', false]],
                fields: ['facilities_area_id']
            }).then(function(pits){
                self.areaIds = _.unique(_.map(pits, (pit) => pit.facilities_area_id[0]));
                return _super(); 
            });
        },

        _getData: function(){
            return this._rpc({
                model: 'maintenance.equipment',
                method: 'search_read',
                domain: [
                    ['vehicle_checkbox', '=', true],
                    ['fac_area', 'in', this.areaIds]
                ],
                fields: ['state']
            });
        },

        _buildData: function(vehicles){
            this.data = {
                vehicleIds: _.map(vehicles, (vehicle) => vehicle.id),
                maintenanceVehicleIds: _.map(_.filter(vehicles, (v) => v.state === 'maintenance'), (m) => m.id),
            };
            Object.assign(this.data, {
                totalVehicle: this.data.vehicleIds.length,
                totalVehicleMaintenance: this.data.maintenanceVehicleIds.length
            });
        },

        _onClickVehicle: function(ev){
            ev.stopPropagation();
            this._openRecords(this.data.vehicleIds);
        },

        _onClicMaintenancekVehicle: function(ev){
            ev.stopPropagation();
            this._openRecords(this.data.maintenanceVehicleIds);
        },

        _openRecords: function(ids){
            this.do_action({
                res_model: 'maintenance.equipment',
                name: _t('Vehicle'),
                views: [[false, 'list'], [false, 'form']],
                domain: [['id', 'in', ids]],
                type: 'ir.actions.act_window'
            });
        }
    });

    const TotalFuel = MiningWidget.extend({
        template: 'DashboardTotalFuel',

        _getData: function(){
            return Promise.resolve({
                total_fuel: 2000,
                uom_name: 'L'
            });
        },

        _buildData: function(result){
            this.data = {
                totalFuel: result.total_fuel,
                uomName: result.uom_name
            };
        }
    });

    const TotalMaintenance = MiningWidget.extend({
        template: 'DashboardTotalMaintenance',

        events: {
            'click .o_records': '_onClickRecords'
        },

        willStart: function(){
            var _super = this._super.bind(this);
            var self = this;
            return this._rpc({
                model: 'mining.project.control',
                method: 'search_read',
                domain: [['mining_site_id', '=', this.siteId], ['facilities_area_id', '!=', false]],
                fields: ['facilities_area_id']
            }).then(function(pits){
                self.areaIds = _.unique(_.map(pits, (pit) => pit.facilities_area_id[0]));
                return _super(); 
            });
        },

        _getData: function(){
            var self = this;

            return this._rpc({
                model: 'maintenance.equipment',
                method: 'search_read',
                domain: [['fac_area', 'in', this.areaIds]],
                fields: ['display_name', 'vehicle_checkbox']
            }).then((assets) => {
                self.assets = assets;
                return self._rpc({
                    model: 'plan.task.check.list',
                    method: 'search_read',
                    domain: [['equipment_id', 'in', _.unique(_.map(assets, (asset) => asset.id))]],
                    fields: ['maintenance_wo_id', 'maintenance_ro_id']
                }).then((tasks) => {
                    self.tasks = tasks;
                    var workorderProm = self._rpc({
                        model: 'maintenance.work.order',
                        method: 'search_read',
                        domain: [['id', 'in', _.unique(_.map(tasks, (task) => task.maintenance_wo_id[0]))]],
                        fields: ['time_in_progress']
                    });
                    var repairProm = self._rpc({
                        model: 'maintenance.repair.order',
                        method: 'search_read',
                        domain: [['id', 'in', _.unique(_.map(tasks, (task) => task.maintenance_ro_id[0]))]],
                        fields: ['time_in_progress']
                    });
                    return Promise.all([workorderProm, repairProm]);
                });
            });
        },

        _buildData: function(results){
            var self = this;
            let workOrders = results[0];
            let repairOrders = results[1];

            this.data = [];
            _.each(self.assets, (asset, sequence) => {
                let tasks = _.filter(self.tasks, (task) => task.equipment_id === asset.id);
                let taskWos = _.filter(workOrders, (wo) => _.map(tasks, (t) => t.maintenance_wo_id[0]).includes(wo.id));
                let taskRos = _.filter(repairOrders, (ro) => _.map(tasks, (t) => t.maintenance_ro_id[0]).includes(ro.id));
                let duration = _.map(taskWos, (wo) => wo.time_in_progress).reduce((a, b) => a + b, 0) + _.map(taskRos, (ro) => ro.time_in_progress).reduce((a, b) => a + b, 0);
                self.data.push({
                    sequence: sequence + 1,
                    ids: _.unique(_.map(tasks, (t) => t.id)),
                    name: asset.display_name,
                    type: asset.vehicle_checkbox ? 'Vehicle' : 'Asset',
                    duration: formatFloatTime(duration)
                });
            });
        },

        _onClickRecords: function(ev){
            ev.stopPropagation();
            let ids = $(ev.currentTarget).data('record-ids');
            if (typeof(ids) === 'string'){
                if (ids === ''){
                    ids = [];
                } else {
                    ids = _.map(ids.split(','), function(id){return parseInt(id);});
                }
            } else {
                ids = [ids];
            }
            this._openRecords(ids);
        },

        _openRecords: function(ids){
            this.do_action({
                res_model: 'plan.task.check.list',
                name: _t('Maintenance Work/Repair Order Lines'),
                views: [[false, 'list'], [false, 'form']],
                domain: [['id', 'in', ids]],
                type: 'ir.actions.act_window'
            });
        }
    });

    const Vehicle = MiningWidget.extend({
        template: 'DashboardVehicle',

        events: {
            'click .o_record': '_onClickRecord'
        },

        init: function(parent, params){
            this._super.apply(this, arguments);
            this.label = params.label;
            this.state = params.state;
        },

        willStart: function(){
            var _super = this._super.bind(this);
            var self = this;
            return this._rpc({
                model: 'mining.project.control',
                method: 'search_read',
                domain: [['mining_site_id', '=', this.siteId], ['facilities_area_id', '!=', false]],
                fields: ['facilities_area_id']
            }).then(function(pits){
                self.areaIds = _.unique(_.map(pits, (pit) => pit.facilities_area_id[0]));
                return _super(); 
            });
        },

        _getData: function(){
            return this._rpc({
                model: 'maintenance.equipment',
                method: 'search_read',
                domain: [['fac_area', 'in', this.areaIds], ['state', '=', this.state]],
                fields: ['display_name']
            });
        },

        _onClickRecord: function(ev){
            ev.stopPropagation();
            let $target = $(ev.currentTarget);
            this.do_action({
                res_model: 'maintenance.equipment',
                res_id: $target.data('id'),
                name: _t($target.val()),
                views: [[false, 'form']],
                type: 'ir.actions.act_window'
            });
        }
    });

    const MiningOpenWeather = OpenWeather.extend({

        init: function(parent, params){
            this._super.apply(this, arguments);
            this.parentClass = params.parentClass;
            this.siteId = parent.resId;
        },

        _rpcData: function(){
            return {
                model: 'mining.site.control',
                method: 'get_open_weather_data',
                args: [[this.siteId]]
            }
        },

        _loadData: function(result){
            result.widget = 11;
            this._super.apply(this, arguments);
        }
    });

    const BoxChart = MiningWidget.extend({
        template: 'DashboardBoxChart',

        jsLibs: [
            '/web/static/lib/Chart/Chart.js'
        ],

        init: function(parent, params){
            this._super.apply(this, arguments);
            this.title = params.title;
            this.type = params.type;
            this.canvasHeight = params.canvasHeight;
            this.additionalClass = params.additionalClass;
            this.operationType = params.operationType;
            this.canvasId = params.canvasId + '_chart';
        },

        start: function(){
            var self = this;
            return this._super.apply(this, arguments).then(() => {
                self._renderChart();
            });
        },

        _renderChart: function(){
            if (this.chart){
                this.chart.destroy();
            }
            let chartData = {
                type: this.type,
                data: this._chartData(),
                options: this._chartOptions()
            };
            
            let canvas = document.getElementById(this.canvasId);
            let ctx = canvas.getContext('2d');
            this.chart = new Chart(ctx, chartData);
        },

        _chartData: function(){
            return {};
        },

        _chartOptions: function(){
            return {};
        },

        _update: function(){
            var self = this;
            return this._super.apply(this, arguments).then(() => {
                self._renderChart();
            });
        }
    });

    const TotalProductionGraph = BoxChart.extend({

        init: function(parent, params){
            this._super.apply(this, arguments);
            this.type = 'bar';
        },

        _getData: function(){
            return this._rpc({
                model: 'mining.production.record',
                method: 'search_read',
                domain: [
                    ['mining_site_id', '=', this.siteId], 
                    ['selected_operation_type', '=', this.operationType.value]
                ],
                fields: ['nett_total', 'equipment_id']
            });
        },

        _buildData: function(records){
            let operationEqs = _.unique(_.map(records, (r) => r.equipment_id[0]));
            let equipments = [];
            _.each(operationEqs, (eqId) => {
                equipments.push({
                    id: eqId,
                    name: _.find(records, (r) => r.equipment_id[0] === eqId).equipment_id[1],
                    total: _.map(_.filter(records, (r) => r.equipment_id[0] === eqId), (o) => o.nett_total).reduce((a, b) => a + b, 0)
                });
            });
            this.data = {
                equipments: equipments,
                total: _.map(equipments, (eq) => eq.total).reduce((a, b) => a + b, 0)
            };
        },

        _chartData: function(){
            return {
                labels: _.map(this.data.equipments, (eq) => eq.name),
                datasets: [{
                    label: _t('Total Production ' + this.data.total + ' t'),
                    data: _.map(this.data.equipments, (eq) => eq.total),
                    backgroundColor: '#14B8A6',
                    borderWidth: 0
                }]
            };
        },

        _chartOptions: function(){
            return {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    yAxes: [{
                        ticks: {
                            beginAtZero: true
                        },
                        gridLines: {
                            display: false
                        }
                    }],
                },
                legend: {
                    labels: {
                        boxWidth: 0
                    }
                }
            }
        },
    });

    const StrippingRatio = BoxChart.extend({

        init: function(parent, params){
            this._super.apply(this, arguments);
            this.type = 'pie';
        },

        _getData: function(){
            return this._rpc({
                model: 'mining.production.record',
                method: 'search_read',
                domain: [
                    ['mining_site_id', '=', this.siteId], 
                    ['selected_operation_type', 'in', ['extraction', 'waste_removal']]
                ],
                fields: ['selected_operation_type', 'nett_total']
            });
        },

        _buildData: function(result){
            let extraction = _.filter(result, (record) => record.selected_operation_type === 'extraction');
            let wasteRemoval = _.filter(result, (record) => record.selected_operation_type === 'waste_removal');
            this.data = [
                {type: 'extraction', label: 'Extraction', total: _.map(extraction, (o) => o.nett_total).reduce((a, b) => a + b, 0)},
                {type: 'waste_removal', label: 'Waste Removal', total: _.map(wasteRemoval, (o) => o.nett_total).reduce((a, b) => a + b, 0)},
            ];
        },

        _chartData: function(){
            return {
                labels: _.map(this.data, (record) => record.label),
                datasets: [{
                    label: _t('Stripping Ratio'),
                    data: _.map(this.data, (record) => record.total),
                    backgroundColor: ['#6366F1', '#A55104'],
                    borderWidth: 0
                }]
            }
        },

        _chartOptions: function(){
            return {
                responsive: true,
                maintainAspectRatio: false,
                title: {
                    display: false,
                }
            }
        }
    });

    const ProductionPerPit = BoxChart.extend({

        jsLibs: _.union(BoxChart.prototype.jsLibs, [
            '/equip3_mining_dashboard/static/src/lib/treemap/treemap@0.2.3.js'
        ]),

        init: function(parent, params){
            this._super.apply(this, arguments);
            this.type = 'treemap';
        },

        willStart: function(){
            var _super = this._super.bind(this);
            var self = this;
            return this._rpc({
                model: 'mining.project.control',
                method: 'search_read',
                domain: [['mining_site_id', '=', this.siteId]],
                fields: ['display_name']
            }).then((pits) => {
                self.pits = pits;
                return _super();
            });
        },

        _getData: function(){
            return this._rpc({
                model: 'mining.production.record',
                method: 'search_read',
                domain: [
                    ['mining_pit_id', 'in', _.map(this.pits, (pit) => pit.id)], 
                    ['selected_operation_type', '=', this.operationType.value]
                ],
                fields: ['mining_pit_id', 'nett_total']
            });
        },

        _buildData: function(result){
            var self = this;
            this.data = [];
            _.each(this.pits, (pit) => {
                let pitRecords = _.filter(result, (o) => o.mining_pit_id[0] === pit.id);
                self.data.push({
                    pit_id: pit.id,
                    pit_name: pit.display_name,
                    total: _.map(pitRecords, (o) => o.nett_total).reduce((a, b) => a + b, 0)
                });
            });
        },

        _chartData: function(){
            let dataLength = this.data.length;
            return {
                labels: _.map(this.data, (record) => record.pit_name),
                datasets: [
                    {
                        tree: this.data,
                        key: 'total',
                        groups: ['pit_name', 'total'],
                        backgroundColor: '#0097AB',
                        borderColor: function(ctx){
                            if (ctx.dataIndex >= dataLength){
                                return '#0097AB';
                            }
                            return 'white';
                        },
                        fontColor: 'white',
                        spacing: 0.5,
                        borderWidth: 1.5,
                    }
                ]
            }
        },

        _chartOptions: function(){
            let dataLength = this.data.length;
            return {
                responsive: true,
                maintainAspectRatio: false,
                title: {
                    display: false
                },
                legend: {
                    display: false
                },
                tooltips: {
                    callbacks: {
                      title: function(item, data) {
                        return _t('Total');
                      },
                      label: function(item, data) {
                        if (item.index >= dataLength){
                            return '';
                        }
                        var dataset = data.datasets[item.datasetIndex];
                        var dataItem = dataset.data[item.index];
                        var obj = dataItem._data;
                        var label = obj.pit_name;
                        return label + ': ' + dataItem.v;
                      }
                    } 
                }
            }
        },
    });

    const ProductionPerDay = BoxChart.extend({

        init: function(parent, params){
            this._super.apply(this, arguments);
            this.type = 'bar';
            this.dateFrom = moment.utc().startOf('month');
            this.dateTo = moment.utc().endOf('month');
        },

        start: function(){
            this.month = new dateTimeMonthYearWidget(this);
            this.month.on('datetime_changed', this, this._onChangeMonth.bind(this));
            var self = this;
            return this._super.apply(this, arguments).then(() => {
                let $title = this.$el.find('.o_box_chart_title');
                $title.html('');
                this.month.appendTo($title).then(() => {
                    self.month.setValue(self.dateFrom);
                });
            });
        },

        _getData: function(){
            let dailyProm = this._rpc({
                model: 'mining.planning.production',
                method: 'search_read',
                domain: [
                    ['mining_planning_id.mining_site_id', '=', this.siteId],
                    ['mining_planning_id.mining_operation_id.operation_type_id', '=', this.operationType.value],
                    ['production_date', '>=', this.dateFrom],
                    ['production_date', '<=', this.dateTo]
                ],
                fields: ['production_date', 'adjusted_target']
            });
            let recordProm = this._rpc({
                model: 'mining.production.record',
                method: 'search_read',
                domain: [
                    ['mining_site_id', '=', this.siteId],
                    ['selected_operation_type', '=', this.operationType.value],
                    ['prod_rec_date', '>=', this.dateFrom],
                    ['prod_rec_date', '<=', this.dateTo]
                ],
                fields: ['prod_rec_date', 'nett_total']
            });
            return Promise.all([dailyProm, recordProm]);
        },

        _buildData: function(results){
            var self = this;
            let dailyRecords = results[0];
            let productionRecords = results[1];

            let date = this.dateFrom.clone();
            this.data = [];
            while (date < this.dateTo){
                let dailyPlan = _.filter(dailyRecords, (o) => toMoment(o.production_date).date() === date.date());
                let dailyProduction = _.filter(productionRecords, (o) => toMoment(o.prod_rec_date).date() === date.date());
                self.data.push({
                    date: date.clone(),
                    production: _.map(dailyProduction, (o) => o.nett_total).reduce((a, b) => a + b, 0),
                    daily_target: _.map(dailyPlan, (o) => o.adjusted_target).reduce((a, b) => a + b, 0),
                })
                date.add(1, 'days');
            }
        },

        _chartData: function(){
            return {
                labels: _.map(this.data, (record) => record.date.format('DD')),
                datasets: [{
                    type: 'line',
                    label: _t('Daily Target'),
                    fill: false,
                    data: _.map(this.data, (record) => record.daily_target),
                    borderColor: '#9395F5',
                    tension: 0.1
                }, {
                    label: _t('Daily Target Achieved'),
                    data: _.map(this.data, (record) => record.production >= record.daily_target ? record.production : 0),
                    backgroundColor: '#14B8A6',
                    borderWidth: 0,
                }, {
                    label: _t('Daily Target Not Achieved'),
                    data: _.map(this.data, (record) => record.production < record.daily_target ? record.production : 0),
                    backgroundColor: '#F36868',
                    borderWidth: 0,
                }]
            };
        },

        _chartOptions: function(){
            return {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    xAxes: [{
                        stacked: true,
                    }],
                    yAxes: [{
                        ticks: {
                            beginAtZero: true
                        },
                        gridLines: {
                            display: false
                        }
                    }]
                },
            }
        },

        _onChangeMonth: function(ev){
            let value = this.month.getValue();
            if (value){
                this.dateFrom = value.clone().startOf('month');
                this.dateTo = value.clone().endOf('month');
                this._update();
            }
        }
    });

    const OperationType = MiningWidget.extend({
        template: 'DashboardOperationType',

        init: function(parent, params){
            this._super.apply(this, arguments);
            this.resId = parent.resId;
        },

        events: {
            'shown.bs.tab a[data-toggle="tab"]': '_onChangeTab'
        },

        _getData: function(){
            return this._rpc({
                model: 'ir.model.fields.selection',
                method: 'search_read',
                domain: [
                    ['field_id.name', '=', 'operation_type_id'], 
                    ['field_id.model', '=', 'mining.operations.two']
                ],
                fields: ['value', 'name']
            });
        },

        _buildData: function(result){
            this._super.apply(this, arguments);
            this.$el = $(this.el);
            _.each(this.data, (ot, index) => {
                ot.active = index === 0 ? true : false;
            });
        },

        start: function(){
            var self = this;
            let operationType = this._getOperationType();
            this.widgets = {
                totalProductionGraph: new TotalProductionGraph(this, {operationType: operationType, parentClass: 'o_total_production_graph_box', title: 'Total Production', canvasId: 'total_production_graph', canvasHeight: 200}),
                strippingRatio: new StrippingRatio(this, {operationType: operationType, parentClass: 'o_stripping_ratio_box', title: 'Stripping Ratio', canvasId: 'stripping_ratio', canvasHeight: 200}),
                productionPerPit: new ProductionPerPit(this, {operationType: operationType, parentClass: 'o_production_per_pit_box', title: 'Production Per Pit', canvasId: 'production_per_pit', canvasHeight: 200}),
                productionPerDay: new ProductionPerDay(this, {operationType: operationType, parentClass: 'o_production_per_day_box', title: 'Production Per Day', canvasId: 'production_per_day', canvasHeight: 200})
            };

            let proms = [];
            _.each(this.widgets, function(widget){
                proms.push(widget.appendTo(self.$el.find('.' + widget.parentClass)));
            });
            return Promise.all([this._super.apply(this, arguments), proms]);
        },

        _update: function(){
            let operationType = this._getOperationType();
            _.each(this.widgets, (widget) => {
                widget.operationType = operationType;
                widget._update();
            });
        },

        _getOperationType: function(){
            return _.find(this.data, (ot) => ot.active);
        },

        _onChangeTab: function(ev){
            ev.preventDefault();
            let $activeTab = $(ev.target);
            let activeType = _.find(this.data, (ot) => ot.value === $activeTab.data('value'));

            let $previousTab = $(ev.relatedTarget);
            let previousType = _.find(this.data, (ot) => ot.value === $previousTab.data('value'));

            activeType.active = true;
            previousType.active = false;
            this._update();
        }
    });

    const MiningSiteDashboardAction = AbstractAction.extend({
        template: 'MiningSiteDashboard',
        hasControlPanel: true,

        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.resId = action.res_id;
            if (!this.resId){
                let parent = this.getParent();
                if (parent){
                    this.do_action(parent.actions[[Object.keys(parent.actions)[0]]].xml_id);
                }
            }
        },

        willStart: function () {
            var self = this;
            var operationProm = this._rpc({
                model: 'mining.site.control',
                method: 'search_read',
                domain: [['id', '=', this.resId]]
            }).then(function(result){
                self.siteData = result && result.length ? result[0] : {};
                self.widgets = {
                    totalProduction: new TotalProduction(self, {parentClass: 'o_total_production_box'}),
                    totalVehicles: new TotalVehicles(self, {parentClass: 'o_total_vehicle_box'}),
                    totalFuel: new TotalFuel(self, {parentClass: 'o_total_fuel_box'}),
                    totalMaintenance: new TotalMaintenance(self, {parentClass: 'o_total_maintenance_box'}),
                    maintenance: new Vehicle(self, {state: 'maintenance', parentClass: 'o_maintenance_box', label: 'Maintenance'}),
                    operative: new Vehicle(self, {state: 'operative', parentClass: 'o_operative_box', label: 'Operative'}),
                    breakdown: new Vehicle(self, {state: 'breakdown', parentClass: 'o_breakdown_box', label: 'Breakdown'}),
                    openWeather: new MiningOpenWeather(self, {parentClass: 'o_weather', containerId: 'openWeatherSiteWidget'}),
                    operationType: new OperationType(self, {parentClass: 'o_operation_type_box'}),
                }
            });
            
            return Promise.all([this._super.apply(this, arguments), operationProm]);
        },

        start: function () {
            var self = this;
			return this._super.apply(this, arguments).then(() => {
                _.each(self.widgets, function(widget){
                    widget.appendTo(self.$el.find('.' + widget.parentClass));
                });
			});
	    },
    });

    core.action_registry.add('mining_site_dashboard', MiningSiteDashboardAction);
    return {
        MiningSiteDashboardAction: MiningSiteDashboardAction
    };
});