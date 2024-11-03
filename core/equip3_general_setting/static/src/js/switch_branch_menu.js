odoo.define('equip3_general_setting.SwitchBranchMenu', function(require) {
    "use strict";

    /**
     * When Odoo is configured in multi-branch mode, users should obviously be able
     * to switch their interface from one branch to the other.  This is the purpose
     * of this widget, by displaying a dropdown menu in the systray.
     */

    var config = require('web.config');
    var core = require('web.core');
    var session = require('web.session');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');

    var _t = core._t;

    var SwitchBranchMenu = Widget.extend({
        template: 'equip3_general_setting.SwitchBranchMenu',
        events: {
            'click .dropdown-item[data-menu] div.log_into': '_onSwitchBranchClick',
            'keydown .dropdown-item[data-menu] div.log_into': '_onSwitchBranchClick',
            'click .dropdown-item[data-menu] div.toggle_branch': '_onToggleBranchClick',
            'keydown .dropdown-item[data-menu] div.toggle_branch': '_onToggleBranchClick',
        },
        
        /**
         * @override
         */
        init: function () {
            this._super.apply(this, arguments);
            this.isMobile = config.device.isMobile;
            this._onSwitchBranchClick = _.debounce(this._onSwitchBranchClick, 1500, true);
        },

        /**
         * @override
         */
        willStart: function () {
            var self = this;
            this.allowed_company_ids = _.map(String(session.user_context.allowed_company_ids).split(','), function(id){
                return parseInt(id);});
            this.allowed_branch_ids = _.map(String(session.user_context.allowed_branch_ids).split(','), function(id){
                return parseInt(id);});
            this.user_branches = _.filter(session.user_branches.allowed_branches, function(branch){
                return self.allowed_company_ids.includes(branch[2]);});
            this.current_branch = this.allowed_branch_ids[0];
            this.current_branch_name = _.find(this.user_branches, function (branch) {
                return branch[0] === self.current_branch;
            })[1];
            return this._super.apply(this, arguments);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent|KeyEvent} ev
         */
        _onSwitchBranchClick: function (ev) {
            if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            var dropdownItem = $(ev.currentTarget).parent();
            var dropdownMenu = dropdownItem.parent();
            var branchID = dropdownItem.data('branch-id');
            var allowed_branch_ids = this.allowed_branch_ids;
            if (dropdownItem.find('.fa-square-o').length) {
                // 1 enabled branch: Stay in single branch mode
                if (this.allowed_branch_ids.length === 1) {
                    if (this.isMobile) {
                        dropdownMenu = dropdownMenu.parent();
                    }
                    dropdownMenu.find('.fa-check-square').removeClass('fa-check-square').addClass('fa-square-o');
                    dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
                    allowed_branch_ids = [branchID];
                } else { // Multi branch mode
                    allowed_branch_ids.push(branchID);
                    dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
                }
            }
            $(ev.currentTarget).attr('aria-pressed', 'true');
            session.setBranches(branchID, allowed_branch_ids);
        },

        //--------------------------------------------------------------------------
        // Handlers
        //--------------------------------------------------------------------------

        /**
         * @private
         * @param {MouseEvent|KeyEvent} ev
         */
        _onToggleBranchClick: function (ev) {
            if (ev.type == 'keydown' && ev.which != $.ui.keyCode.ENTER && ev.which != $.ui.keyCode.SPACE) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            var dropdownItem = $(ev.currentTarget).parent();
            var branchID = dropdownItem.data('branch-id');
            var allowed_branch_ids = this.allowed_branch_ids;
            var current_branch_id = allowed_branch_ids[0];
            var shouldSetBranch = true;
            if (dropdownItem.find('.fa-square-o').length) {
                allowed_branch_ids.push(branchID);
                dropdownItem.find('.fa-square-o').removeClass('fa-square-o').addClass('fa-check-square');
                $(ev.currentTarget).attr('aria-checked', 'true');
            } else {
                if (allowed_branch_ids.length > 1){
                    allowed_branch_ids.splice(allowed_branch_ids.indexOf(branchID), 1);
                    dropdownItem.find('.fa-check-square').addClass('fa-square-o').removeClass('fa-check-square');
                    $(ev.currentTarget).attr('aria-checked', 'false');
                } else {
                    shouldSetBranch = false;
                }
            }
            if (shouldSetBranch){
                session.setBranches(current_branch_id, allowed_branch_ids);
            }
        },

    });

    if (session.display_switch_branch_menu) {
        SystrayMenu.Items.push(SwitchBranchMenu);
    }

    return SwitchBranchMenu;

});
