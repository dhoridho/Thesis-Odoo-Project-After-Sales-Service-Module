$(document).ready(function(){
    let slideIndex = 0;
    let currentInterval = 5000;
    showSlides();

    function showSlides() {
        let i;
        let slides = $('.pos-payment_info').find('.pos-advertisement').find('.carousel-item');
        if (slides.length){
            for (i = 0; i < slides.length; i++) {
                slides[i].style.display = "none";
            }
            slideIndex++;
            if (slideIndex > slides.length) {slideIndex = 1}
            slides[slideIndex-1].style.display = "block";
            var currentInterval = $('#myCarousel').find('.active').attr('data-interval');
        }
        setTimeout(showSlides, currentInterval); // Change image every currentInterval seconds
      }


});
