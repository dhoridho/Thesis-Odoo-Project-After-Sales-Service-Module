odoo.define('acs_hms.acs_hms_char', function (require) {
"use strict";


var AbstractField = require('web.AbstractField');
var FieldRegistry = require('web.field_registry');
var utils = require('web.utils');
var core = require('web.core');
var time = require('web.time');

var _t = core._t;
var qweb = core.qweb;


var _t = core._t;

var AcsDashboardGraph = AbstractField.extend({
    className: "o_dashboard_graph",
    jsLibs: [
        '/web/static/lib/Chart/Chart.js',
    ],
    init: function () {
        this._super.apply(this, arguments);
        //this.graph_type = this.attrs.graph_type;
        this.graph_type = 'line';
        this.data = JSON.parse(this.value);
        this.xlabel = this.attrs.xlabel;
        this.ylabel = this.attrs.ylabel;
    },
    /**
     * The widget view uses the ChartJS lib to render the graph. This lib
     * requires that the rendering is done directly into the DOM (so that it can
     * correctly compute positions). However, the views are always rendered in
     * fragments, and appended to the DOM once ready (to prevent them from
     * flickering). We here use the on_attach_callback hook, called when the
     * widget is attached to the DOM, to perform the rendering. This ensures
     * that the rendering is always done in the DOM.
     */
    on_attach_callback: function () {
        this._isInDOM = true;
        this._renderInDOM();
    },
    /**
     * Called when the field is detached from the DOM.
     */
    on_detach_callback: function () {
        this._isInDOM = false;
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Render the widget only when it is in the DOM.
     *
     * @override
     * @private
     */
    _render: function () {
        if (this._isInDOM) {
            return this._renderInDOM();
        }
        return Promise.resolve();
    },
    /**
     * Render the widget. This function assumes that it is attached to the DOM.
     *
     * @private
     */
    _renderInDOM: function () {
        this.$el.empty();
        var config, cssClass;
        if (this.graph_type === 'line') {
            config = this._getLineChartConfig();
            cssClass = 'acs_graph_linechart';
        }
        this.$canvas = $('<canvas/>');
        this.$el.addClass(cssClass);
        this.$el.empty();
        this.$el.append(this.$canvas);
        var context = this.$canvas[0].getContext('2d');
        this.chart = new Chart(context, config);
    },
    _getLineChartConfig: function () {
        var labels = this.data[0].values.map(function (pt) {
            return pt.x;
        });
        var borderColor = this.data[0].is_sample_data ? '#dddddd' : '#875a7b';

        var line_data = [{
            data: this.data[0].values,
            fill: 'start',
            label: this.data[0].key,
            borderColor: this.data[0].color,
            borderWidth: 2,
        }]
        if (this.data.length>=2) {
            var line_data = [{
                data: this.data[0].values,
                fill: 'start',
                label: this.data[0].key,
                borderColor: this.data[0].color,
                borderWidth: 2,
            },
            {
                data: this.data[1].values,
                fill: 'start',
                label: this.data[1].key,
                borderColor: this.data[1].color,
                borderWidth: 2,
            }]

        }

        return {
            type: 'line',
            data: {
                labels: labels,
                datasets: line_data 
            },
            options: {
                legend: {display: true},
                scales: {
                    yAxes: [{
                        display: true,
                        scaleLabel: {
                            display: true,
                            labelString: this.ylabel,
                            fontSize: 14
                        }
                    }],
                    xAxes: [{
                        display: true,
                        scaleLabel: {
                            display: true,
                            labelString: this.xlabel,
                            fontSize: 14
                        }
                    }]
                },
                maintainAspectRatio: false,
                elements: {
                    line: {
                        tension: 0.000001
                    }
                },
                tooltips: {
                    intersect: false,
                    position: 'nearest',
                    caretSize: 0,
                },
            },
        };
    },
    
});
    
FieldRegistry.add('AcsDashboardGraph', AcsDashboardGraph);

});