odoo.define('kpi_scorecard.scorecard_kanbanmodel', function (require) {
"use strict";

    const KanbanModel = require('web.KanbanModel');

    const ScoreCardKanbanModel = KanbanModel.extend({
        reload: function (id, options) {
            // Re-write to explicitly retrieve searchDomain from element, when no options.domain is received
            options = options || {};
            var element = this.localData[id];
            var searchDomain = options.domain || element.searchDomain || [];
            element.searchDomain = options.searchDomain = searchDomain;
            if (options.kpiDomain !== undefined) {
                options.domain = searchDomain.concat(options.kpiDomain);
            };
            return this._super.apply(this, arguments);
        },
    });


    return ScoreCardKanbanModel;


});