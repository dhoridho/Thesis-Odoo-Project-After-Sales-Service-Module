odoo.define('awesome.MenuPannel', function (require) {
    "use strict";

    const DropdownMenuItem = require('web.DropdownMenuItem');

    const { Component, hooks } = owl;
    const { useExternalListener, useRef, useState } = hooks;

    class AwesomeMenuPannel extends Component {
        constructor() {
            super(...arguments);

            this.dropdownMenu = useRef('dropdown');
            this.state = useState({ open: false });
        }

        //---------------------------------------------------------------------
        // Getters
        //---------------------------------------------------------------------

        /**
         * In desktop, by default, we do not display a caret icon next to the
         * dropdown.
         * @returns {boolean}
         */
        get displayCaret() {
            return false;
        }

        /**
         * In mobile, by default, we display a chevron icon next to the dropdown
         * button. Note that when 'displayCaret' is true, we display a caret
         * instead of a chevron, no matter the value of 'displayChevron'.
         * @returns {boolean}
         */
        get displayChevron() {
            return this.env.device.isMobile;
        }

        /**
         * Can be overriden to force an icon on an inheriting class.
         * @returns {string} Font Awesome icon class
         */
        get icon() {
            return this.props.icon;
        }

        /**
         * Meant to be overriden to provide the list of items to display.
         * @returns {Object[]}
         */
        get items() {
            return this.props.items;
        }

        /**
         * @returns {string}
         */
        get title() {
            return this.props.title;
        }

        //---------------------------------------------------------------------
        // Handlers
        //---------------------------------------------------------------------

        /**
         * @private
         * @param {KeyboardEvent} ev
         */
        _onButtonKeydown(ev) {
            switch (ev.key) {
                case 'ArrowLeft':
                case 'ArrowRight':
                case 'ArrowUp':
                case 'ArrowDown':
                    const firstItem = this.el.querySelector('.dropdown-item');
                    if (firstItem) {
                        ev.preventDefault();
                        firstItem.focus();
                    }
            }
        }

        /**
         * @private
         * @param {OwlEvent} ev
         */
        _onItemSelected(/* ev */) {
            if (this.props.closeOnSelected) {
                this.state.open = false;
            }
        }
    }

    AwesomeMenuPannel.components = { DropdownMenuItem };
    AwesomeMenuPannel.defaultProps = { items: [] };
    AwesomeMenuPannel.props = {
        icon: { type: String, optional: 1 },
        items: {
            type: Array,
            element: Object,
            optional: 1,
        },
        title: { type: String, optional: 1 },
        closeOnSelected: { type: Boolean, optional: 1 },
    };
    AwesomeMenuPannel.template = 'awesome.MenuPannel';

    return AwesomeMenuPannel;
});
