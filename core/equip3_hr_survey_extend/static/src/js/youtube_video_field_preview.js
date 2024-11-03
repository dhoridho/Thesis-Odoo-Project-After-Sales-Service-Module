odoo.define('equip3_hr_survey_extend.youtube_video_field_preview', function (require) {
"use strict";


var AbstractField = require('web.AbstractField');
var core = require('web.core');
var fieldRegistry = require('web.field_registry');

var QWeb = core.qweb;

/**
 * Displays preview of the video showcasing product.
 */
var FieldYoutubeVideoPreview = AbstractField.extend({
    className: 'd-block o_field_youtube_video_preview',

    _render: function () {
        this.$el.html(QWeb.render('youtubeVideo', {
            embedCode: this.value,
        }));
    },
});

fieldRegistry.add('youtube_video_preview', FieldYoutubeVideoPreview);

return FieldYoutubeVideoPreview;

});
