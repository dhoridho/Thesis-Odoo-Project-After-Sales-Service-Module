odoo.define('awesome_theme_pro.full_screen', function (require) {
    "use strict";

    const { Component, hooks } = owl;
    const { useState } = hooks;

    class AwesomeFullScreen_ extends Component {

        constructor() {
            super(...arguments);

            this.state = useState({
                maxized: false,
            });

            $(document).bind("fullscreenchange", () => {
                this.state.maxized = $(document).fullScreen();
            });
        }

        _toggle_full_screen() {
            if (!this.state.maxized) {
                this.state.maxized = true;
                $(document).fullScreen(true);
            } else {
                this.state.maxized = false;
                $(document).fullScreen(false);
            }
        }
        
    }

    AwesomeFullScreen_.template = 'awesome_theme_pro.full_screen';

    return AwesomeFullScreen_;
});



