$(document).ready(function () {

    // Multi image gallery
    var api;
    $('#gallery').each(function (index) {
        var dynamic_data = {}
        //dynamic_data['gallery_images_preload_type'] = 'all'
        dynamic_data['slider_scale_mode'] = 'fit'
        dynamic_data['slider_enable_text_panel'] = false
        dynamic_data['gallery_skin'] = "alexis"
        dynamic_data['gallery_width'] = 1800
        dynamic_data['theme_panel_position'] = 'left'
        dynamic_data['thumb_image_overlay_effect'] = true
        dynamic_data['thumb_image_overlay_type'] = "blur"

        api = $('#gallery').unitegallery(dynamic_data);
    });

});
