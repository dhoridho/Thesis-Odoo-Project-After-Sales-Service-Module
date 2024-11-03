odoo.define('kpi_scorecard.scorecard_kanbanview', function (require) {
"use strict";

    const ScoreCardKanbanController = require('kpi_scorecard.scorecard_kanbancontroller');
    const ScoreCardKanbanModel = require('kpi_scorecard.scorecard_kanbanmodel');
    const KanbanRenderer = require('web.KanbanRenderer');
    const KanbanView = require('web.KanbanView');
    const view_registry = require('web.view_registry');

    const { _lt } = require('web.core');

    const ScoreCardKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: ScoreCardKanbanController,
            Model: ScoreCardKanbanModel,
            Renderer: KanbanRenderer,
        }),
        searchMenuTypes: ['filter', 'favorite'],
        display_name: _lt('KPI Scorecard'),
        groupable: false,
    });

    view_registry.add('scorecard_kanban', ScoreCardKanbanView);

    return ScoreCardKanbanView;

});
