odoo.define('equip3_crm_insight.CRMInsight', function(require){
    "use strict";

    const AbstractAction = require('web.AbstractAction');
    const core = require('web.core');
    const field_utils = require('web.field_utils');
    const session = require('web.session');
    const Widget = require('web.Widget');
    const config = require('web.config');

    const _t = core._t;
    const QWeb = core.qweb;

    const InsightWidget = Widget.extend({
        name: 'insight_widget',
        label: _t('Insight Widget'),
        template: 'InsightWidget',
        titleAlign: 'left',

        events: {
            'click .o_config': '_onSelectEditor',
            'click .o_btn_editor': '_onButtonEditorClick',
            'click .o_demo_checkbox': '_toggleDemoData',
        },

        init: function(parent, options){
            this._super.apply(this, arguments);
            this.parent = parent;
            this.currency = Object.keys(session.currencies).length > 0 ? session.currencies[Object.keys(session.currencies)[0]] : {};
            this.container = options.container;
            this.isDebug = config.isDebug();

            this.editors = {
                demo: {
                    label: _t('Demo Data'), 
                    prefix: 'demo_data', 
                    default: this._demoData.bind(this), 
                    visible: true
                }
            }
        },

        start: function(){
            this.$el = $(this.el);
            this.$configDropdown = this.$('.o_config_dropdown');
            this.$checkbox = this.$('input.o_demo_input');
            this._update();
            return this._super.apply(this, arguments);
        },

        _buildData: function(){
            let data = {};
            if (this.useDemo){
                data = this._demoData();
            } else {
                data = this._realData();
            }
            this.data = data;
        },

        _update: function(){
            var self = this;
            this.useDemoCfg = _.find(this.parent.result.configs, con => con.name === `use_demo_${this.name}`);
            this.useDemo = this.useDemoCfg ? JSON.parse(this.useDemoCfg.value).use_demo : false;
            this.$checkbox.prop('checked', this.useDemo);

            _.each(this.editors, function(cfg, configName){
                let config = _.find(self.parent.result.configs, con => con.name === `${cfg.prefix}_${self.name}`);
                let $el = $(QWeb.render('InsightEditor', {configName: configName}));

                let editor = new JSONEditor($el.find('.o_editor')[0], {});
                _.extend(cfg, {$el: $el, editor: editor, config: config});
            });

            this._buildData();

            _.each(this.editors, function(cfg){
                cfg.editor.set(cfg.default());
            })

            this.$content = $(QWeb.render(this.contentTemplate, {widget: this}));
            this.$('.o_box_content').html(this.$content);

            _.each(this.editors, function(cfg, configName){
                let $el = self.$el.find(`.o_box_editor[data-editor="${configName}"]`);
                if ($el.length){
                    $el.remove();
                }
                self.$el.append(cfg.$el);
            });
        },

        _defaultDemoData: function(){
            return {};
        },

        _demoData: function(){
            if (this.editors.demo.config){
                return JSON.parse(this.editors.demo.config.value);
            }
            return this._defaultDemoData();
        },

        _realData: function(){
            return {};
        },

        _onSelectEditor: function(ev){
            let $target = $(ev.currentTarget);
            let editorName = $target.data('editor');
            _.each(this.editors, function(cfg, configName){
                cfg.$el.toggleClass('d-none', configName !== editorName);
            });
        },

        _updateUseDemo: function(useDemo){
            let value = JSON.stringify({"use_demo": useDemo});
            return {
                method: this.useDemoCfg ? 'write' : 'create',
                args: this.useDemoCfg ? [[this.useDemoCfg.id], {value: value}] : [{name: `use_demo_${this.name}`, value: value}],
            };
        },

        _toggleDemoData: function(ev){
            ev.stopPropagation();
            let useDemo = !this.useDemo;
            this.trigger_up('config_change', {
                updates: [this._updateUseDemo(useDemo)], 
                widget: this
            });
        },

        _onButtonEditorClick: function(ev){
            ev.stopPropagation();
            let $target = $(ev.currentTarget);
            let $parent = $target.closest('.o_box_editor');
            let editorName = $parent.data('editor');

            let action = `_${$target.data('action')}Editor`;
            console.log('>>> ACTION')
            console.log(action)
            this[action](editorName);
        },

        _saveEditor: function(editorName){
            let updates = [];
            if (editorName === 'demo'){
                updates.push(this._updateUseDemo(true));
            }

            let editor = this.editors[editorName];
            let config = JSON.stringify(editor.editor.get());

            updates.push({
                method: editor.config ? 'write' : 'create',
                args: editor.config ? [[editor.config.id], {value: config}] : [{name: `${editor.prefix}_${this.name}`, value: config}],
            })
            this.trigger_up('config_change', {updates: updates, widget: this});
        },

        _resetEditor: function(editorName){
            let editor = this.editors[editorName];
            if (editor.config){
                this.trigger_up('config_change', {
                    updates: [{
                        method: 'unlink',
                        args: [[editor.config.id]]
                    }],
                    widget: this
                });
            } else {
                editor.editor.set(editor.default());
            }
        },

        _discardEditor: function(editorName){
            this.editors[editorName].$el.addClass('d-none');
        },

        _getPercentage(this_value, last_value){
            let percentage = Math.round((this_value / last_value) * 100, 2);
            percentage *= this_value > last_value ? 1 : -1;
            return percentage;
        },

        _formatCurrency: function(value){
            let formatted = field_utils.format.monetary(value, {}, {currency: this.currency}) + '.00';
            return formatted.replace('&nbsp;', ' ');
        },
    });

    const TotalClosing = InsightWidget.extend({
        name: 'total_closing',
        label: _t('Total Closing'),
        contentTemplate: 'InsightTotalClosing',

        _defaultDemoData: function(){
            return {
                this_month: {value: 1000000},
                last_month: {value: 700000},
                this_quarter: {value: 1500000},
                last_quarter: {value: 2000000},
            };
        },

        _realData: function(){
            var leads = this.parent.result.leads;

            function getRevenue(start, end){
                return _.map(
                    _.filter(leads, lead => lead.date_closed.isBetween(start, end, 'days', '[]')), 
                lead => lead.expected_revenue).reduce((a, b) => a + b, 0);
            }

            return {
                this_month: {value: getRevenue(moment().startOf('month'), moment().endOf('month'))},
                last_month: {value: getRevenue(moment().subtract(1, 'months').startOf('month'), moment().subtract(1, 'months').endOf('month'))},
                this_quarter: {value: getRevenue(moment().startOf('quarter'), moment().endOf('quarter'))},
                last_quarter: {value: getRevenue(moment().subtract(1, 'quarters').startOf('quarter'), moment().subtract(1, 'quarters').endOf('quarter'))},
            };
        },

        _buildData: function(){
            this._super.apply(this, arguments);
            this.data.this_month.percentage = this._getPercentage(this.data.this_month.value, this.data.last_month.value);
            this.data.this_quarter.percentage = this._getPercentage(this.data.this_quarter.value, this.data.last_quarter.value);
        }
    });

    const Trending = InsightWidget.extend({
        name: 'trending',
        label: _t('Trending'),
        contentTemplate: 'InsightTrending',

        _defaultDemoData: function(){
            return [
                _t('The most engagement source in this month is from LinkedIn'),
                _t('The least engagement source in this month is from Facebook'),
                _t('Customer Generation in this Quarter is 100'),
                _t('Favorite campaign in this quarter is ......')
            ];
        },

        _realData: function(){
            return [];
        }
    });

    const GeneratedAccount = InsightWidget.extend({
        name: 'generated_account',
        label: _t('Generated Account'),
        contentTemplate: 'InsightCircle',
        titleAlign: 'center',

        _defaultDemoData: function(){
            return {
                left: {
                    this_value: 10,
                    last_value: 15,
                    text: _t('This Month')
                },
                right: {
                    this_value: 40,
                    last_value: 20,
                    text: _t('This Quarter')
                }
            };
        },

        _realData: function(){
            var partners = this.parent.result.partners;

            function getPartners(start, end){
                return _.filter(partners, partner => partner.customer_creation_date.isBetween(start, end, 'days', '[]')).length;
            }

            return {
                left: {
                    this_value: getPartners(moment().startOf('month'), moment().endOf('month')),
                    last_value: getPartners(moment().subtract(1, 'months').startOf('month'), moment().subtract(1, 'months').endOf('month')),
                    text: _t('This Month')
                },
                right: {
                    this_value: getPartners(moment().startOf('quarter'), moment().endOf('quarter')),
                    last_value: getPartners(moment().subtract(1, 'quarters').startOf('quarter'), moment().subtract(1, 'quarters').endOf('quarter')),
                    text: _t('This Quarter')
                }
            };
        },

        _buildData: function(){
            this._super.apply(this, arguments);
            this.data.left.percentage = this._getPercentage(this.data.left.this_value, this.data.left.last_value);
            this.data.right.percentage = this._getPercentage(this.data.right.this_value, this.data.right.last_value);
        }
    });

    const Opportunities = InsightWidget.extend({
        name: 'opportunities',
        label: _t('Opportunities'),
        contentTemplate: 'InsightCircle',
        titleAlign: 'center',

        _defaultDemoData: function(){
            return {
                left: {
                    this_value: 186,
                    text: _t('Won Opportunities')
                },
                right: {
                    this_value: 105,
                    text: _t('Lost Opportunities')
                }
            };
        },

        _realData: function(){
            var leads = this.parent.result.leads;
            return {
                left: {
                    this_value: _.filter(leads, lead => lead.active && lead.stage_is_won).length,
                    text: _t('Won Opportunities')
                },
                right: {
                    this_value: _.filter(leads, lead => !lead.active && lead.probability === 0).length,
                    text: _t('Lost Opportunities')
                }
            };
        }
    });

    const WonRevenue = InsightWidget.extend({
        name: 'won_revenue',
        label: _t('Won Revenue'),
        contentTemplate: 'InsightCircle',
        titleAlign: 'center',

        _defaultDemoData: function(){
            return {
                left: {
                    this_value: 17,
                    last_value: 15,
                    text: _t('This Month')
                },
                right: {
                    this_value: 33,
                    last_value: 50,
                    text: _t('This Quarter')
                },
            };
        },

        _realData: function(){
            var leads = this.parent.result.leads;

            function getLeads(start, end){
                return _.filter(leads, lead => lead.active && lead.stage_is_won && lead.date_closed.isBetween(start, end, 'days', '[]')).length;
            }

            return {
                left: {
                    this_value: getLeads(moment().startOf('month'), moment().endOf('month')),
                    last_value: getLeads(moment().subtract(1, 'months').startOf('month'), moment().subtract(1, 'months').endOf('month')),
                    text: _t('This Month')
                },
                right: {
                    this_value: getLeads(moment().startOf('quarter'), moment().endOf('quarter')),
                    last_value: getLeads(moment().subtract(1, 'quarters').startOf('quarter'), moment().subtract(1, 'quarters').endOf('quarter')),
                    text: _t('This Quarter')
                },
            };
        },

        _buildData: function(){
            this._super.apply(this, arguments);
            this.data.left.percentage = this._getPercentage(this.data.left.this_value, this.data.left.last_value);
            this.data.right.percentage = this._getPercentage(this.data.right.this_value, this.data.right.last_value);
        }
    });

    const ChartInsightWidget = InsightWidget.extend({
        name: 'chart_insight_widget',
        isChart: true,
        chartType: 'bar',
        legendPosition: 'top',
        customLegend: true,
        legendIcon: '<span class="fa fa-circle"></span>',
        contentTemplate: 'InsightChartContainer',

        init: function(parent, options){
            this._super.apply(this, arguments);
            _.extend(this.editors, {
                chart: {
                    label: _t('Chart Config'), 
                    prefix: 'chart_config', 
                    default: this._filterConfig.bind(this), 
                    visible: this.isChart
                }
            });
        },

        _update: function(){
            this._super.apply(this, arguments);
            this.$canvas = this.$content.find('canvas');
            if (this.customLegend){
                this.$legend = this.$content.find(`.o_${this.name}_legend`);
            }
            this._renderChart();
        },

        _filterConfig: function(config){
            if (!config){
                config = this._chartConfig();
            }
            if ('type' in config){
                delete config.type;
            }
            if ('data' in config){
                if ('labels' in config.data){
                    delete config.data.labels;
                }
                if ('datasets' in config.data){
                    _.each(config.data.datasets, function(dataset){
                        if ('data' in dataset){
                            delete dataset.data;
                        }
                    })
                }
            }
            if ('plugins' in config){
                delete config.plugins;
            }
            return config;
        },

        _chartData: function(){
            return {};
        },

        _chartOptions: function(){
            return {};
        },

        _chartPlugins: function(){
            return [];
        },

        _chartConfig: function(){
            let config = {
                type: this.chartType,
                data: this._chartData(),
                options: this._chartOptions(),
                plugins: this._chartPlugins()
            };
            if (this.editors.chart.config){
                let customConfig = this._filterConfig(JSON.parse(this.editors.chart.config.value));
                $.extend(true, config, customConfig);
            }
            return config;
        },

        _renderChart: function(){
            if (this.chart){
                this.chart.destroy();
            }
            var ctx = this.$canvas[0].getContext('2d');
            var config = this._chartConfig();

            this.chart = new Chart(ctx, config);

            if (this.customLegend){
                this.$legend.html(this._generateCustomLegend());
            }
        },

        _generateCustomLegend: function(){
            let labels, colors;
            if (this.chart.data.datasets.length > 1){
                labels = _.map(this.chart.data.datasets, d => d.label);
                colors = _.map(this.chart.data.datasets, d => d.backgroundColor)
            } else {
                labels = this.chart.data.labels;
                colors = this.chart.data.datasets[0].backgroundColor;
            }

            let $legend = $(QWeb.render('InsightCustomLegend', {
                labels: labels,
                colors: colors,
                icon: this.legendIcon,
            }));

            $legend.find('li.o_legend').on('click', this._onChangeLegend.bind(this));
            return $legend;
        },

        _onChangeLegend: function (e) {
            var $target = $(e.currentTarget);
            var index = $target.data('index');

            var obj;
            if (this.chart.config.data.datasets.length === 1){
                obj = this.chart.getDatasetMeta(0).data[index];
            } else {
                obj = this.chart.getDatasetMeta(index);
            }

            obj.hidden = !obj.hidden;
            $target.toggleClass('o_hide');
            this.chart.update();
        }
    });

    const RevenuePerLeadType = ChartInsightWidget.extend({
        name: 'revenue_per_lead_type',
        label: _t('Revenue Per Lead Type'),
        chartType: 'horizontalBar',
        legendIcon: `<svg xmlns="http://www.w3.org/2000/svg" width="56" height="35" viewBox="0 0 56 35" fill="none">
            <rect x="45" width="9" height="45" rx="4.5" transform="rotate(90 45 0)" fill="currentColor"/>
            <rect x="35" y="13" width="9" height="35" rx="4.5" transform="rotate(90 35 13)" fill="currentColor"/>
            <rect x="56" y="26" width="9" height="56" rx="4.5" transform="rotate(90 56 26)" fill="currentColor"/>
        </svg>`,

        _defaultDemoData: function(){
            return {
                thisQuarter: [
                    {type: 'Type 1', value: 3100},
                    {type: 'Type 2', value: 1900},
                    {type: 'Type 3', value: 4500},
                    {type: 'Type 4', value: 3000},
                    {type: 'Type 5', value: 4000},
                ],
                lastQuarter: [
                    {type: 'Type 1', value: 4000},
                    {type: 'Type 2', value: 2900},
                    {type: 'Type 3', value: 3800},
                    {type: 'Type 4', value: 4200},
                    {type: 'Type 5', value: 2100},
                ]
            };
        },

        _realData: function(){
            var leads = this.parent.result.leads;

            var types = {};
            _.each(leads, function(lead){
                if (lead.type_name in types){
                    types[lead.type_name].push({date_closed: lead.date_closed, revenue: lead.expected_revenue});
                } else if (lead.type_name){
                    types[lead.type_name] = [{date_closed: lead.date_closed, revenue: lead.expected_revenue}];
                }
            });

            let thisStart = moment().startOf('quarter');
            let thisEnd = moment().endOf('quarter');
            let lastStart = moment().subtract(1, 'quarters').startOf('quarter');
            let lastEnd = moment().subtract(1, 'quarters').endOf('quarter');

            let thisQuarter = [];
            let lastQuarter = [];
            _.each(types, function(leadsType, typeName){
                if (typeName){
                    let thisRevenue = 0, lastRevenue = 0;
                    _.each(leadsType, function(lt){
                        if (lt.date_closed.isBetween(thisStart, thisEnd, 'days', '[]')){
                            thisRevenue += lt.revenue;
                        } else if (lt.date_closed.isBetween(lastStart, lastEnd, 'days', '[]')){
                            lastRevenue += lt.revenue;
                        }
                    });
                    thisQuarter.push({type: typeName, value: thisRevenue});
                    lastQuarter.push({type: typeName, value: lastRevenue});
                }
                
            });
            return {
                thisQuarter: thisQuarter,
                lastQuarter: lastQuarter
            };
        },

        _chartData: function(){
            return {
                labels: _.map(this.data.thisQuarter, r => r.type),
                datasets: [{
                    label: _t('This Quarter'),
                    data: _.map(this.data.thisQuarter, r => r.value),
                    backgroundColor: '#377DFF',
                    borderWidth: 0,
                }, {
                    label: _t('Last Quarter'),
                    data: _.map(this.data.lastQuarter, r => r.value),
                    backgroundColor: '#FF5630',
                    borderWidth: 0
                }]
            };
        },

        _chartOptions: function(){
            return {
                scales: {
                    xAxes: [{
                        gridLines: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            // callback: function(value, index, values) {
                            //     return Math.round(value / 1000, 2) + 'K';
                            // },
                            min: 0,
                            // stepSize: 1000,
                            fontFamily: 'Lato',
                            fontColor: '#4F4F4F'
                        }
                    }],
                    yAxes: [{
                        gridLines: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            fontFamily: 'Lato',
                            fontColor: '#4F4F4F'
                        }
                    }]
                },
                legend: {
                    display: false
                },
                cornerRadius: 20,
                plugins: {
                    datalabels: {
                        display: false
                    },
                }
            };
        }
    });

    const TopSource = ChartInsightWidget.extend({
        name: 'top_source',
        label: _t('Top Source'),
        chartType: 'funnel',
        legendPosition: 'bottom',

        _defaultDemoData: function(){
            return [
                {name: 'Facebook', value: 1000890990},
                {name: 'LinkedIn', value: 908030678},
                {name: 'WhatsApp', value: 408385047},
                {name: 'NewsLetter', value: 1000000},
                {name: 'Youtube', value: 450000},
            ];
        },

        _realData: function(){
            var leads = this.parent.result.leads;
            var sources = {};
            _.each(leads, function(lead){
                if (lead.source_name in sources){
                    sources[lead.source_name] += lead.expected_revenue;
                } else if (lead.source_name) {
                    sources[lead.source_name] = lead.expected_revenue;
                }
            });
            return _.map(sources, function(revenue, source){ return {name: source, value: revenue}; })
            .sort((a, b) => b.value - a.value)
            .slice(0, 5);
        },

        _chartData: function(){
            return {
                labels: _.map(this.data, source => source.name),
                datasets: [{
                    data: _.map(this.data, source => source.value),
                    backgroundColor: ['#002F87', '#0243BC', '#0052EB', '#2C6FEC', '#4A8AFF'],
                }]
            };
        },

        _chartOptions: function(){
            return {
                title: {
                    display: false
                },
                legend: {
                    display: false
                },
                sort: 'desc',
                topWidth: 100,
                bottomWidth: 400,
                plugins: {
                    datalabels: {
                        display: false
                    },
                }
            };
        },

        _chartPlugins: function(){
            var self = this;
            return [{
                beforeTooltipDraw: function(chart){
                    var { ctx } = chart;
                    var meta = chart.getDatasetMeta(0);
                    var visibleDataCount = _.filter(meta.data, d => !d.hidden).length;
                    let m = chart.height / visibleDataCount;
                    let o = m / 2;
                    let i = 0;
                    _.each(self.data, function(source){
                        let legend = _.find(chart.legend.legendItems, leg => leg.text === source.name);
                        if (!legend.hidden){
                            ctx.save();
                            ctx.textAlign = 'center';
                            ctx.font = '12px Lato';
                            ctx.fillStyle = 'white';
                            ctx.fillText(self._formatCurrency(source.value), chart.width / 2, (i * m) + o);
                            ctx.restore();
                            i += 1;
                        }
                    });
                },
            }]
        }
    });

    const BestTeam = ChartInsightWidget.extend({
        name: 'best_team',
        label: _t('Best Team'),
        chartType: 'line',
        customLegend: false,

        _defaultDemoData: function(){
            return [
                {name: 'Eropa', value: 998100},
                {name: 'Team EVA HR', value: 4810000},
                {name: 'Pelawak Handal', value: 999000},
                {name: 'Team Intern Batch 4', value: 325000},
                {name: 'Tim Satu Rasa', value: 473500}
            ];
        },

        _realData: function(){
            var leads = this.parent.result.leads;
            var teams = {};
            _.each(leads, function(lead){
                if (lead.team_name in teams){
                    teams[lead.team_name] += lead.expected_revenue;
                } else if (lead.team_name) {
                    teams[lead.team_name] = lead.expected_revenue;
                }
            });
            return _.map(teams, function(revenue, team){ return {name: team, value: revenue}; })
            .sort((a, b) => b.value - a.value)
            .slice(0, 5);
        },

        _chartData: function(){
            return {
                labels: _.map(this.data, team => team.name),
                datasets: [{
                    data: _.map(this.data, team => team.value),
                    borderColor: '#377DFF',
                    borderWidth: 4,
                    pointBackgroundColor: 'transparent',
                    pointBorderWidth: 3,
                    pointBorderColor: '#FFA600',
                    pointRadius: 6,
                    fill: false
                }]
            };
        },

        _chartOptions: function(){
            return {
                layout: {
                    padding: {
                        top: 30,
                        right: 50
                    }
                },
                plugins: {
                    datalabels: {
                        align: 'top',
                        offset: 10,
                        backgroundColor: '#377DFF',
                        color: '#FFFFFF',
                        borderRadius: 5,

                        formatter: function(value, context){
                            if (value / 1000000 > 1){
                                return (value / 1000000).toFixed(2) + 'M';
                            }
                            return (value / 1000).toFixed(2) + 'K';
                        }
                    }
                },
                scales: {
                    xAxes: [{
                        gridLines: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            fontFamily: 'Lato',
                            fontColor: '#4F4F4F'
                        }
                    }],
                    yAxes: [{
                        gridLines: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            // callback: function(value, index, values) {
                            //     if (value){
                            //         return Math.round(value / 1000000, 2) + 'M';
                            //     }
                            //     return '';
                            // },
                            min: 0,
                            // stepSize: 1000000,
                            fontFamily: 'Lato',
                            fontColor: '#4F4F4F'
                        }
                    }]
                },
                legend: {
                    display: false
                }
            }
        }
    });

    const ReasonOfLost = ChartInsightWidget.extend({
        name: 'reason_of_lost',
        label: _t('Reason of Lost'),
        chartType: 'horizontalBar',
        customLegend: false,

        _defaultDemoData: function(){
            return [
                {name: 'Too expensive', value: 20},
                {name: "We don't have people/skills", value: 10},
                {name: 'Not enough stock', value: 30},
                {name: 'Yuyu', value: 5},
            ];
        },

        _realData: function(){
            var leads = this.parent.result.leads;
            var reasons = {};
            _.each(leads, function(lead){
                if (lead.reason_name in reasons){
                    reasons[lead.reason_name] += 1;
                } else if (lead.reason_name) {
                    reasons[lead.reason_name] = 1;
                }
            });
            return _.map(reasons, function(count, reason){ return {name: reason, value: count}; });
        },

        _chartData: function(){
            return {
                labels:  _.map(this.data, reason => reason.name),
                datasets: [{
                    data:  _.map(this.data, reason => reason.value),
                    backgroundColor: '#2D9AFF'
                }]
            }
        },

        _chartOptions: function(){
            return {
                legend: {
                    display: false
                },
                scales: {
                    xAxes: [{
                        gridLines: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            min: 0,
                            fontFamily: 'Lato',
                            fontColor: '#4F4F4F'
                        }
                    }],
                    yAxes: [{
                        gridLines: {
                            drawOnChartArea: false
                        },
                        ticks: {
                            min: 0,
                            fontFamily: 'Lato',
                            fontColor: '#4F4F4F'
                        }
                    }]
                },
                plugins: {
                    datalabels: {
                        display: false
                    },
                }
            }
        }
    });

    const CRMInsight = AbstractAction.extend({
        template: 'CRMInsight',

        jsLibs: [
            'web/static/lib/Chart/Chart.js',
            'equip3_crm_insight/static/lib/chartjs-plugin-datalabels.min.js',
            'equip3_crm_insight/static/lib/Chart.roundedBarCharts.min.js',
            'equip3_crm_insight/static/lib/chart.funnel.equal.js',
            'https://cdn.jsdelivr.net/npm/jsoneditor@9.10.2/dist/jsoneditor.min.js',
        ],

        cssLibs: [
            'https://cdn.jsdelivr.net/npm/jsoneditor@9.10.2/dist/jsoneditor.min.css'
        ],

        custom_events: {
            config_change: '_onConfigChange'
        },

        init: function (parent, action, options) {
            this._super.apply(this, arguments);
        },

        willStart: function(){
            var self = this;
            var dataProm = this._rpc({
                model: 'crm.insight.data',
                method: 'get_data'
            }).then(function(result){
                self.result = result;
                self._postProcessData();
            });
            return Promise.all([this._super.apply(this, arguments), dataProm]);
        },

        _postProcessData: function(){
            function toMoment(dateStr){
                return moment(dateStr, 'YYYY-MM-DD HH:mm:ss');
            }

            _.each(this.result.leads, function(lead){
                lead.date_closed = toMoment(lead.date_closed);
            });
            _.each(this.result.partners, function(partner){
                partner.customer_creation_date = toMoment(partner.customer_creation_date);
            });
        },

        start: function(){
            var self = this;

            this.widgets = {
                totalClosing: new TotalClosing(this, {container: 'o_total_closing'}),
                trennding: new Trending(this, {container: 'o_trending'}),
                generatedAccount: new GeneratedAccount(this, {container: 'o_generated_account'}),
                opportunities: new Opportunities(this, {container: 'o_opportunities'}),
                wonRevenue: new WonRevenue(this, {container: 'o_won_revenue'}),
                revenuePerLeadType: new RevenuePerLeadType(this, {container: 'o_revenue_per_lead_type'}),
                topSource: new TopSource(this, {container: 'o_top_source'}),
                bestTeam: new BestTeam(this, {container: 'o_best_team'}),
                reasonOfLost: new ReasonOfLost(this, {container: 'o_reason_of_lost'})
            };

            return this._super.apply(this, arguments).then(function(){
                _.each(self.widgets, function(widget){
                    widget.appendTo(self.$el.find('.' + widget.container));
                })
            });
        },

        _onConfigChange: function(ev){
            var self = this;

            var { updates, widget } = ev.data;
            var proms = [];
            _.each(updates, function(update){
                let { method, args } = update;
                proms.push(self._rpc({
                    model: 'crm.insight.data',
                    method: method,
                    args: args
                }));
            });

            return Promise.all(proms).then(function(results){
                _.each(updates, function(update, index){
                    var result = results[index];
                    let { method, args } = update;

                    if (method === 'create'){
                        self.result.configs.push({
                            id: result,
                            name: args[0].name,
                            value: args[0].value
                        });
                    } else if (method === 'write'){
                        let config = _.find(self.result.configs, cfg => cfg.id === args[0][0]);
                        config.value = args[1].value;
                    } else if (method === 'unlink'){
                        let index = _.findIndex(self.result.configs, cfg => cfg.id === args[0][0]);
                        self.result.configs.splice(index, 1);
                    } else {
                        return;
                    }
                });
                widget._update();
            });
        }
    });

    core.action_registry.add('crm_insight', CRMInsight);
    return CRMInsight;
});