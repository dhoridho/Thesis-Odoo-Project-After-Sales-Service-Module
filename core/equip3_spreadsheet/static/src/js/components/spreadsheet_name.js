odoo.define("equip3_spreadsheet.SpreadsheetName", function (require) {
    "use strict";
    const { useState, useRef } = owl.hooks;

    const WIDTH_MARGIN = 3
    const PADDING_RIGHT = 5;
    const PADDING_LEFT = PADDING_RIGHT - WIDTH_MARGIN;


    class SpreadsheetName extends owl.Component {

        constructor() {
            super(...arguments);
            this.placeholder = this.env._t("Untitled spreadsheet");
            this.state = useState({
                inputSize: 1,
                isUntitled: this._isUntitled(this.props.name),
            });
            this.input = useRef("speadsheetNameInput");
        }

        async mounted() {
            this._setInputSize(this.props.name);
        }
        
        _setInputSize(text) {
            const { font } = window.getComputedStyle(this.input.el);
            this.state.inputSize = this._computeTextWidth(text || this.placeholder, font) + PADDING_RIGHT + PADDING_LEFT;
        }
        
        _computeTextWidth(text, font) {
            const canvas = document.createElement("canvas");
            const context = canvas.getContext("2d");
            context.font = font;
            const width = context.measureText(text).width;
            return Math.ceil(width) + WIDTH_MARGIN;
        }
        
        _isUntitled(name) {
            name = name.trim();
            return !name || name === this.placeholder;
        }
        
        _onFocus(ev) {
            if (this._isUntitled(ev.target.value)) {
                ev.target.value = this.placeholder;
                ev.target.select();
            }
        }
        
        _onInput(ev) {
            const value = ev.target.value;
            this.state.isUntitled = this._isUntitled(value);
            this._setInputSize(value);
        }
        
        _onNameChanged(ev) {
            const value = ev.target.value.trim();
            ev.target.value = value;
            this._setInputSize(value);
            this.trigger("spreadsheet-name-changed", {
                name: value,
            });
            ev.target.blur();
        }
    }

    SpreadsheetName.template = "equip3_spreadsheet.SpreadsheetName";
    SpreadsheetName.props = {
        name: String,
    };

    return SpreadsheetName;
});
