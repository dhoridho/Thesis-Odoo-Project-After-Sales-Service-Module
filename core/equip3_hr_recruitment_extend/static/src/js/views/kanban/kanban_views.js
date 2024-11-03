odoo.define('equip3_hr_recruitment_extend.RecruitmentKanbanView', function (require) {
"use strict";

    var KanbanRecord = require('web.KanbanRecord');
    var KanbanRenderer = require('web.KanbanRenderer');
    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var view_registry = require('web.view_registry');

    var RecruitmentKanbanRecord = KanbanRecord.extend({
        events: _.extend({}, KanbanRecord.prototype.events, {
            'click': '_onSelectRecord'
        }),

        _onSelectRecord: function(ev){
            var hasNotActiveDropdown = this.$el.parent().find('.o_dropdown_open').length == 0;
            if (hasNotActiveDropdown){
                var isNotButton = $(ev.target).closest('button').length == 0;
                var isNotA = $(ev.target).closest('a').length == 0;
                if (isNotButton && isNotA){
                    ev.preventDefault();
                    this.trigger_up('on_kanban_box_clicked', {id: this.db_id, mode: 'edit'});
                }
            } else {
                var isNotDropdownButton = $(ev.target).closest('a.o_kanban_manage_toggle_button').length == 0;
                if (isNotDropdownButton){
                    this.$el.parent().find('.o_kanban_record').removeClass('o_dropdown_open');
                }
            }
        }
    });


    var RecruitmentKanbanRenderer = KanbanRenderer.extend({
        config: _.extend({}, KanbanRenderer.prototype.config, {
            KanbanRecord: RecruitmentKanbanRecord
        }),
    });

    var RecruitmentKanbanController = KanbanController.extend({
        events: _.extend({}, KanbanController.prototype.events, {
            'click': '_onAnyWhereClick'
        }),
        custom_events: _.extend({}, KanbanController.prototype.custom_events, {
            on_kanban_box_clicked: '_onKanbanBoxClicked'
        }),

        start: function () {
            this.$el.addClass('o_recruitment_kanban_controller');
            return this._super.apply(this, arguments);
        },

        _onKanbanBoxClicked: function(ev){
            ev.stopPropagation();
            var record = this.model.get(ev.data.id, {raw: true});
            this.trigger_up('switch_view', {
                view_type: 'form',
                res_id: record.res_id,
                mode: ev.data.mode,
                model: this.modelName
            });
        },

        _onAnyWhereClick: function(ev){
            ev.stopPropagation();
            var isNotKanbanRecord = $(ev.target).closest('.o_kanban_record').length == 0;
            var self = this;
            if (isNotKanbanRecord){
                self.$el.find('.o_dropdown_open').each(function(){
                    $(this).removeClass('o_dropdown_open');
                });
            }
        }
    });

    var RecruitmentKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Renderer: RecruitmentKanbanRenderer,
            Controller: RecruitmentKanbanController
        })
    });

    view_registry.add('hr_recruitment_kanban', RecruitmentKanbanView);

    return RecruitmentKanbanView;
});
