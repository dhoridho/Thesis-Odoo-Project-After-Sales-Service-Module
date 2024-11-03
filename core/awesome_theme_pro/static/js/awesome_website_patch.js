odoo.define('awesome_theme.theme_preview_kanban', function (require) {
    "use strict";

    var core = require('web.core');
    var _lt = core._lt;

    require('website.theme_preview_kanban');

    var ViewRegistry = require('web.view_registry');
    var KanBanController = ViewRegistry.get('theme_preview_kanban')
    var ThemePreviewKanbanController = KanBanController.prototype.config.Controller;
    var KanbanController = require('web.KanbanController');

    ThemePreviewKanbanController.include({
        start: async function () {
            await KanbanController.prototype.start.apply(this, arguments);

            // hide pager
            this.el.classList.add('o_view_kanban_theme_preview_controller');

            // update breacrumb
            const websiteLink = Object.assign(document.createElement('a'), {
                className: 'btn btn-secondary ml-3 text-black-75',
                href: '/',
                innerHTML: '<i class="fa fa-close"></i>',
            });
            const smallBreadcumb = Object.assign(document.createElement('small'), {
                className: 'mx-2 text-muted',
                innerHTML: _lt("Don't worry, you can switch later."),
            });
            this._controlPanelWrapper.el.querySelector('.breadcrumb li.active').classList.add('text-black-75');
            this._controlPanelWrapper.el.appendChild(websiteLink);
            this._controlPanelWrapper.el.querySelector('li').appendChild(smallBreadcumb);
        }
    })
});
