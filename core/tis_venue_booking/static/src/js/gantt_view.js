odoo.define('tis_venue_booking.GanttView', function (require) {
"use strict";

var AbstractView = require('web.AbstractView');
var core = require('web.core');
var session = require('web.session');
var GanttModel = require('tis_venue_booking.GanttModel');
var GanttRenderer = require('tis_venue_booking.GanttRenderer');
var GanttController = require('tis_venue_booking.GanttController');
var view_registry = require('web.view_registry');

var _t = core._t;
var _lt = core._lt;

// gather the fields to get
var fields_to_gather = [
    "date_start",
    "date_delay",
    "date_stop",
    "consolidation",
    "progress",
];

var scales = [
    'day',
    'week',
    'month',
    'year'
];

// determine locale file to load
var locales_mapping = {
    'ar_SY': 'ar', 'ca_ES': 'ca', 'zh_CN': 'cn', 'cs_CZ': 'cs', 'da_DK': 'da',
    'de_DE': 'de', 'el_GR': 'el', 'es_ES': 'es', 'fi_FI': 'fi', 'fr_FR': 'fr',
    'he_IL': 'he', 'hu_HU': 'hu', 'id_ID': 'id', 'it_IT': 'it', 'ja_JP': 'jp',
    'ko_KR': 'kr', 'nl_NL': 'nl', 'nb_NO': 'no', 'pl_PL': 'pl', 'pt_PT': 'pt',
    'ro_RO': 'ro', 'ru_RU': 'ru', 'sl_SI': 'si', 'sk_SK': 'sk', 'sv_SE': 'sv',
    'tr_TR': 'tr', 'uk_UA': 'ua',
    'ar': 'ar', 'ca': 'ca', 'zh': 'cn', 'cs': 'cs', 'da': 'da', 'de': 'de',
    'el': 'el', 'es': 'es', 'fi': 'fi', 'fr': 'fr', 'he': 'he', 'hu': 'hu',
    'id': 'id', 'it': 'it', 'ja': 'jp', 'ko': 'kr', 'nl': 'nl', 'nb': 'no',
    'pl': 'pl', 'pt': 'pt', 'ro': 'ro', 'ru': 'ru', 'sl': 'si', 'sk': 'sk',
    'sv': 'sv', 'tr': 'tr', 'uk': 'ua',
};
var current_locale = session.user_context.lang || 'en_US';
var current_short_locale = current_locale.split('_')[0];
var locale_code = locales_mapping[current_locale] || locales_mapping[current_short_locale];
var locale_suffix = locale_code !== undefined ? '_' + locale_code : '';

var GanttView = AbstractView.extend({
    cssLibs: [
        "/tis_venue_booking/static/lib/dhtmlxGantt/codebase/dhtmlxgantt.css"
    ],
    jsLibs: [
        "/tis_venue_booking/static/lib/dhtmlxGantt/sources/dhtmlxcommon.js",
        "/tis_venue_booking/static/lib/dhtmlxGantt/codebase/locale/locale" + locale_suffix + ".js"
    ],
    display_name: _lt('Gantt'),
    icon: 'fa-tasks',
    config: _.extend({}, AbstractView.prototype.config, {
        Model: GanttModel,
        Controller: GanttController,
        Renderer: GanttRenderer,
    }),
    viewType: 'gantt',
    /**
     * @override
     */
    init: function (viewInfo, params) {
        this._super.apply(this, arguments);

        var arch = this.arch;
        var fields = this.fields;
        var mapping = {name: 'name'};

        // gather the fields to get
        _.each(fields_to_gather, function (field) {
            if (arch.attrs[field]) {
                mapping[field] = arch.attrs[field];
            }
        });

        // consolidation exclude, get the related fields
        if (arch.attrs.consolidation_exclude) {
            mapping.consolidation_exclude = arch.attrs.consolidation_exclude;
        }
        var scale = arch.attrs.scale_zoom;
        if (!_.contains(scales, scale)) {
            scale = "month";
        }

        // TODO : make sure th 'default_group_by' attribute works
        // var default_group_by = [];
        // if (arch.attrs.default_group_by) {
        //     default_group_by = arch.attrs.default_group_by.split(',');
        // }

        this.controllerParams.context = params.context || {};
        this.controllerParams.title = params.action ? params.action.name : _t("Gantt");
        this.loadParams.fields = fields;
        this.loadParams.mapping = mapping;
        this.loadParams.scale = scale;
        this.loadParams.initialDate = moment(params.initialDate || new Date());
    },
});

view_registry.add('gantt', GanttView);

return GanttView;

});
