odoo.define('awesome_theme_pro.AbstractController', function (require) {
    "use strict";

    const { ComponentWrapper } = require('web.OwlCompatibility');

    var mvc = require('web.mvc');
    var core = require('web.core')
    var AbstractController = require('web.AbstractController')
    var BackendUserSetting = require('awesome_theme_pro.backend_setting')

    AbstractController.include({

        _formatFields(fields) {
            const formattedFields = {};
            for (const fieldName in fields) {
                formattedFields[fieldName] = Object.assign({
                    description: fields[fieldName].string,
                    name: fieldName,
                }, fields[fieldName]);
            }
            return formattedFields;
        },

        get_control_pannel_template: function () {
            return 'awesome_theme_pro.ControlPanel.' + BackendUserSetting.settings.control_panel_mode;
        },

        // async
        start: async function () {

            if (this.withControlPanel) {
                var old_template = this.ControlPanel.template;
            }

            var parent = this.getParent()
            var controllerInfo = this.controllerID && parent && parent.controllers ? parent.controllers[this.controllerID] : undefined

            // if it is execute in dilaog, keep the control pannel
            if (!this.executeInDialog
                && (controllerInfo && !controllerInfo.executeInDialog)) {

                core.bus.trigger('hide_portal_content');

                if (this.ControlPanel) {
                    this.ControlPanel.template = this.get_control_pannel_template()
                }

                this.$el.addClass('o_view_controller');
                this.renderButtons();

                // call the mvc
                const promises = [mvc.Controller.prototype.start.apply(this, ...arguments)];
                if (this.withControlPanel) {
                    this._updateControlPanelProps(this.initialState);
                    this._controlPanelWrapper = new ComponentWrapper(this, this.ControlPanel, this.controlPanelProps);
                    this._controlPanelWrapper.env.bus.on('focus-view', this, () => this._giveFocus());
                    promises.push(this._controlPanelWrapper.mount(this.el, { position: 'first-child' }));
                }

                if (this.withSearchPanel) {
                    this._searchPanelWrapper = new ComponentWrapper(this, this.SearchPanel, this.searchPanelProps);
                    const content = this.el.querySelector(':scope .o_content');
                    content.classList.add('o_controller_with_searchpanel');
                    promises.push(this._searchPanelWrapper.mount(content, { position: 'first-child' }));
                }

                await Promise.all(promises);

                await this._update(this.initialState, { shouldUpdateSearchComponents: false });
                this.updateButtons();
                this.el.classList.toggle('o_view_sample_data', this.model.isInSampleMode());
            } else {
                await this._super.apply(this, arguments)
            }

            if (this.withControlPanel) {
                this.ControlPanel.template = old_template;
            }
        },

        destroy: function () {
            this.executeInDialog = false;
            this._super.apply(this, arguments);
        }
    })
})

